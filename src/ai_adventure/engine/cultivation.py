"""Cultivation facade: re-exports framework + legacy helpers.

Prefer importing from:
- ``cultivation_state`` — meters / view
- ``cultivation_path`` — Milestone 3 anomaly / path choice
- ``cultivation_sessions`` — active Cautious/Balanced/Aggressive sessions
"""

from __future__ import annotations

from dataclasses import replace

from ai_adventure.engine.constants import (
    CULTIVATION_METHOD_YIELDS,
    CULTIVATION_PROGRESS_MAX,
    EVENT_TYPE_CULTIVATION_PRACTICE,
    REALM_COMPREHENSION_MAX,
)
from ai_adventure.engine.cultivation_path import (
    attempt_breakthrough,
    commit_path_choice,
    is_breakthrough_ready,
    refresh_breakthrough_readiness,
)
from ai_adventure.engine.breakthroughs import (
    evaluate_breakthrough_readiness,
    run_breakthrough_attempt,
)
from ai_adventure.engine.cultivation_sessions import (
    CultivationSessionResult,
    cultivation_availability,
    get_session_method,
    list_session_methods,
    run_cultivation_session,
    session_result_to_dict,
)
from ai_adventure.engine.cultivation_state import (
    CultivationEvent,
    CultivationResult,
    CultivationState,
    clamp_int,
    cultivation_state_from_player,
    cultivation_view,
    progress_multiplier,
    sync_qi_reserve_max,
)
from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.foundation import clamp_stability, sync_foundation_quality


def apply_cultivation_method(
    state: CultivationState,
    method_id: str,
) -> CultivationResult:
    """Legacy Milestone 3 method yields (Absorb Qi / Stabilize / Calm Mind).

    Prefer ``run_cultivation_session`` for new Cautious/Balanced/Aggressive play.
    Kept for opening-story compatibility and older tests.
    """

    from ai_adventure.engine.cultivation_sessions import cultivation_availability

    allowed, reason = cultivation_availability(state)
    if not allowed:
        raise EngineValidationError(reason or "Cultivation is unavailable")
    if method_id not in CULTIVATION_METHOD_YIELDS:
        # Delegate session methods through the session runner for convenience.
        if method_id in {m.id for m in list_session_methods()}:
            session = run_cultivation_session(state, method_id)
            if session.outcome_type == "blocked":
                raise EngineValidationError(session.blocked_reason or "Cultivation blocked")
            return CultivationResult(
                state=session.state,
                events=session.events,
                summary=session.summary,
            )
        raise EngineValidationError(f"Unknown cultivation method: {method_id}")

    state = sync_qi_reserve_max(state)
    qi_gain, progress_gain, comprehension_gain, stability_delta = CULTIVATION_METHOD_YIELDS[method_id]
    progress_gain = max(1, int(progress_gain * progress_multiplier(state)))

    new_qi = min(state.qi_reserve_max, state.qi_reserve_current + qi_gain)
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
                "method_id": method_id,
                "qi_gain": qi_gain,
                "progress_gain": progress_gain,
                "comprehension_gain": comprehension_gain,
                "foundation_stability_delta": stability_delta,
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


def attempt_realm_breakthrough(
    state: CultivationState,
    *,
    rng=None,
) -> CultivationResult:
    """Attempt Peak → next playable realm via the Phase 3 breakthrough engine."""

    from ai_adventure.engine.breakthroughs import run_breakthrough_attempt
    from ai_adventure.engine.realms import normalize_stage_id

    if normalize_stage_id(state.stage_id) != "peak":
        raise EngineValidationError("Realm breakthrough requires Peak stage")
    result = run_breakthrough_attempt(state, rng=rng)
    if result.outcome_type == "blocked":
        raise EngineValidationError(result.blocked_reason or "Realm breakthrough unavailable")
    return CultivationResult(
        state=result.state,
        events=result.events,
        summary=result.summary,
    )


def post_choice_practice(state: CultivationState, method_id: str) -> CultivationResult:
    """Practice after path confirmation."""

    return apply_cultivation_method(state, method_id)


__all__ = [
    "CultivationEvent",
    "CultivationResult",
    "CultivationSessionResult",
    "CultivationState",
    "apply_cultivation_method",
    "attempt_breakthrough",
    "attempt_realm_breakthrough",
    "commit_path_choice",
    "cultivation_availability",
    "cultivation_state_from_player",
    "cultivation_view",
    "evaluate_breakthrough_readiness",
    "get_session_method",
    "is_breakthrough_ready",
    "list_session_methods",
    "post_choice_practice",
    "refresh_breakthrough_readiness",
    "run_breakthrough_attempt",
    "run_cultivation_session",
    "session_result_to_dict",
    "sync_qi_reserve_max",
]
