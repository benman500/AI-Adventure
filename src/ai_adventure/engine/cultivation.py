"""Deterministic cultivation rules for Milestone 3 opening loop."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from ai_adventure.engine.constants import (
    ANOMALY_STATE_NONE,
    ANOMALY_STATE_RESOLVED,
    ANOMALY_STATE_TRIGGERED,
    BOUNDLESS_BREAKTHROUGH_THRESHOLD_MULTIPLIER,
    BOUNDLESS_PROGRESS_MULTIPLIER,
    BOUNDLESS_RESOURCE_COST_MULTIPLIER,
    BREAKTHROUGH_ATTEMPTED,
    BREAKTHROUGH_NOT_READY,
    BREAKTHROUGH_PROGRESS_THRESHOLD,
    BREAKTHROUGH_QI_THRESHOLD,
    BREAKTHROUGH_READY,
    CULTIVATION_METHOD_YIELDS,
    CULTIVATION_PATH_BOUNDLESS,
    CULTIVATION_PATH_ORDINARY,
    CULTIVATION_PROGRESS_MAX,
    EVENT_TYPE_BREAKTHROUGH_ATTEMPT,
    EVENT_TYPE_BREAKTHROUGH_READINESS,
    EVENT_TYPE_BREAKTHROUGH_SUCCESS,
    EVENT_TYPE_CULTIVATION_ANOMALY,
    EVENT_TYPE_CULTIVATION_PRACTICE,
    EVENT_TYPE_PATH_CHOICE_BOUNDLESS,
    EVENT_TYPE_PATH_CHOICE_ORDINARY,
    FOUNDATION_QUALITY_BANDS,
    ORDINARY_BREAKTHROUGH_THRESHOLD_MULTIPLIER,
    ORDINARY_PROGRESS_MULTIPLIER,
    ORDINARY_RESOURCE_COST_MULTIPLIER,
    PATH_STATUS_CONFIRMED_BOUNDLESS,
    PATH_STATUS_CONFIRMED_ORDINARY,
    PATH_STATUS_PROVISIONAL,
    REALM_DISPLAY_NAMES,
    STAGE_DISPLAY_NAMES,
    STARTING_STAGE_ID,
)
from ai_adventure.engine.errors import EngineValidationError


@dataclass(frozen=True, slots=True)
class CultivationState:
    """Player cultivation fields used by the engine."""

    cultivation_path: str
    path_status: str
    realm_id: str
    stage_id: str
    body: int
    qi: int
    soul: int
    dao: int
    foundation_quality: int
    qi_reserve_current: int
    qi_reserve_max: int
    cultivation_progress: int
    practice_sessions: int
    anomaly_state: str
    breakthrough_readiness: str


@dataclass(frozen=True, slots=True)
class CultivationEvent:
    """Structured event emitted by cultivation operations."""

    event_type: str
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class CultivationResult:
    """Outcome of a cultivation operation."""

    state: CultivationState
    events: tuple[CultivationEvent, ...]
    summary: str


def foundation_quality_label(value: int) -> str:
    """Map internal foundation quality to a qualitative band."""

    label = FOUNDATION_QUALITY_BANDS[0][1]
    for threshold, band in FOUNDATION_QUALITY_BANDS:
        if value >= threshold:
            label = band
    return label


def realm_stage_display(realm_id: str, stage_id: str) -> str:
    """Return player-facing realm and stage text."""

    realm = REALM_DISPLAY_NAMES.get(realm_id, realm_id.replace("_", " ").title())
    stage = STAGE_DISPLAY_NAMES.get(stage_id, stage_id.replace("_", " ").title())
    return f"{realm} ({stage})"


def _progress_multiplier(state: CultivationState) -> float:
    if state.cultivation_path == CULTIVATION_PATH_BOUNDLESS and state.path_status == PATH_STATUS_CONFIRMED_BOUNDLESS:
        return BOUNDLESS_PROGRESS_MULTIPLIER
    return ORDINARY_PROGRESS_MULTIPLIER


def _breakthrough_threshold_multiplier(state: CultivationState) -> float:
    if state.cultivation_path == CULTIVATION_PATH_BOUNDLESS and state.path_status == PATH_STATUS_CONFIRMED_BOUNDLESS:
        return BOUNDLESS_BREAKTHROUGH_THRESHOLD_MULTIPLIER
    return ORDINARY_BREAKTHROUGH_THRESHOLD_MULTIPLIER


def is_breakthrough_ready(state: CultivationState) -> bool:
    """True when qi and progress satisfy breakthrough thresholds."""

    return (
        state.qi_reserve_current >= BREAKTHROUGH_QI_THRESHOLD
        and state.cultivation_progress >= BREAKTHROUGH_PROGRESS_THRESHOLD
    )


def refresh_breakthrough_readiness(state: CultivationState) -> tuple[CultivationState, CultivationEvent | None]:
    """Update breakthrough readiness from current qi/progress (not session count)."""

    if state.breakthrough_readiness == BREAKTHROUGH_ATTEMPTED:
        return state, None
    if is_breakthrough_ready(state):
        if state.breakthrough_readiness != BREAKTHROUGH_READY:
            updated = replace(state, breakthrough_readiness=BREAKTHROUGH_READY)
            event = CultivationEvent(
                event_type=EVENT_TYPE_BREAKTHROUGH_READINESS,
                payload={
                    "qi_reserve_current": updated.qi_reserve_current,
                    "cultivation_progress": updated.cultivation_progress,
                },
            )
            return updated, event
        return state, None
    if state.breakthrough_readiness == BREAKTHROUGH_READY:
        return replace(state, breakthrough_readiness=BREAKTHROUGH_NOT_READY), None
    return state, None


def apply_cultivation_method(
    state: CultivationState,
    method_id: str,
) -> CultivationResult:
    """Run one cultivation method session (Absorb Qi, Stabilize Foundation, Calm Mind)."""

    if state.anomaly_state == ANOMALY_STATE_TRIGGERED:
        raise EngineValidationError("Cultivation is suspended until the anomaly is understood")
    if state.breakthrough_readiness == BREAKTHROUGH_ATTEMPTED and state.path_status == PATH_STATUS_PROVISIONAL:
        raise EngineValidationError("Await guidance before continuing cultivation")
    if method_id not in CULTIVATION_METHOD_YIELDS:
        raise EngineValidationError(f"Unknown cultivation method: {method_id}")

    qi_gain, progress_gain = CULTIVATION_METHOD_YIELDS[method_id]
    progress_gain = max(1, int(progress_gain * _progress_multiplier(state)))

    new_qi = min(state.qi_reserve_max, state.qi_reserve_current + qi_gain)
    new_progress = min(CULTIVATION_PROGRESS_MAX, state.cultivation_progress + progress_gain)
    updated = replace(
        state,
        qi_reserve_current=new_qi,
        cultivation_progress=new_progress,
        practice_sessions=state.practice_sessions + 1,
    )
    updated, readiness_event = refresh_breakthrough_readiness(updated)

    events: list[CultivationEvent] = [
        CultivationEvent(
            event_type=EVENT_TYPE_CULTIVATION_PRACTICE,
            payload={
                "method_id": method_id,
                "qi_gain": qi_gain,
                "progress_gain": progress_gain,
                "qi_reserve_current": updated.qi_reserve_current,
                "cultivation_progress": updated.cultivation_progress,
                "practice_sessions": updated.practice_sessions,
            },
        )
    ]
    if readiness_event is not None:
        events.append(readiness_event)

    return CultivationResult(
        state=updated,
        events=tuple(events),
        summary=f"Cultivation method {method_id.replace('_', ' ')} completed.",
    )


def attempt_breakthrough(state: CultivationState) -> CultivationResult:
    """First genuine breakthrough attempt; provisional path triggers the anomaly."""

    if not is_breakthrough_ready(state):
        raise EngineValidationError("Breakthrough readiness has not been reached")
    if state.breakthrough_readiness == BREAKTHROUGH_ATTEMPTED:
        raise EngineValidationError("Breakthrough has already been attempted")

    events: list[CultivationEvent] = [
        CultivationEvent(
            event_type=EVENT_TYPE_BREAKTHROUGH_ATTEMPT,
            payload={
                "realm_id": state.realm_id,
                "stage_id": state.stage_id,
                "qi_reserve_current": state.qi_reserve_current,
                "cultivation_progress": state.cultivation_progress,
            },
        )
    ]

    if state.path_status == PATH_STATUS_PROVISIONAL:
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
            summary="You gathered your Qi, reached for the breakthrough—and nothing happened.",
        )

    if state.cultivation_path == CULTIVATION_PATH_BOUNDLESS:
        threshold = int(BREAKTHROUGH_PROGRESS_THRESHOLD * _breakthrough_threshold_multiplier(state))
        if state.cultivation_progress < threshold:
            raise EngineValidationError("Insufficient foundation depth for a Boundless breakthrough")

    updated = _advance_stage(state)
    events.append(
        CultivationEvent(
            event_type=EVENT_TYPE_BREAKTHROUGH_SUCCESS,
            payload={
                "realm_id": updated.realm_id,
                "stage_id": updated.stage_id,
                "from_stage_id": state.stage_id,
            },
        )
    )
    updated = replace(
        updated,
        breakthrough_readiness=BREAKTHROUGH_NOT_READY,
        cultivation_progress=0,
        qi_reserve_current=0,
        anomaly_state=ANOMALY_STATE_RESOLVED if state.anomaly_state != ANOMALY_STATE_NONE else ANOMALY_STATE_NONE,
    )
    return CultivationResult(
        state=updated,
        events=tuple(events),
        summary=f"Breakthrough success: {realm_stage_display(updated.realm_id, updated.stage_id)}.",
    )


def commit_path_choice(state: CultivationState, *, choose_boundless: bool) -> CultivationResult:
    """Permanently confirm ordinary (fix) or Boundless Foundation path."""

    if state.path_status != PATH_STATUS_PROVISIONAL:
        raise EngineValidationError("Cultivation path has already been confirmed")
    if state.anomaly_state != ANOMALY_STATE_TRIGGERED:
        raise EngineValidationError("Path choice is not available yet")

    if choose_boundless:
        updated = replace(
            state,
            cultivation_path=CULTIVATION_PATH_BOUNDLESS,
            path_status=PATH_STATUS_CONFIRMED_BOUNDLESS,
            anomaly_state=ANOMALY_STATE_RESOLVED,
            foundation_quality=state.foundation_quality + 1,
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
        updated = replace(
            state,
            cultivation_path=CULTIVATION_PATH_ORDINARY,
            path_status=PATH_STATUS_CONFIRMED_ORDINARY,
            anomaly_state=ANOMALY_STATE_RESOLVED,
            stage_id="mid",
            cultivation_progress=0,
            qi_reserve_current=0,
            breakthrough_readiness=BREAKTHROUGH_NOT_READY,
        )
        event = CultivationEvent(
            event_type=EVENT_TYPE_PATH_CHOICE_ORDINARY,
            payload={
                "cultivation_path": CULTIVATION_PATH_ORDINARY,
                "path_status": PATH_STATUS_CONFIRMED_ORDINARY,
                "stage_id": "mid",
            },
        )
        summary = "The anomaly is corrected; ordinary cultivation resumes."

    return CultivationResult(state=updated, events=(event,), summary=summary)


def post_choice_practice(state: CultivationState, method_id: str) -> CultivationResult:
    """Practice after path confirmation to demonstrate divergent pacing."""

    result = apply_cultivation_method(state, method_id)
    return result


def cultivation_view(state: CultivationState) -> dict[str, Any]:
    """Player-visible cultivation facts (no CPI)."""

    return {
        "realm_stage": realm_stage_display(state.realm_id, state.stage_id),
        "realm_id": state.realm_id,
        "stage_id": state.stage_id,
        "cultivation_path": state.cultivation_path,
        "path_status": state.path_status,
        "qi_reserve_current": state.qi_reserve_current,
        "qi_reserve_max": state.qi_reserve_max,
        "cultivation_progress": state.cultivation_progress,
        "cultivation_progress_max": CULTIVATION_PROGRESS_MAX,
        "foundation_quality_label": foundation_quality_label(state.foundation_quality),
        "practice_sessions": state.practice_sessions,
        "breakthrough_readiness": state.breakthrough_readiness,
        "anomaly_state": state.anomaly_state,
        "breakthrough_ready": is_breakthrough_ready(state),
        "resource_cost_multiplier": (
            BOUNDLESS_RESOURCE_COST_MULTIPLIER
            if state.path_status == PATH_STATUS_CONFIRMED_BOUNDLESS
            else ORDINARY_RESOURCE_COST_MULTIPLIER
        ),
        "progress_multiplier": _progress_multiplier(state),
    }


def _advance_stage(state: CultivationState) -> CultivationState:
    """Advance one minor stage within Body Tempering for M3 demo."""

    stage_order = ["early", "mid", "late", "peak"]
    if state.stage_id not in stage_order:
        raise EngineValidationError(f"Unknown stage: {state.stage_id}")
    index = stage_order.index(state.stage_id)
    if index >= len(stage_order) - 1:
        return state
    return replace(state, stage_id=stage_order[index + 1])


def cultivation_state_from_player(player: object) -> CultivationState:
    """Build CultivationState from an ORM player row."""

    return CultivationState(
        cultivation_path=getattr(player, "cultivation_path"),
        path_status=getattr(player, "path_status", PATH_STATUS_PROVISIONAL),
        realm_id=getattr(player, "realm_id"),
        stage_id=getattr(player, "stage_id"),
        body=getattr(player, "body"),
        qi=getattr(player, "qi"),
        soul=getattr(player, "soul"),
        dao=getattr(player, "dao", 1),
        foundation_quality=getattr(player, "foundation_quality"),
        qi_reserve_current=getattr(player, "qi_reserve_current", 0),
        qi_reserve_max=getattr(player, "qi_reserve_max", 10),
        cultivation_progress=getattr(player, "cultivation_progress", 0),
        practice_sessions=getattr(player, "practice_sessions", 0),
        anomaly_state=getattr(player, "anomaly_state", ANOMALY_STATE_NONE),
        breakthrough_readiness=getattr(player, "breakthrough_readiness", BREAKTHROUGH_NOT_READY),
    )
