"""Active cultivation sessions (Cautious / Balanced / Aggressive).

Data-driven methods in ``data/cultivation/session_methods.json``.
RNG is injectable for deterministic tests.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from random import Random
from typing import Any, Literal

from pydantic import BaseModel, Field

from ai_adventure.engine.constants import (
    ANOMALY_STATE_TRIGGERED,
    BREAKTHROUGH_ATTEMPTED,
    CULTIVATION_PROGRESS_MAX,
    EVENT_TYPE_CULTIVATION_PRACTICE,
    PATH_STATUS_PROVISIONAL,
    REALM_COMPREHENSION_MAX,
)
from ai_adventure.engine.cultivation_path import (
    is_breakthrough_ready,
    refresh_breakthrough_readiness,
)
from ai_adventure.engine.cultivation_state import (
    CultivationEvent,
    CultivationState,
    clamp_int,
    progress_multiplier,
    sync_qi_reserve_max,
)
from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.foundation import clamp_stability, sync_foundation_quality
from ai_adventure.engine.modifiers import ModifierSnapshot, consumer_number

_METHODS_PATH = Path(__file__).resolve().parents[1] / "data" / "cultivation" / "session_methods.json"

# Explicit consumer allowlist — unsupported snapshot keys are ignored, never interpreted.
SESSION_SUPPORTED_EFFECT_TYPES: frozenset[str] = frozenset(
    {
        "session_progress_mult",
        "session_qi_gain_mult",
        "session_stability_flat",
        "comprehension_gain_mult",
    }
)

OutcomeType = Literal["success", "setback", "blocked"]


class SessionMethodDefinition(BaseModel):
    """One active cultivation posture."""

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    description: str = Field(min_length=1)
    qi_gain: int = Field(ge=0)
    progress_gain: int = Field(ge=0)
    comprehension_gain: int = Field(ge=0)
    stability_delta: int = 0
    stability_improve_chance: float = Field(ge=0.0, le=1.0)
    setback_chance: float = Field(ge=0.0, le=1.0)
    setback_qi_loss: int = Field(ge=0)
    setback_progress_penalty: int = Field(ge=0)
    setback_stability_loss: int = Field(ge=0)
    risk_level: str = Field(min_length=1)
    time_cost_days: int = Field(ge=0)
    playtime_seconds: int = Field(ge=0)


class SessionMethodCatalog(BaseModel):
    """Catalog of active cultivation methods."""

    methods: list[SessionMethodDefinition] = Field(min_length=1)


@dataclass(frozen=True, slots=True)
class CultivationSessionResult:
    """Structured backend result for one cultivation session."""

    method_id: str
    method_label: str
    outcome_type: OutcomeType
    qi_before: int
    qi_after: int
    progress_before: int
    progress_after: int
    comprehension_before: int
    comprehension_after: int
    stability_before: int
    stability_after: int
    time_consumed_days: int
    playtime_seconds: int
    summary: str
    setback: bool
    setback_description: str | None
    state: CultivationState
    events: tuple[CultivationEvent, ...]
    blocked_reason: str | None = None


@lru_cache(maxsize=1)
def load_session_methods(path: str | None = None) -> dict[str, SessionMethodDefinition]:
    """Load active cultivation method definitions."""

    catalog_path = Path(path) if path else _METHODS_PATH
    if not catalog_path.is_file():
        raise EngineValidationError(f"Session methods missing: {catalog_path}")
    try:
        raw = json.loads(catalog_path.read_text(encoding="utf-8"))
        catalog = SessionMethodCatalog.model_validate(raw)
    except Exception as exc:  # noqa: BLE001
        raise EngineValidationError(f"Invalid session methods: {exc}") from exc
    return {item.id: item for item in catalog.methods}


def clear_session_methods_cache() -> None:
    """Clear cached session methods (tests)."""

    load_session_methods.cache_clear()


def list_session_methods(path: str | None = None) -> list[SessionMethodDefinition]:
    """Return methods in catalog order."""

    return list(load_session_methods(path).values())


def get_session_method(method_id: str, path: str | None = None) -> SessionMethodDefinition:
    """Return one method or raise."""

    methods = load_session_methods(path)
    try:
        return methods[method_id]
    except KeyError as exc:
        raise EngineValidationError(f"Unknown cultivation method: {method_id}") from exc


def cultivation_availability(state: CultivationState) -> tuple[bool, str | None]:
    """Return whether cultivation is allowed and a player-facing reason if not."""

    if state.anomaly_state == ANOMALY_STATE_TRIGGERED:
        return False, "Cultivation is suspended until the anomaly is understood."
    if (
        state.breakthrough_readiness == BREAKTHROUGH_ATTEMPTED
        and state.path_status == PATH_STATUS_PROVISIONAL
    ):
        return False, "Await guidance before continuing cultivation."
    return True, None


def apply_session_modifier_snapshot(
    *,
    progress_gain: int,
    qi_gain: int,
    comprehension_gain: int,
    stability_delta: int,
    modifiers: ModifierSnapshot | None,
) -> tuple[int, int, int, int]:
    """Apply resolved session modifiers. Consumer understands snapshot only.

    Supported effect types (only): ``SESSION_SUPPORTED_EFFECT_TYPES``.
    Any other keys present on the snapshot are ignored.
    """

    if modifiers is None:
        return progress_gain, qi_gain, comprehension_gain, stability_delta

    progress_mult = consumer_number(
        modifiers,
        "session_progress_mult",
        supported=SESSION_SUPPORTED_EFFECT_TYPES,
        default=1.0,
    )
    qi_mult = consumer_number(
        modifiers,
        "session_qi_gain_mult",
        supported=SESSION_SUPPORTED_EFFECT_TYPES,
        default=1.0,
    )
    comprehension_mult = consumer_number(
        modifiers,
        "comprehension_gain_mult",
        supported=SESSION_SUPPORTED_EFFECT_TYPES,
        default=1.0,
    )
    stability_flat = consumer_number(
        modifiers,
        "session_stability_flat",
        supported=SESSION_SUPPORTED_EFFECT_TYPES,
        default=0.0,
    )

    return (
        max(0, int(progress_gain * progress_mult)),
        max(0, int(qi_gain * qi_mult)),
        max(0, int(comprehension_gain * comprehension_mult)),
        int(stability_delta + stability_flat),
    )


def run_cultivation_session(
    state: CultivationState,
    method_id: str,
    *,
    rng: Random | None = None,
    methods_path: str | None = None,
    modifiers: ModifierSnapshot | None = None,
) -> CultivationSessionResult:
    """Execute one Cautious/Balanced/Aggressive cultivation session.

    ``modifiers`` is an ephemeral ``ModifierSnapshot``. This function must not
    inspect technique catalogs, mastery tables, or effect bundles.
    """

    state = sync_qi_reserve_max(state)
    allowed, reason = cultivation_availability(state)
    method = get_session_method(method_id, methods_path)

    if not allowed:
        return CultivationSessionResult(
            method_id=method.id,
            method_label=method.label,
            outcome_type="blocked",
            qi_before=state.qi_reserve_current,
            qi_after=state.qi_reserve_current,
            progress_before=state.cultivation_progress,
            progress_after=state.cultivation_progress,
            comprehension_before=state.realm_comprehension,
            comprehension_after=state.realm_comprehension,
            stability_before=state.foundation_stability,
            stability_after=state.foundation_stability,
            time_consumed_days=0,
            playtime_seconds=0,
            summary=reason or "Cultivation is unavailable.",
            setback=False,
            setback_description=None,
            state=state,
            events=(),
            blocked_reason=reason,
        )

    rng = rng or Random()
    qi_before = state.qi_reserve_current
    progress_before = state.cultivation_progress
    comprehension_before = state.realm_comprehension
    stability_before = state.foundation_stability

    progress_gain = max(0, int(method.progress_gain * progress_multiplier(state)))
    qi_gain = method.qi_gain
    comprehension_gain = method.comprehension_gain
    stability_delta = method.stability_delta

    progress_gain, qi_gain, comprehension_gain, stability_delta = apply_session_modifier_snapshot(
        progress_gain=progress_gain,
        qi_gain=qi_gain,
        comprehension_gain=comprehension_gain,
        stability_delta=stability_delta,
        modifiers=modifiers,
    )

    if method.stability_improve_chance > 0 and rng.random() < method.stability_improve_chance:
        stability_delta = max(stability_delta, 1)

    setback = False
    setback_description: str | None = None
    if method.setback_chance > 0 and rng.random() < method.setback_chance:
        setback = True
        qi_gain = max(0, qi_gain - method.setback_qi_loss)
        progress_gain = max(0, progress_gain - method.setback_progress_penalty)
        stability_delta -= method.setback_stability_loss
        setback_description = (
            "A minor cultivation setback disrupts your circulation—"
            "some Qi slips away and your foundation wavers."
        )

    new_qi = min(state.qi_reserve_max, state.qi_reserve_current + qi_gain)
    # Progress stays capped at 100; further sessions may still gain Qi/comprehension.
    new_progress = min(CULTIVATION_PROGRESS_MAX, state.cultivation_progress + progress_gain)
    new_comprehension = clamp_int(
        state.realm_comprehension + comprehension_gain,
        0,
        REALM_COMPREHENSION_MAX,
    )
    new_stability = clamp_stability(state.foundation_stability + stability_delta)
    new_quality = sync_foundation_quality(new_stability, state.foundation_quality)

    updated = replace(
        state,
        qi_reserve_current=new_qi,
        cultivation_progress=new_progress,
        realm_comprehension=new_comprehension,
        foundation_stability=new_stability,
        foundation_quality=new_quality,
        practice_sessions=state.practice_sessions + 1,
    )
    updated, readiness_event = refresh_breakthrough_readiness(updated)

    events: list[CultivationEvent] = [
        CultivationEvent(
            event_type=EVENT_TYPE_CULTIVATION_PRACTICE,
            payload={
                "method_id": method.id,
                "outcome_type": "setback" if setback else "success",
                "qi_gain": qi_gain,
                "progress_gain": progress_gain,
                "comprehension_gain": comprehension_gain,
                "foundation_stability_delta": new_stability - stability_before,
                "time_cost_days": method.time_cost_days,
                "playtime_seconds": method.playtime_seconds,
                "modifiers_applied": modifiers is not None and (
                    bool(modifiers.numbers) or bool(modifiers.flags)
                ),
            },
        )
    ]
    if readiness_event is not None:
        events.append(readiness_event)

    if setback:
        summary = (
            f"{method.label} cultivation ends in a minor setback. "
            f"{setback_description}"
        )
        outcome: OutcomeType = "setback"
    else:
        summary = (
            f"{method.label} cultivation completes. "
            f"Qi {qi_before}→{new_qi}, progress {progress_before}→{new_progress}."
        )
        outcome = "success"

    return CultivationSessionResult(
        method_id=method.id,
        method_label=method.label,
        outcome_type=outcome,
        qi_before=qi_before,
        qi_after=new_qi,
        progress_before=progress_before,
        progress_after=new_progress,
        comprehension_before=comprehension_before,
        comprehension_after=new_comprehension,
        stability_before=stability_before,
        stability_after=new_stability,
        time_consumed_days=method.time_cost_days,
        playtime_seconds=method.playtime_seconds,
        summary=summary,
        setback=setback,
        setback_description=setback_description,
        state=updated,
        events=tuple(events),
        blocked_reason=None,
    )


def session_result_to_dict(result: CultivationSessionResult) -> dict[str, Any]:
    """Serialize a session result for persistence / templates."""

    return {
        "method_id": result.method_id,
        "method_label": result.method_label,
        "outcome_type": result.outcome_type,
        "qi_before": result.qi_before,
        "qi_after": result.qi_after,
        "progress_before": result.progress_before,
        "progress_after": result.progress_after,
        "comprehension_before": result.comprehension_before,
        "comprehension_after": result.comprehension_after,
        "stability_before": result.stability_before,
        "stability_after": result.stability_after,
        "time_consumed_days": result.time_consumed_days,
        "playtime_seconds": result.playtime_seconds,
        "summary": result.summary,
        "setback": result.setback,
        "setback_description": result.setback_description,
        "blocked_reason": result.blocked_reason,
    }


# TODO(Phase 7+): spiritual roots / consumables as additional modifier sources.
# TODO(Phase 12): AI-generated cultivation encounters after engine outcome is fixed.
