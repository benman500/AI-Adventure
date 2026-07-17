"""Milestone 3 opening path: anomaly, breakthrough attempt, path confirmation.

Phase 3 stage/realm breakthroughs live in ``engine.breakthroughs``. This module
keeps opening-story anomaly semantics and adapts confirmed-path attempts into
the generic breakthrough engine.
"""

from __future__ import annotations

from dataclasses import replace
from random import Random

from ai_adventure.engine.constants import (
    ANOMALY_STATE_NONE,
    ANOMALY_STATE_RESOLVED,
    ANOMALY_STATE_TRIGGERED,
    BREAKTHROUGH_ATTEMPTED,
    BREAKTHROUGH_NOT_READY,
    BREAKTHROUGH_PROGRESS_THRESHOLD,
    BREAKTHROUGH_QI_THRESHOLD,
    BREAKTHROUGH_READY,
    CULTIVATION_PATH_BOUNDLESS,
    CULTIVATION_PATH_ORDINARY,
    EVENT_TYPE_BREAKTHROUGH_ATTEMPT,
    EVENT_TYPE_BREAKTHROUGH_READINESS,
    EVENT_TYPE_CULTIVATION_ANOMALY,
    EVENT_TYPE_PATH_CHOICE_BOUNDLESS,
    EVENT_TYPE_PATH_CHOICE_ORDINARY,
    PATH_STATUS_CONFIRMED_BOUNDLESS,
    PATH_STATUS_CONFIRMED_ORDINARY,
    PATH_STATUS_PROVISIONAL,
)
from ai_adventure.engine.cultivation_state import CultivationEvent, CultivationResult, CultivationState
from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.foundation import clamp_stability, sync_foundation_quality


def is_breakthrough_ready(state: CultivationState) -> bool:
    """True when the player may attempt a breakthrough in their current mode.

    Provisional (opening): Milestone 3 qi/progress thresholds.
    Confirmed path: Phase 3 data-driven readiness (progress/comprehension/Qi).
    """

    if state.path_status == PATH_STATUS_PROVISIONAL:
        return (
            state.qi_reserve_current >= BREAKTHROUGH_QI_THRESHOLD
            and state.cultivation_progress >= BREAKTHROUGH_PROGRESS_THRESHOLD
            and state.breakthrough_readiness != BREAKTHROUGH_ATTEMPTED
            and state.anomaly_state != ANOMALY_STATE_TRIGGERED
        )

    from ai_adventure.engine.breakthroughs import evaluate_breakthrough_readiness

    return evaluate_breakthrough_readiness(state).eligible


def refresh_breakthrough_readiness(
    state: CultivationState,
) -> tuple[CultivationState, CultivationEvent | None]:
    """Update breakthrough readiness from current meters / gates."""

    if (
        state.path_status == PATH_STATUS_PROVISIONAL
        and state.breakthrough_readiness == BREAKTHROUGH_ATTEMPTED
    ):
        return state, None

    if is_breakthrough_ready(state):
        if state.breakthrough_readiness != BREAKTHROUGH_READY:
            updated = replace(state, breakthrough_readiness=BREAKTHROUGH_READY)
            event = CultivationEvent(
                event_type=EVENT_TYPE_BREAKTHROUGH_READINESS,
                payload={
                    "qi_reserve_current": updated.qi_reserve_current,
                    "cultivation_progress": updated.cultivation_progress,
                    "path_status": updated.path_status,
                },
            )
            return updated, event
        return state, None
    if state.breakthrough_readiness == BREAKTHROUGH_READY:
        return replace(state, breakthrough_readiness=BREAKTHROUGH_NOT_READY), None
    return state, None


def attempt_breakthrough(
    state: CultivationState,
    *,
    rng: Random | None = None,
) -> CultivationResult:
    """Attempt breakthrough: opening anomaly (provisional) or Phase 3 engine (confirmed)."""

    if state.path_status == PATH_STATUS_PROVISIONAL:
        return _opening_anomaly_attempt(state)

    from ai_adventure.engine.breakthroughs import run_breakthrough_attempt

    result = run_breakthrough_attempt(state, rng=rng)
    if result.outcome_type == "blocked":
        raise EngineValidationError(result.blocked_reason or "Breakthrough is unavailable")
    return CultivationResult(
        state=result.state,
        events=result.events,
        summary=result.summary,
    )


