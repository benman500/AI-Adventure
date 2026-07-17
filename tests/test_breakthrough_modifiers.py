"""Breakthroughs as ModifierSnapshot consumer + consumer allowlist policy."""

from __future__ import annotations

from dataclasses import replace
from random import Random

import pytest

from ai_adventure.engine.breakthroughs import (
    BREAKTHROUGH_SUPPORTED_EFFECT_TYPES,
    calculate_success_chance,
    evaluate_breakthrough_readiness,
    find_transition_for_state,
    qi_cost_for_transition,
    run_breakthrough_attempt,
)
from ai_adventure.engine.constants import (
    ANOMALY_STATE_NONE,
    BREAKTHROUGH_NOT_READY,
    CULTIVATION_PATH_ORDINARY,
    PATH_STATUS_CONFIRMED_ORDINARY,
    STARTING_REALM_ID,
)
from ai_adventure.engine.cultivation_sessions import (
    SESSION_SUPPORTED_EFFECT_TYPES,
    apply_session_modifier_snapshot,
)
from ai_adventure.engine.cultivation_state import CultivationState
from ai_adventure.engine.modifiers import (
    ModifierSnapshot,
    consumer_number,
    ignored_snapshot_effect_types,
)
from ai_adventure.engine.techniques import (
    TechniqueMasteryRecord,
    technique_mastery_to_effect_instances,
)
from ai_adventure.engine.modifiers import ModifierContext, aggregate
from ai_adventure.services.techniques import TechniqueService
from tests.conftest_helpers import create_test_save


def _confirmed_middle(**overrides: object) -> CultivationState:
    base = CultivationState(
        cultivation_path=CULTIVATION_PATH_ORDINARY,
        path_status=PATH_STATUS_CONFIRMED_ORDINARY,
        realm_id=STARTING_REALM_ID,
        stage_id="middle",
        body=1,
        qi=1,
        soul=1,
        dao=1,
        foundation_quality=3,
        qi_reserve_current=20,
        qi_reserve_max=20,
        cultivation_progress=100,
        realm_comprehension=50,
        foundation_stability=55,
        practice_sessions=5,
        anomaly_state=ANOMALY_STATE_NONE,
        breakthrough_readiness=BREAKTHROUGH_NOT_READY,
        breakthrough_attempts_current_stage=0,
    )
    return replace(base, **overrides)  # type: ignore[arg-type]


def test_session_consumer_allowlist_ignores_unsupported_types() -> None:
    snap = ModifierSnapshot(
        numbers={
            "session_progress_mult": 1.10,
            "breakthrough_chance_flat": 0.05,  # must NOT affect sessions
        },
        flags=frozenset(),
        contributions=(),
    )
    progress, qi, comp, stab = apply_session_modifier_snapshot(
        progress_gain=25,
        qi_gain=4,
        comprehension_gain=3,
        stability_delta=0,
        modifiers=snap,
    )
    assert progress == 27
    assert ignored_snapshot_effect_types(
        snap,
        supported=SESSION_SUPPORTED_EFFECT_TYPES,
    ) == frozenset({"breakthrough_chance_flat"})
    # consumer_number refuses unsupported ids even if present
    assert (
        consumer_number(
            snap,
            "breakthrough_chance_flat",
            supported=SESSION_SUPPORTED_EFFECT_TYPES,
            default=0.0,
        )
        == 0.0
    )


def test_breakthrough_chance_flat_increases_success_chance() -> None:
    state = _confirmed_middle()
    transition = find_transition_for_state(state)
    assert transition is not None
    qi_cost = qi_cost_for_transition(state.qi_reserve_max, transition.qi_cost_percent_of_max)
    base = calculate_success_chance(state, transition, qi_cost=qi_cost)
    boosted = calculate_success_chance(
        state,
        transition,
        qi_cost=qi_cost,
        modifiers=ModifierSnapshot(
            numbers={"breakthrough_chance_flat": 0.03},
            flags=frozenset(),
            contributions=(),
        ),
    )
    assert boosted == pytest.approx(base + 0.03)


def test_breakthrough_consumer_ignores_session_types() -> None:
    state = _confirmed_middle()
    transition = find_transition_for_state(state)
    assert transition is not None
    qi_cost = qi_cost_for_transition(state.qi_reserve_max, transition.qi_cost_percent_of_max)
    base = calculate_success_chance(state, transition, qi_cost=qi_cost)
    polluted = calculate_success_chance(
        state,
        transition,
        qi_cost=qi_cost,
        modifiers=ModifierSnapshot(
            numbers={
                "session_progress_mult": 1.25,
                "breakthrough_chance_flat": 0.02,
            },
            flags=frozenset(),
            contributions=(),
        ),
    )
    assert polluted == pytest.approx(base + 0.02)
    assert "session_progress_mult" not in BREAKTHROUGH_SUPPORTED_EFFECT_TYPES


def test_breakthrough_attempt_uses_snapshot_only() -> None:
    state = _confirmed_middle()
    readiness = evaluate_breakthrough_readiness(state)
    assert readiness.eligible

    boosted_readiness = evaluate_breakthrough_readiness(
        state,
        modifiers=ModifierSnapshot(
            numbers={"breakthrough_chance_flat": 0.05},
            flags=frozenset(),
            contributions=(),
        ),
    )
    assert boosted_readiness.success_chance == pytest.approx(readiness.success_chance + 0.05)

    result = run_breakthrough_attempt(
        state,
        rng=Random(0),
        modifiers=ModifierSnapshot(
            numbers={"breakthrough_chance_flat": 0.05},
            flags=frozenset(),
            contributions=(),
        ),
    )
    assert result.success_chance == pytest.approx(boosted_readiness.success_chance)
    assert result.outcome_type in {"success", "failure"}


def test_threshold_focus_technique_feeds_breakthrough_snapshot(tmp_path) -> None:
    service = create_test_save(tmp_path)
    save_id = service.list_saves()[0].save_id
    TechniqueService(service._session_factory).learn(save_id, "tech_threshold_focus")

    instances = technique_mastery_to_effect_instances(
        [
            TechniqueMasteryRecord(
                actor_id="actor-1",
                technique_id="tech_threshold_focus",
                known=True,
                equipped=True,
                mastery_rank=1,
            )
        ]
    )
    snap = aggregate(
        instances,
        ModifierContext(actor_id="actor-1", world_day=1, activity="breakthrough"),
    )
    assert snap.number("breakthrough_chance_flat") == pytest.approx(0.03)
    # cultivate_session context must not include breakthrough flat from this bundle
    session_snap = aggregate(
        instances,
        ModifierContext(actor_id="actor-1", world_day=1, activity="cultivate_session"),
    )
    assert "breakthrough_chance_flat" not in session_snap.numbers
