"""Core cultivation state, sync helpers, and player-facing view models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_adventure.engine.constants import (
    ANOMALY_STATE_NONE,
    BOUNDLESS_PROGRESS_MULTIPLIER,
    BOUNDLESS_RESOURCE_COST_MULTIPLIER,
    BREAKTHROUGH_NOT_READY,
    CULTIVATION_PROGRESS_MAX,
    ORDINARY_PROGRESS_MULTIPLIER,
    ORDINARY_RESOURCE_COST_MULTIPLIER,
    PATH_STATUS_CONFIRMED_BOUNDLESS,
    PATH_STATUS_PROVISIONAL,
    REALM_COMPREHENSION_MAX,
    STARTING_FOUNDATION_STABILITY,
    STARTING_REALM_COMPREHENSION,
)
from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.foundation import foundation_quality_label
from ai_adventure.engine.realms import (
    get_realm,
    get_stage,
    normalize_realm_id,
    normalize_stage_id,
    realm_display_name,
    stage_display_name,
)


def _breakthrough_ready_flag(state: CultivationState) -> bool:
    """Lazy import avoids circular dependency with cultivation_path."""

    from ai_adventure.engine.cultivation_path import is_breakthrough_ready

    return is_breakthrough_ready(state)


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
    realm_comprehension: int
    foundation_stability: int
    practice_sessions: int
    anomaly_state: str
    breakthrough_readiness: str
    breakthrough_attempts_current_stage: int = 0


@dataclass(frozen=True, slots=True)
class CultivationEvent:
    """Structured event emitted by cultivation operations."""

    event_type: str
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class CultivationResult:
    """Outcome of a cultivation operation (legacy/path helpers)."""

    state: CultivationState
    events: tuple[CultivationEvent, ...]
    summary: str


def clamp_int(value: int, minimum: int, maximum: int) -> int:
    """Clamp an integer into an inclusive range."""

    return max(minimum, min(maximum, value))


def progress_multiplier(state: CultivationState) -> float:
    """Ordinary vs Boundless progress multiplier."""

    if (
        state.cultivation_path == "boundless"
        and state.path_status == PATH_STATUS_CONFIRMED_BOUNDLESS
    ):
        return BOUNDLESS_PROGRESS_MULTIPLIER
    return ORDINARY_PROGRESS_MULTIPLIER


def sync_qi_reserve_max(state: CultivationState) -> CultivationState:
    """Ensure qi_reserve_max is at least the realm catalog base_qi_max.

    Preserves intentional character bonuses already stored above the catalog floor.
    """

    from dataclasses import replace

    realm = get_realm(normalize_realm_id(state.realm_id))
    floor = realm.base_qi_max
    new_max = max(state.qi_reserve_max, floor)
    if new_max == state.qi_reserve_max:
        return state
    return replace(
        state,
        qi_reserve_max=new_max,
        qi_reserve_current=min(state.qi_reserve_current, new_max),
    )


def cultivation_state_from_player(player: object) -> CultivationState:
    """Build CultivationState from an ORM player row, syncing realm qi floor."""

    state = CultivationState(
        cultivation_path=getattr(player, "cultivation_path"),
        path_status=getattr(player, "path_status", PATH_STATUS_PROVISIONAL),
        realm_id=normalize_realm_id(getattr(player, "realm_id")),
        stage_id=normalize_stage_id(getattr(player, "stage_id")),
        body=getattr(player, "body"),
        qi=getattr(player, "qi"),
        soul=getattr(player, "soul"),
        dao=getattr(player, "dao", 1),
        foundation_quality=getattr(player, "foundation_quality"),
        qi_reserve_current=getattr(player, "qi_reserve_current", 0),
        qi_reserve_max=getattr(player, "qi_reserve_max", 10),
        cultivation_progress=getattr(player, "cultivation_progress", 0),
        realm_comprehension=getattr(player, "realm_comprehension", STARTING_REALM_COMPREHENSION),
        foundation_stability=getattr(player, "foundation_stability", STARTING_FOUNDATION_STABILITY),
        practice_sessions=getattr(player, "practice_sessions", 0),
        anomaly_state=getattr(player, "anomaly_state", ANOMALY_STATE_NONE),
        breakthrough_readiness=getattr(player, "breakthrough_readiness", BREAKTHROUGH_NOT_READY),
        breakthrough_attempts_current_stage=getattr(
            player, "breakthrough_attempts_current_stage", 0
        ),
    )
    return sync_qi_reserve_max(state)


def cultivation_view(state: CultivationState) -> dict[str, Any]:
    """Player-visible cultivation facts (no CPI)."""

    state = sync_qi_reserve_max(state)
    realm_name = (
        realm_display_name(state.realm_id)
        if _safe_realm(state.realm_id)
        else state.realm_id
    )
    stage_name = (
        stage_display_name(state.stage_id)
        if _safe_stage(state.stage_id)
        else state.stage_id
    )

    return {
        "realm_stage": f"{realm_name} ({stage_name})",
        "realm_id": state.realm_id,
        "realm_name": realm_name,
        "stage_id": normalize_stage_id(state.stage_id),
        "stage_name": stage_name,
        "cultivation_path": state.cultivation_path,
        "path_status": state.path_status,
        "qi_current": state.qi_reserve_current,
        "qi_max": state.qi_reserve_max,
        "qi_reserve_current": state.qi_reserve_current,
        "qi_reserve_max": state.qi_reserve_max,
        "cultivation_progress": state.cultivation_progress,
        "cultivation_progress_max": CULTIVATION_PROGRESS_MAX,
        "realm_comprehension": state.realm_comprehension,
        "realm_comprehension_max": REALM_COMPREHENSION_MAX,
        "foundation_stability": state.foundation_stability,
        "foundation_stability_max": 100,
        "foundation_quality": state.foundation_quality,
        "foundation_quality_label": foundation_quality_label(state.foundation_quality),
        "practice_sessions": state.practice_sessions,
        "breakthrough_readiness": state.breakthrough_readiness,
        "breakthrough_ready": _breakthrough_ready_flag(state),
        "anomaly_state": state.anomaly_state,
        "resource_cost_multiplier": (
            BOUNDLESS_RESOURCE_COST_MULTIPLIER
            if state.path_status == PATH_STATUS_CONFIRMED_BOUNDLESS
            else ORDINARY_RESOURCE_COST_MULTIPLIER
        ),
        "progress_multiplier": progress_multiplier(state),
    }


def _safe_realm(realm_id: str) -> bool:
    try:
        get_realm(realm_id)
        return True
    except EngineValidationError:
        return False


def _safe_stage(stage_id: str) -> bool:
    try:
        get_stage(stage_id)
        return True
    except EngineValidationError:
        return False