def _opening_anomaly_attempt(state: CultivationState) -> CultivationResult:
    """Milestone 3 first breakthrough attempt — triggers the anomaly, no stage advance."""

    if not (
        state.qi_reserve_current >= BREAKTHROUGH_QI_THRESHOLD
        and state.cultivation_progress >= BREAKTHROUGH_PROGRESS_THRESHOLD
    ):
        raise EngineValidationError("Breakthrough readiness has not been reached")
    if state.breakthrough_readiness == BREAKTHROUGH_ATTEMPTED:
        raise EngineValidationError("Breakthrough has already been attempted")
    if state.anomaly_state == ANOMALY_STATE_TRIGGERED:
        raise EngineValidationError("Cultivation anomaly already in progress")

    events: list[CultivationEvent] = [
        CultivationEvent(
            event_type=EVENT_TYPE_BREAKTHROUGH_ATTEMPT,
            payload={
                "realm_id": state.realm_id,
                "stage_id": state.stage_id,
                "qi_reserve_current": state.qi_reserve_current,
                "cultivation_progress": state.cultivation_progress,
                "mode": "opening_anomaly",
            },
        )
    ]
    updated = replace(
        state,
        breakthrough_readiness=BREAKTHROUGH_ATTEMPTED,
        anomaly_state=ANOMALY_STATE_TRIGGERED,
    )
    events.append(
        CultivationEvent(
            event_type=EVENT_TYPE_CULTIVATION_ANOMALY,
            payload={
                "realm_id": updated.realm_id,
                "stage_id": updated.stage_id,
                "message": "Breakthrough did not occur despite full readiness.",
            },
        )
    )
    return CultivationResult(
        state=updated,
        events=tuple(events),
        summary="You gather your Qi, reach for the breakthrough—and nothing happens.",
    )


def commit_path_choice(state: CultivationState, *, choose_boundless: bool) -> CultivationResult:
    """Permanently confirm ordinary (fix) or Boundless Foundation path."""

    if state.path_status != PATH_STATUS_PROVISIONAL:
        raise EngineValidationError("Cultivation path has already been confirmed")
    if state.anomaly_state != ANOMALY_STATE_TRIGGERED:
        raise EngineValidationError("Path choice is not available yet")

    if choose_boundless:
        new_stability = clamp_stability(state.foundation_stability + 5)
        new_quality = sync_foundation_quality(new_stability, state.foundation_quality + 1)
        updated = replace(
            state,
            cultivation_path=CULTIVATION_PATH_BOUNDLESS,
            path_status=PATH_STATUS_CONFIRMED_BOUNDLESS,
            anomaly_state=ANOMALY_STATE_RESOLVED,
            foundation_stability=new_stability,
            foundation_quality=new_quality,
            breakthrough_attempts_current_stage=0,
        )
        event = CultivationEvent(
            event_type=EVENT_TYPE_PATH_CHOICE_BOUNDLESS,
            payload={
                "cultivation_path": CULTIVATION_PATH_BOUNDLESS,
                "path_status": PATH_STATUS_CONFIRMED_BOUNDLESS,
            },
        )
        summary = "You commit to the ancient Boundless Foundation Path."
    else:
        # Story-gated ordinary fix: jump to Middle without a generic breakthrough.
        # Documented debt: Early→Middle for ordinary opening is not the Phase 3 engine.
        updated = replace(
            state,
            cultivation_path=CULTIVATION_PATH_ORDINARY,
            path_status=PATH_STATUS_CONFIRMED_ORDINARY,
            anomaly_state=ANOMALY_STATE_RESOLVED,
            stage_id="middle",
            cultivation_progress=0,
            qi_reserve_current=0,
            breakthrough_readiness=BREAKTHROUGH_NOT_READY,
            breakthrough_attempts_current_stage=0,
        )
        event = CultivationEvent(
            event_type=EVENT_TYPE_PATH_CHOICE_ORDINARY,
            payload={
                "cultivation_path": CULTIVATION_PATH_ORDINARY,
                "path_status": PATH_STATUS_CONFIRMED_ORDINARY,
                "stage_id": "middle",
            },
        )
        summary = "The anomaly is corrected; ordinary cultivation resumes."

    return CultivationResult(state=updated, events=(event,), summary=summary)
