"""Phase 3 breakthrough readiness and stage advancement tests."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from random import Random

import pytest
from fastapi.testclient import TestClient

from ai_adventure.engine.breakthroughs import (
    apply_comprehension_carryover,
    evaluate_breakthrough_readiness,
    load_breakthrough_catalog,
    qi_cost_for_transition,
    recalculate_qi_reserve_max,
    run_breakthrough_attempt,
)
from ai_adventure.engine.constants import (
    ANOMALY_STATE_NONE,
    ANOMALY_STATE_RESOLVED,
    ANOMALY_STATE_TRIGGERED,
    BREAKTHROUGH_NOT_READY,
    CULTIVATION_PATH_ORDINARY,
    PATH_STATUS_CONFIRMED_ORDINARY,
    PATH_STATUS_PROVISIONAL,
    STARTING_REALM_ID,
)
from ai_adventure.engine.cultivation_path import attempt_breakthrough
from ai_adventure.engine.cultivation_state import CultivationState
from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.repositories import SaveRepository
from tests.conftest_helpers import (
    VALID_IDENTITY_ANSWERS,
    advance_to_cultivation_hall,
    create_test_save,
    make_test_app,
)


def _confirmed(
    *,
    stage_id: str = "early",
    realm_id: str = STARTING_REALM_ID,
    progress: int = 100,
    comprehension: int = 25,
    qi: int = 10,
    qi_max: int = 10,
    stability: int = 50,
    attempts: int = 0,
) -> CultivationState:
    return CultivationState(
        cultivation_path=CULTIVATION_PATH_ORDINARY,
        path_status=PATH_STATUS_CONFIRMED_ORDINARY,
        realm_id=realm_id,
        stage_id=stage_id,
        body=1,
        qi=1,
        soul=1,
        dao=1,
        foundation_quality=1,
        qi_reserve_current=qi,
        qi_reserve_max=qi_max,
        cultivation_progress=progress,
        realm_comprehension=comprehension,
        foundation_stability=stability,
        practice_sessions=0,
        anomaly_state=ANOMALY_STATE_RESOLVED,
        breakthrough_readiness=BREAKTHROUGH_NOT_READY,
        breakthrough_attempts_current_stage=attempts,
    )


@pytest.mark.parametrize(
    ("stage_id", "comprehension", "target_stage"),
    [
        ("early", 25, "middle"),
        ("middle", 45, "late"),
        ("late", 65, "peak"),
    ],
)
def test_readiness_for_stage_transitions(
    stage_id: str,
    comprehension: int,
    target_stage: str,
) -> None:
    state = _confirmed(stage_id=stage_id, comprehension=comprehension, qi=10)
    readiness = evaluate_breakthrough_readiness(state)
    assert readiness.eligible is True
    assert readiness.target_stage_id == target_stage
    assert readiness.target_realm_id == STARTING_REALM_ID
    assert readiness.progress_required == 100
    assert readiness.comprehension_required == comprehension


def test_readiness_peak_to_qi_gathering() -> None:
    state = _confirmed(
        stage_id="peak",
        comprehension=80,
        qi=10,
        qi_max=10,
    )
    readiness = evaluate_breakthrough_readiness(state)
    assert readiness.eligible is True
    assert readiness.target_realm_id == "qi_gathering"
    assert readiness.target_stage_id == "early"
    assert readiness.mode == "realm"


def test_qi_gathering_peak_blocks_further_advancement() -> None:
    state = _confirmed(
        realm_id="qi_gathering",
        stage_id="peak",
        comprehension=100,
        qi=20,
        qi_max=20,
    )
    readiness = evaluate_breakthrough_readiness(state)
    assert readiness.eligible is False
    assert readiness.mode == "none"
    assert any("No further" in reason for reason in readiness.blocking_reasons)


class _AlwaysSucceed(Random):
    def random(self) -> float:  # noqa: A003
        return 0.0


class _AlwaysFail(Random):
    def random(self) -> float:  # noqa: A003
        return 0.99


def test_successful_early_to_middle() -> None:
    state = _confirmed(stage_id="early", comprehension=25, qi=10)
    result = run_breakthrough_attempt(state, rng=_AlwaysSucceed())
    assert result.outcome_type == "success"
    assert result.stage_after == "middle"
    assert result.progress_after == 0
    assert result.attempts_after == 0
    cost = qi_cost_for_transition(10, 25)
    assert result.qi_after == 10 - cost
    assert result.comprehension_after == apply_comprehension_carryover(25, ratio=0.5)


def test_successful_middle_to_late() -> None:
    state = _confirmed(stage_id="middle", comprehension=45, qi=10)
    result = run_breakthrough_attempt(state, rng=_AlwaysSucceed())
    assert result.success is True
    assert result.stage_after == "late"


def test_successful_late_to_peak() -> None:
    state = _confirmed(stage_id="late", comprehension=65, qi=10)
    result = run_breakthrough_attempt(state, rng=_AlwaysSucceed())
    assert result.success is True
    assert result.stage_after == "peak"


def test_insufficient_progress() -> None:
    state = _confirmed(progress=99, comprehension=25, qi=10)
    readiness = evaluate_breakthrough_readiness(state)
    assert readiness.eligible is False
    result = run_breakthrough_attempt(state, rng=Random(0))
    assert result.outcome_type == "blocked"


def test_insufficient_comprehension() -> None:
    state = _confirmed(comprehension=24, qi=10)
    readiness = evaluate_breakthrough_readiness(state)
    assert readiness.eligible is False


def test_insufficient_qi() -> None:
    cost = qi_cost_for_transition(10, 25)
    state = _confirmed(qi=cost - 1, comprehension=25)
    readiness = evaluate_breakthrough_readiness(state)
    assert readiness.eligible is False


def test_story_gated_provisional_attempt() -> None:
    provisional = CultivationState(
        cultivation_path=CULTIVATION_PATH_ORDINARY,
        path_status=PATH_STATUS_PROVISIONAL,
        realm_id=STARTING_REALM_ID,
        stage_id="early",
        body=1,
        qi=1,
        soul=1,
        dao=1,
        foundation_quality=1,
        qi_reserve_current=10,
        qi_reserve_max=10,
        cultivation_progress=100,
        realm_comprehension=25,
        foundation_stability=50,
        practice_sessions=0,
        anomaly_state=ANOMALY_STATE_NONE,
        breakthrough_readiness=BREAKTHROUGH_NOT_READY,
    )
    readiness = evaluate_breakthrough_readiness(provisional)
    assert readiness.mode == "opening"
    assert readiness.eligible is True
    with pytest.raises(EngineValidationError, match="Opening breakthrough"):
        run_breakthrough_attempt(provisional, rng=Random(0))
    opening = attempt_breakthrough(provisional)
    assert opening.state.anomaly_state == ANOMALY_STATE_TRIGGERED
    assert opening.state.stage_id == "early"


def test_deterministic_success_and_failure() -> None:
    state = _confirmed(stage_id="early", comprehension=80, qi=10, stability=80)
    success = run_breakthrough_attempt(state, rng=_AlwaysSucceed())
    assert success.outcome_type == "success"

    failure = run_breakthrough_attempt(state, rng=_AlwaysFail())
    assert failure.outcome_type == "failure"
    assert failure.stage_after == "early"
    assert failure.qi_after < failure.qi_before
    assert failure.stability_after < failure.stability_before
    assert failure.progress_after < failure.progress_before
    assert failure.attempts_after == 1


def test_qi_consumption_and_progress_reset_on_success() -> None:
    state = _confirmed(comprehension=40, qi=10)
    cost = qi_cost_for_transition(10, 25)
    result = run_breakthrough_attempt(state, rng=_AlwaysSucceed())
    assert result.success
    assert result.qi_after == 10 - cost
    assert result.progress_after == 0
    assert result.attempts_after == 0


def test_comprehension_carryover_and_qi_max_on_realm_advance() -> None:
    catalog = load_breakthrough_catalog()
    # Intentional bonus above Body Tempering floor of 10.
    state = _confirmed(
        stage_id="peak",
        comprehension=90,
        qi=14,
        qi_max=14,
        stability=80,
    )
    assert recalculate_qi_reserve_max(state, new_realm_id="qi_gathering") == 24

    result = run_breakthrough_attempt(state, rng=_AlwaysSucceed())
    assert result.success
    assert result.realm_after == "qi_gathering"
    assert result.stage_after == "early"
    assert result.comprehension_after == apply_comprehension_carryover(
        90, ratio=catalog.comprehension_carry_ratio
    )
    assert result.state.qi_reserve_max == 24


def test_attempt_counter_resets_on_success() -> None:
    state = _confirmed(comprehension=40, qi=10, attempts=3)
    result = run_breakthrough_attempt(state, rng=_AlwaysSucceed())
    assert result.success
    assert result.attempts_after == 0
    assert result.state.breakthrough_attempts_current_stage == 0


def test_direct_backend_bypass_blocked_outside_hall(tmp_path: Path) -> None:
    from ai_adventure.services.cultivation import CultivationService

    service = create_test_save(tmp_path)
    save_id = service.list_saves()[0].save_id
    service.get_play_scene(save_id)  # bootstrap story at opening (not hall)
    cult = CultivationService(service._session_factory)
    with pytest.raises(EngineValidationError, match="cannot be attempted here"):
        cult.attempt_breakthrough(save_id)


def test_save_reload_breakthrough_result(tmp_path: Path) -> None:
    service = create_test_save(tmp_path, character_name="Breaker")
    save_id = service.list_saves()[0].save_id
    # Force confirmed middle-ready state in DB after opening skip is hard; set fields directly.
    with service._session_factory() as session:
        save = SaveRepository(session).get_with_player(save_id)
        assert save and save.player
        player = save.player
        player.path_status = PATH_STATUS_CONFIRMED_ORDINARY
        player.anomaly_state = ANOMALY_STATE_RESOLVED
        player.stage_id = "early"
        player.cultivation_progress = 100
        player.realm_comprehension = 40
        player.qi_reserve_current = 10
        player.qi_reserve_max = 10
        player.foundation_stability = 60
        session.commit()

    advance_to_cultivation_hall(service, save_id)
    before = service.get_play_scene(save_id)
    assert before.breakthrough_readiness is not None
    scene = service.submit_story_action(save_id, "attempt_breakthrough")
    assert scene.last_breakthrough_result is not None
    reloaded = service.get_play_scene(save_id)
    assert reloaded.last_breakthrough_result is not None
    assert reloaded.cultivation["stage_id"] in {"early", "middle"}


def test_breakthrough_ui_disabled_states(tmp_path: Path) -> None:
    app = make_test_app(tmp_path, filename="bt_ui.db")
    client = TestClient(app)
    created = client.post(
        "/new",
        data={
            "character_name": "UI Breaker",
            "background_id": "hunter",
            **{f"answer_{k}": v for k, v in VALID_IDENTITY_ANSWERS.items()},
        },
        follow_redirects=False,
    )
    save_id = created.headers["location"].rsplit("/", 1)[-1]
    early = client.get(f"/play/{save_id}")
    assert b"Breakthrough Readiness" in early.content

    # Walk to hall
    for action in (
        "check_snares",
        "report_only",
        "leave_home",
        "continue",
        "continue",
        "travel_together",
        "continue",
        "enter",
        "continue",
        "continue",
        "continue",
        "continue",
    ):
        client.post(f"/play/{save_id}/action", data={"action_id": action})

    hall = client.get(f"/play/{save_id}")
    assert hall.status_code == 200
    assert b"Breakthrough Readiness" in hall.content
    assert b"Attempt Breakthrough" in hall.content
