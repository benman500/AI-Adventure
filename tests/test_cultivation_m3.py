"""Cultivation engine tests for Milestone 3."""

from dataclasses import replace

import pytest

from ai_adventure.engine import EngineValidationError, attempt_breakthrough, commit_path_choice
from ai_adventure.engine.constants import (
    ANOMALY_STATE_NONE,
    ANOMALY_STATE_RESOLVED,
    ANOMALY_STATE_TRIGGERED,
    BREAKTHROUGH_NOT_READY,
    BREAKTHROUGH_PROGRESS_THRESHOLD,
    BREAKTHROUGH_QI_THRESHOLD,
    BREAKTHROUGH_READY,
    CULTIVATION_METHOD_ABSORB_QI,
    CULTIVATION_METHOD_CALM_MIND,
    CULTIVATION_METHOD_STABILIZE_FOUNDATION,
    CULTIVATION_PATH_BOUNDLESS,
    CULTIVATION_PATH_ORDINARY,
    PATH_STATUS_CONFIRMED_BOUNDLESS,
    PATH_STATUS_CONFIRMED_ORDINARY,
    PATH_STATUS_PROVISIONAL,
    STARTING_REALM_ID,
    STARTING_STAGE_ID,
)
from ai_adventure.engine.cultivation import (
    CultivationState,
    apply_cultivation_method,
    is_breakthrough_ready,
)


def _ready_state(*, sessions: int = 3) -> CultivationState:
    return CultivationState(
        cultivation_path=CULTIVATION_PATH_ORDINARY,
        path_status=PATH_STATUS_PROVISIONAL,
        realm_id=STARTING_REALM_ID,
        stage_id=STARTING_STAGE_ID,
        body=1,
        qi=1,
        soul=1,
        dao=1,
        foundation_quality=1,
        qi_reserve_current=BREAKTHROUGH_QI_THRESHOLD,
        qi_reserve_max=10,
        cultivation_progress=BREAKTHROUGH_PROGRESS_THRESHOLD,
        realm_comprehension=0,
        foundation_stability=50,
        practice_sessions=sessions,
        anomaly_state=ANOMALY_STATE_NONE,
        breakthrough_readiness=BREAKTHROUGH_READY,
    )


def test_cultivation_methods_update_qi_and_progress() -> None:
    """Each named method applies deterministic gains."""

    state = _ready_state(sessions=0)
    state = replace(
        state,
        qi_reserve_current=0,
        cultivation_progress=0,
        breakthrough_readiness=BREAKTHROUGH_NOT_READY,
    )

    absorb = apply_cultivation_method(state, CULTIVATION_METHOD_ABSORB_QI)
    assert absorb.state.qi_reserve_current == 4
    assert absorb.state.cultivation_progress == 25

    stabilize = apply_cultivation_method(absorb.state, CULTIVATION_METHOD_STABILIZE_FOUNDATION)
    assert stabilize.state.cultivation_progress == 52

    calm = apply_cultivation_method(stabilize.state, CULTIVATION_METHOD_CALM_MIND)
    assert calm.state.qi_reserve_current == 10


def test_breakthrough_readiness_from_thresholds_not_session_count() -> None:
    """Readiness depends on qi/progress, not a fixed session index."""

    state = CultivationState(
        cultivation_path=CULTIVATION_PATH_ORDINARY,
        path_status=PATH_STATUS_PROVISIONAL,
        realm_id=STARTING_REALM_ID,
        stage_id=STARTING_STAGE_ID,
        body=1,
        qi=1,
        soul=1,
        dao=1,
        foundation_quality=1,
        qi_reserve_current=BREAKTHROUGH_QI_THRESHOLD,
        qi_reserve_max=10,
        cultivation_progress=BREAKTHROUGH_PROGRESS_THRESHOLD,
        realm_comprehension=0,
        foundation_stability=50,
        practice_sessions=99,
        anomaly_state=ANOMALY_STATE_NONE,
        breakthrough_readiness=BREAKTHROUGH_NOT_READY,
    )
    assert is_breakthrough_ready(state)

    low_sessions = replace(state, practice_sessions=1)
    assert is_breakthrough_ready(low_sessions)


def test_anomaly_on_first_breakthrough_attempt() -> None:
    """Provisional path triggers anomaly on breakthrough attempt, not before."""

    state = _ready_state()
    result = attempt_breakthrough(state)
    assert result.state.anomaly_state == ANOMALY_STATE_TRIGGERED
    assert result.state.stage_id == STARTING_STAGE_ID
    assert any(e.event_type == "cultivation_anomaly_triggered" for e in result.events)


def test_anomaly_not_triggered_by_practice_alone() -> None:
    """Practice alone never triggers the anomaly."""

    state = CultivationState(
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
    for _ in range(5):
        result = apply_cultivation_method(state, CULTIVATION_METHOD_ABSORB_QI)
        state = result.state
    assert state.anomaly_state == ANOMALY_STATE_NONE


def test_ordinary_path_commit() -> None:
    """Ordinary fix resolves anomaly and advances stage."""

    state = replace(
        _ready_state(),
        anomaly_state=ANOMALY_STATE_TRIGGERED,
        breakthrough_readiness="attempted",
    )
    result = commit_path_choice(state, choose_boundless=False)
    assert result.state.path_status == PATH_STATUS_CONFIRMED_ORDINARY
    assert result.state.anomaly_state == ANOMALY_STATE_RESOLVED
    assert result.state.stage_id == "middle"


def test_boundless_path_commit() -> None:
    """Boundless commit does not grant free breakthrough power."""

    state = replace(
        _ready_state(),
        anomaly_state=ANOMALY_STATE_TRIGGERED,
        breakthrough_readiness="attempted",
    )
    result = commit_path_choice(state, choose_boundless=True)
    assert result.state.path_status == PATH_STATUS_CONFIRMED_BOUNDLESS
    assert result.state.cultivation_path == CULTIVATION_PATH_BOUNDLESS
    assert result.state.stage_id == STARTING_STAGE_ID
    # Boundless bumps stability (+5) and quality (+1), then quality is synced
    # upward from stability so both meters stay coherent.
    assert result.state.foundation_stability == 55
    assert result.state.foundation_quality == 3


def test_path_choice_is_permanent() -> None:
    """Second path commit is rejected."""

    state = replace(
        _ready_state(),
        path_status=PATH_STATUS_CONFIRMED_ORDINARY,
        anomaly_state=ANOMALY_STATE_RESOLVED,
    )
    with pytest.raises(EngineValidationError, match="already been confirmed"):
        commit_path_choice(state, choose_boundless=True)


def test_boundless_practice_slower_than_ordinary() -> None:
    """Post-choice Boundless progress is slower than ordinary."""

    ordinary = CultivationState(
        cultivation_path=CULTIVATION_PATH_ORDINARY,
        path_status=PATH_STATUS_CONFIRMED_ORDINARY,
        realm_id=STARTING_REALM_ID,
        stage_id="middle",
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
        anomaly_state=ANOMALY_STATE_RESOLVED,
        breakthrough_readiness=BREAKTHROUGH_NOT_READY,
    )
    boundless = replace(
        ordinary,
        cultivation_path=CULTIVATION_PATH_BOUNDLESS,
        path_status=PATH_STATUS_CONFIRMED_BOUNDLESS,
    )

    ord_result = apply_cultivation_method(ordinary, CULTIVATION_METHOD_ABSORB_QI)
    bnd_result = apply_cultivation_method(boundless, CULTIVATION_METHOD_ABSORB_QI)
    assert bnd_result.state.cultivation_progress < ord_result.state.cultivation_progress
