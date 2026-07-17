"""Phase 6c: techniques as first modifier source → cultivation sessions."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from random import Random

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from ai_adventure.engine.constants import (
    ANOMALY_STATE_NONE,
    BREAKTHROUGH_NOT_READY,
    CULTIVATION_PATH_ORDINARY,
    PATH_STATUS_PROVISIONAL,
    STARTING_REALM_ID,
    STARTING_STAGE_ID,
)
from ai_adventure.engine.cultivation_sessions import run_cultivation_session
from ai_adventure.engine.cultivation_state import CultivationState
from ai_adventure.engine.modifiers import (
    ModifierContext,
    ModifierSnapshot,
    aggregate,
)
from ai_adventure.engine.techniques import (
    get_technique,
    list_techniques,
    technique_mastery_to_effect_instances,
    validate_technique_catalog_against_bundles,
    TechniqueMasteryRecord,
)
from ai_adventure.services.cultivation import CultivationService
from ai_adventure.services.techniques import TechniqueService
from tests.conftest_helpers import advance_to_cultivation_hall, create_test_save, make_service


def _state(**overrides: object) -> CultivationState:
    base = CultivationState(
        cultivation_path=CULTIVATION_PATH_ORDINARY,
        path_status=PATH_STATUS_PROVISIONAL,
        realm_id=STARTING_REALM_ID,
        stage_id=STARTING_STAGE_ID,
        body=1,
        qi=1,
        soul=1,
        dao=1,
        foundation_quality=1,
        qi_reserve_current=0,
        qi_reserve_max=10,
        cultivation_progress=0,
        realm_comprehension=0,
        foundation_stability=50,
        practice_sessions=0,
        anomaly_state=ANOMALY_STATE_NONE,
        breakthrough_readiness=BREAKTHROUGH_NOT_READY,
    )
    return replace(base, **overrides)  # type: ignore[arg-type]


def test_technique_catalog_has_starters() -> None:
    techs = list_techniques()
    ids = [t.id for t in techs]
    assert "tech_steady_practice" in ids
    assert "tech_qi_absorption" in ids
    assert "tech_foundation_guard" in ids
    assert "tech_threshold_focus" in ids
    validate_technique_catalog_against_bundles()


def test_each_starter_targets_a_different_modifier_category() -> None:
    from ai_adventure.engine.modifiers import load_effect_bundle_catalog, load_effect_type_registry

    registry = load_effect_type_registry()
    bundles = load_effect_bundle_catalog(type_registry=registry)
    practice = bundles.get(get_technique("tech_steady_practice").effect_bundle_id)
    qi = bundles.get(get_technique("tech_qi_absorption").effect_bundle_id)
    foundation = bundles.get(get_technique("tech_foundation_guard").effect_bundle_id)
    assert practice.effects[0].type == "session_progress_mult"
    assert qi.effects[0].type == "session_qi_gain_mult"
    assert foundation.effects[0].type == "session_stability_flat"
    threshold = bundles.get(get_technique("tech_threshold_focus").effect_bundle_id)
    assert threshold.effects[0].type == "breakthrough_chance_flat"


def test_session_consumer_uses_snapshot_only_not_technique_tables() -> None:
    """Cultivation session accepts ModifierSnapshot; no technique imports needed."""

    snap = ModifierSnapshot(
        numbers={"session_progress_mult": 1.10, "session_qi_gain_mult": 1.0},
        flags=frozenset(),
        contributions=(),
    )
    baseline = run_cultivation_session(_state(), "balanced", rng=Random(0))
    boosted = run_cultivation_session(
        _state(),
        "balanced",
        rng=Random(0),
        modifiers=snap,
    )
    assert boosted.progress_after > baseline.progress_after
    assert boosted.progress_after == 27  # int(25 * 1.10)


def test_learn_technique_changes_snapshot_and_session_outcome(tmp_path: Path) -> None:
    service = create_test_save(tmp_path)
    save_id = service.list_saves()[0].save_id
    advance_to_cultivation_hall(service, save_id)

    tech_service = TechniqueService(service._session_factory)
    cult_service = CultivationService(service._session_factory)

    before = cult_service.cultivate(save_id, "balanced", rng=Random(0))
    assert before.outcome_type == "success"
    # Starter wood root applies session_progress_mult 1.05 → int(25 * 1.05) = 26
    assert before.progress_after == 26
    assert before.qi_after == 4

    learned = tech_service.learn(save_id, "tech_steady_practice")
    assert learned["known"] is True
    assert learned["equipped"] is True

    after = cult_service.cultivate(save_id, "balanced", rng=Random(0))
    # tech 1.10 × root 1.05 = 1.155 → int(25 * 1.155) = 28
    assert after.progress_after == before.progress_after + 28
    assert after.qi_after == before.qi_after + 4  # qi technique not learned


def test_qi_and_stability_techniques_affect_session(tmp_path: Path) -> None:
    service = create_test_save(tmp_path)
    save_id = service.list_saves()[0].save_id
    advance_to_cultivation_hall(service, save_id)
    tech_service = TechniqueService(service._session_factory)
    cult_service = CultivationService(service._session_factory)

    tech_service.learn(save_id, "tech_qi_absorption")
    tech_service.learn(save_id, "tech_foundation_guard")

    result = cult_service.cultivate(save_id, "balanced", rng=Random(0))
    # balanced qi 4 * 1.25 = 5; stability +2
    assert result.qi_after == 5
    assert result.stability_after == 52


def test_qi_mult_with_clear_integer_effect() -> None:
    snap = ModifierSnapshot(
        numbers={"session_qi_gain_mult": 1.10},
        flags=frozenset(),
        contributions=(),
    )
    baseline = run_cultivation_session(_state(), "aggressive", rng=Random(0))
    boosted = run_cultivation_session(
        _state(),
        "aggressive",
        rng=Random(0),
        modifiers=snap,
    )
    assert baseline.qi_after == 6
    assert boosted.qi_after == 6  # int(6*1.10)=6
    # Use a synthetic snapshot with stronger mult within cap to prove wiring
    strong = ModifierSnapshot(
        numbers={"session_qi_gain_mult": 1.25},
        flags=frozenset(),
        contributions=(),
    )
    boosted_strong = run_cultivation_session(
        _state(),
        "aggressive",
        rng=Random(0),
        modifiers=strong,
    )
    assert boosted_strong.qi_after == 7  # int(6 * 1.25) = 7


def test_stability_flat_from_snapshot() -> None:
    snap = ModifierSnapshot(
        numbers={"session_stability_flat": 2.0},
        flags=frozenset(),
        contributions=(),
    )
    baseline = run_cultivation_session(_state(), "balanced", rng=Random(0))
    boosted = run_cultivation_session(
        _state(),
        "balanced",
        rng=Random(0),
        modifiers=snap,
    )
    assert boosted.stability_after == baseline.stability_after + 2


def test_mastery_source_adapter_builds_instances() -> None:
    records = [
        TechniqueMasteryRecord(
            actor_id="actor-1",
            technique_id="tech_steady_practice",
            known=True,
            equipped=True,
            mastery_rank=1,
        )
    ]
    instances = technique_mastery_to_effect_instances(records)
    assert len(instances) == 1
    assert instances[0].bundle_id == "bundle_tech_steady_practice"
    snap = aggregate(
        instances,
        ModifierContext(actor_id="actor-1", world_day=1, activity="cultivate_session"),
    )
    assert snap.number("session_progress_mult") == pytest.approx(1.10)


def test_unequipped_technique_does_not_affect_snapshot() -> None:
    records = [
        TechniqueMasteryRecord(
            actor_id="actor-1",
            technique_id="tech_steady_practice",
            known=True,
            equipped=False,
            mastery_rank=1,
        )
    ]
    instances = technique_mastery_to_effect_instances(records)
    assert instances == []


def test_migration_0009_creates_technique_mastery(tmp_path: Path, monkeypatch) -> None:
    from ai_adventure.config import get_settings

    db_path = tmp_path / "migrate.db"
    url = f"sqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("AI_ADVENTURE_DATABASE_URL", url)
    get_settings.cache_clear()

    root = Path(__file__).resolve().parents[1]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")

    with create_engine(url, future=True).connect() as conn:
        version = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
        assert version == ("0012_npc_world_state",)
        tables = {
            row[0]
            for row in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            ).fetchall()
        }
        assert "technique_mastery" in tables
        assert "spiritual_root_ownership" in tables

    get_settings.cache_clear()
