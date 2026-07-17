"""Phase 3 breakthrough readiness, chance, and stage/realm advancement.

Milestone 3 provisional anomaly attempts remain in ``cultivation_path`` and are
reached through the adapter in ``attempt_stage_or_opening_breakthrough``.
Generic stage advancement never bypasses story-gated provisional path logic.

Architecture hooks (not implemented here): spiritual roots, pills, tribulations,
environmental modifiers, AI-generated breakthrough narration.
Techniques affect breakthrough chance only via ``ModifierSnapshot``
(``BREAKTHROUGH_SUPPORTED_EFFECT_TYPES``); Boundless path math stays outside modifiers.
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
    BREAKTHROUGH_NOT_READY,
    BREAKTHROUGH_QI_THRESHOLD,
    BREAKTHROUGH_READY,
    BREAKTHROUGH_PROGRESS_THRESHOLD,
    CULTIVATION_PATH_BOUNDLESS,
    CULTIVATION_PROGRESS_MAX,
    EVENT_TYPE_BREAKTHROUGH_ATTEMPT,
    EVENT_TYPE_BREAKTHROUGH_SUCCESS,
    PATH_STATUS_PROVISIONAL,
    REALM_COMPREHENSION_MAX,
)
from ai_adventure.engine.cultivation_sessions import cultivation_availability
from ai_adventure.engine.cultivation_state import CultivationEvent, CultivationState, clamp_int, sync_qi_reserve_max
from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.foundation import clamp_stability, sync_foundation_quality
from ai_adventure.engine.modifiers import ModifierSnapshot, consumer_number
from ai_adventure.engine.realms import (
    get_realm,
    list_realms,
    next_stage_id,
    normalize_realm_id,
    normalize_stage_id,
    realm_display_name,
    stage_display_name,
)

_BREAKTHROUGHS_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "cultivation" / "breakthroughs.json"
)

# Explicit consumer allowlist — unsupported snapshot keys are ignored, never interpreted.
BREAKTHROUGH_SUPPORTED_EFFECT_TYPES: frozenset[str] = frozenset(
    {
        "breakthrough_chance_flat",
    }
)

OutcomeType = Literal["success", "failure", "blocked", "opening_anomaly"]
ChanceBand = Literal["Very Low", "Low", "Moderate", "High", "Very High"]


class BreakthroughTransitionDefinition(BaseModel):
    """One stage or realm transition rule."""

    id: str = Field(min_length=1)
    from_stage_id: str = Field(min_length=1)
    to_stage_id: str = Field(min_length=1)
    to_realm_id: str | None = None
    progress_required: int = Field(ge=0, le=100)
    comprehension_required: int = Field(ge=0, le=100)
    stability_recommended: int = Field(ge=0, le=100)
    qi_cost_percent_of_max: int = Field(ge=0, le=100)
    base_success_chance: float = Field(gt=0.0, lt=1.0)
    base_difficulty: str = Field(min_length=1)
    stability_strongly_affects: bool = False
    allows_realm_change: bool = False


class BreakthroughCatalog(BaseModel):
    """Global breakthrough tuning + transitions."""

    chance_clamp_min: float = Field(ge=0.0, le=1.0)
    chance_clamp_max: float = Field(ge=0.0, le=1.0)
    comprehension_carry_ratio: float = Field(ge=0.0, le=1.0)
    failure_qi_cost_ratio: float = Field(ge=0.0, le=1.0)
    failure_stability_loss: int = Field(ge=0)
    failure_progress_loss: int = Field(ge=0)
    failed_attempt_chance_penalty: float = Field(ge=0.0)
    excess_comprehension_bonus_per_point: float = Field(ge=0.0)
    stability_bonus_per_point_from_50: float = Field(ge=0.0)
    qi_surplus_bonus_cap: float = Field(ge=0.0)
    boundless_chance_multiplier: float = Field(gt=0.0, le=1.0)
    transitions: list[BreakthroughTransitionDefinition] = Field(min_length=1)


@dataclass(frozen=True, slots=True)
class BreakthroughReadiness:
    """Structured readiness for the next breakthrough transition."""

    eligible: bool
    transition_id: str | None
    target_realm_id: str | None
    target_stage_id: str | None
    target_realm_name: str | None
    target_stage_name: str | None
    progress_required: int
    progress_current: int
    comprehension_required: int
    comprehension_current: int
    stability_recommended: int
    stability_current: int
    qi_cost: int
    qi_current: int
    qi_max: int
    success_chance: float
    success_chance_band: ChanceBand
    success_chance_percent: int
    warnings: tuple[str, ...]
    blocking_reasons: tuple[str, ...]
    mode: Literal["opening", "stage", "realm", "none"]
    base_difficulty: str | None = None


@dataclass(frozen=True, slots=True)
class BreakthroughAttemptResult:
    """Structured result of one breakthrough attempt."""

    outcome_type: OutcomeType
    transition_id: str | None
    success: bool
    qi_before: int
    qi_after: int
    progress_before: int
    progress_after: int
    comprehension_before: int
    comprehension_after: int
    stability_before: int
    stability_after: int
    realm_before: str
    realm_after: str
    stage_before: str
    stage_after: str
    success_chance: float
    roll: float | None
    summary: str
    state: CultivationState
    events: tuple[CultivationEvent, ...]
    blocked_reason: str | None = None
    attempts_before: int = 0
    attempts_after: int = 0


@lru_cache(maxsize=1)
def load_breakthrough_catalog(path: str | None = None) -> BreakthroughCatalog:
    """Load data-driven breakthrough definitions."""

    catalog_path = Path(path) if path else _BREAKTHROUGHS_PATH
    if not catalog_path.is_file():
        raise EngineValidationError(f"Breakthrough catalog missing: {catalog_path}")
    try:
        raw = json.loads(catalog_path.read_text(encoding="utf-8"))
        return BreakthroughCatalog.model_validate(raw)
    except Exception as exc:  # noqa: BLE001
        raise EngineValidationError(f"Invalid breakthrough catalog: {exc}") from exc


def clear_breakthrough_catalog_cache() -> None:
    """Clear cached breakthrough catalog (tests)."""

    load_breakthrough_catalog.cache_clear()


def qi_cost_for_transition(qi_max: int, percent: int) -> int:
    """Compute Qi cost as a percentage of max, at least 1 when percent > 0."""

    if percent <= 0:
        return 0
    return max(1, (qi_max * percent + 99) // 100)


def chance_band(chance: float) -> ChanceBand:
    """Map a probability into a coarse player-facing band."""

    if chance < 0.2:
        return "Very Low"
    if chance < 0.4:
        return "Low"
    if chance < 0.6:
        return "Moderate"
    if chance < 0.8:
        return "High"
    return "Very High"


def next_playable_realm_id(realm_id: str) -> str | None:
    """Return the next playable realm after ``realm_id``, if any."""

    playable = list_realms(playable_only=True)
    current = normalize_realm_id(realm_id)
    ids = [item.id for item in playable]
    if current not in ids:
        return None
    index = ids.index(current)
    if index >= len(ids) - 1:
        return None
    return ids[index + 1]


def resolve_transition_target(
    state: CultivationState,
    transition: BreakthroughTransitionDefinition,
) -> tuple[str, str] | None:
    """Resolve target realm/stage for a transition, or None if blocked by ladder end."""

    from_stage = normalize_stage_id(state.stage_id)
    if from_stage != transition.from_stage_id:
        return None

    if transition.allows_realm_change:
        if from_stage != "peak":
            return None
        nxt = next_playable_realm_id(state.realm_id)
        if nxt is None:
            # Already at the highest implemented playable realm (Qi Gathering Peak).
            return None
        return nxt, transition.to_stage_id

    nxt_stage = next_stage_id(state.stage_id)
    if nxt_stage is None or nxt_stage != transition.to_stage_id:
        return None
    return normalize_realm_id(state.realm_id), nxt_stage


def find_transition_for_state(
    state: CultivationState,
    *,
    catalog: BreakthroughCatalog | None = None,
) -> BreakthroughTransitionDefinition | None:
    """Find the catalog transition matching the player's current stage."""

    catalog = catalog or load_breakthrough_catalog()
    stage = normalize_stage_id(state.stage_id)
    for transition in catalog.transitions:
        if transition.from_stage_id != stage:
            continue
        if resolve_transition_target(state, transition) is not None:
            return transition
    return None


def calculate_success_chance(
    state: CultivationState,
    transition: BreakthroughTransitionDefinition,
    *,
    qi_cost: int,
    catalog: BreakthroughCatalog | None = None,
    modifiers: ModifierSnapshot | None = None,
) -> float:
    """Backend-owned success probability for a transition.

    Optional ``modifiers`` may contribute ``breakthrough_chance_flat`` only
    (see ``BREAKTHROUGH_SUPPORTED_EFFECT_TYPES``). Boundless path multipliers
    remain outside the Modifier Framework.
    """

    catalog = catalog or load_breakthrough_catalog()
    chance = transition.base_success_chance

    excess_comp = max(0, state.realm_comprehension - transition.comprehension_required)
    chance += excess_comp * catalog.excess_comprehension_bonus_per_point

    stability_delta = state.foundation_stability - 50
    weight = 2.0 if transition.stability_strongly_affects else 1.0
    chance += stability_delta * catalog.stability_bonus_per_point_from_50 * weight

    if qi_cost > 0 and state.qi_reserve_current > qi_cost:
        surplus_ratio = (state.qi_reserve_current - qi_cost) / max(1, state.qi_reserve_max)
        chance += min(catalog.qi_surplus_bonus_cap, surplus_ratio * 0.1)

    attempts = getattr(state, "breakthrough_attempts_current_stage", 0) or 0
    chance -= attempts * catalog.failed_attempt_chance_penalty

    if (
        state.cultivation_path == CULTIVATION_PATH_BOUNDLESS
        and state.path_status != PATH_STATUS_PROVISIONAL
    ):
        chance *= catalog.boundless_chance_multiplier

    chance += consumer_number(
        modifiers,
        "breakthrough_chance_flat",
        supported=BREAKTHROUGH_SUPPORTED_EFFECT_TYPES,
        default=0.0,
    )

    return max(catalog.chance_clamp_min, min(catalog.chance_clamp_max, chance))


def evaluate_breakthrough_readiness(
    state: CultivationState,
    *,
    catalog: BreakthroughCatalog | None = None,
    modifiers: ModifierSnapshot | None = None,
) -> BreakthroughReadiness:
    """Compute structured breakthrough readiness (never in templates).

    ``modifiers`` is an ephemeral ``ModifierSnapshot`` for activity
    ``breakthrough``. This function must not inspect technique tables.
    """

    catalog = catalog or load_breakthrough_catalog()
    state = sync_qi_reserve_max(state)
    warnings: list[str] = []
    blocking: list[str] = []

    # Opening-story provisional path uses M3 thresholds and must not run generic stage math.
    if state.path_status == PATH_STATUS_PROVISIONAL:
        return _opening_readiness(state, warnings=warnings, blocking=blocking)

    allowed, reason = cultivation_availability(state)
    if not allowed and reason:
        blocking.append(reason)

    if state.anomaly_state == ANOMALY_STATE_TRIGGERED:
        blocking.append("Story gate: resolve the cultivation anomaly before advancing.")

    transition = find_transition_for_state(state, catalog=catalog)
    if transition is None:
        blocking.append("No further stage or realm advancement is implemented from this point.")
        return BreakthroughReadiness(
            eligible=False,
            transition_id=None,
            target_realm_id=None,
            target_stage_id=None,
            target_realm_name=None,
            target_stage_name=None,
            progress_required=CULTIVATION_PROGRESS_MAX,
            progress_current=state.cultivation_progress,
            comprehension_required=0,
            comprehension_current=state.realm_comprehension,
            stability_recommended=0,
            stability_current=state.foundation_stability,
            qi_cost=0,
            qi_current=state.qi_reserve_current,
            qi_max=state.qi_reserve_max,
            success_chance=0.0,
            success_chance_band="Very Low",
            success_chance_percent=0,
            warnings=tuple(warnings),
            blocking_reasons=tuple(blocking),
            mode="none",
        )

    target = resolve_transition_target(state, transition)
    assert target is not None
    target_realm_id, target_stage_id = target
    qi_cost = qi_cost_for_transition(state.qi_reserve_max, transition.qi_cost_percent_of_max)

    if state.cultivation_progress < transition.progress_required:
        blocking.append(
            f"Cultivation progress {state.cultivation_progress}/{transition.progress_required}."
        )
    if state.realm_comprehension < transition.comprehension_required:
        blocking.append(
            f"Realm comprehension {state.realm_comprehension}/{transition.comprehension_required}."
        )
    if state.qi_reserve_current < qi_cost:
        blocking.append(f"Qi {state.qi_reserve_current}/{qi_cost} required.")

    if state.foundation_stability < transition.stability_recommended:
        warnings.append(
            f"Foundation stability {state.foundation_stability} is below the "
            f"recommended {transition.stability_recommended}."
        )

    chance = calculate_success_chance(
        state,
        transition,
        qi_cost=qi_cost,
        catalog=catalog,
        modifiers=modifiers,
    )
    mode: Literal["stage", "realm"] = "realm" if transition.allows_realm_change else "stage"

    return BreakthroughReadiness(
        eligible=len(blocking) == 0,
        transition_id=transition.id,
        target_realm_id=target_realm_id,
        target_stage_id=target_stage_id,
        target_realm_name=realm_display_name(target_realm_id),
        target_stage_name=stage_display_name(target_stage_id),
        progress_required=transition.progress_required,
        progress_current=state.cultivation_progress,
        comprehension_required=transition.comprehension_required,
        comprehension_current=state.realm_comprehension,
        stability_recommended=transition.stability_recommended,
        stability_current=state.foundation_stability,
        qi_cost=qi_cost,
        qi_current=state.qi_reserve_current,
        qi_max=state.qi_reserve_max,
        success_chance=chance,
        success_chance_band=chance_band(chance),
        success_chance_percent=int(round(chance * 100)),
        warnings=tuple(warnings),
        blocking_reasons=tuple(blocking),
        mode=mode,
        base_difficulty=transition.base_difficulty,
    )


def _opening_readiness(
    state: CultivationState,
    *,
    warnings: list[str],
    blocking: list[str],
) -> BreakthroughReadiness:
    """Milestone 3 opening breakthrough readiness (story-gated anomaly path)."""

    if state.anomaly_state == ANOMALY_STATE_TRIGGERED:
        blocking.append("Story gate: cultivation anomaly in progress.")
    if state.breakthrough_readiness == BREAKTHROUGH_ATTEMPTED:
        blocking.append("Await guidance before continuing cultivation.")
    if state.cultivation_progress < BREAKTHROUGH_PROGRESS_THRESHOLD:
        blocking.append(
            f"Cultivation progress {state.cultivation_progress}/{BREAKTHROUGH_PROGRESS_THRESHOLD}."
        )
    if state.qi_reserve_current < BREAKTHROUGH_QI_THRESHOLD:
        blocking.append(f"Qi {state.qi_reserve_current}/{BREAKTHROUGH_QI_THRESHOLD} required.")

    warnings.append(
        "Opening breakthrough is story-gated: the first attempt triggers the anomaly, "
        "not a normal stage advance."
    )

    return BreakthroughReadiness(
        eligible=len(blocking) == 0,
        transition_id="opening_anomaly",
        target_realm_id=normalize_realm_id(state.realm_id),
        target_stage_id=normalize_stage_id(state.stage_id),
        target_realm_name=realm_display_name(state.realm_id),
        target_stage_name=stage_display_name(state.stage_id),
        progress_required=BREAKTHROUGH_PROGRESS_THRESHOLD,
        progress_current=state.cultivation_progress,
        comprehension_required=0,
        comprehension_current=state.realm_comprehension,
        stability_recommended=0,
        stability_current=state.foundation_stability,
        qi_cost=BREAKTHROUGH_QI_THRESHOLD,
        qi_current=state.qi_reserve_current,
        qi_max=state.qi_reserve_max,
        success_chance=0.0,
        success_chance_band="Very Low",
        success_chance_percent=0,
        warnings=tuple(warnings),
        blocking_reasons=tuple(blocking),
        mode="opening",
        base_difficulty="story",
    )


def apply_comprehension_carryover(
    current: int,
    *,
    ratio: float,
) -> int:
    """Retain a fraction of comprehension after a successful breakthrough."""

    return clamp_int(int(current * ratio), 0, REALM_COMPREHENSION_MAX)


def recalculate_qi_reserve_max(
    state: CultivationState,
    *,
    new_realm_id: str,
) -> int:
    """Set qi max from target realm floor while preserving intentional bonuses."""

    old_realm = get_realm(state.realm_id)
    new_realm = get_realm(new_realm_id)
    bonus = max(0, state.qi_reserve_max - old_realm.base_qi_max)
    return new_realm.base_qi_max + bonus


def run_breakthrough_attempt(
    state: CultivationState,
    *,
    rng: Random | None = None,
    catalog: BreakthroughCatalog | None = None,
    modifiers: ModifierSnapshot | None = None,
) -> BreakthroughAttemptResult:
    """Attempt a Phase 3 stage or realm breakthrough (confirmed path only).

    ``modifiers`` is an ephemeral ``ModifierSnapshot``. This function must not
    inspect technique catalogs, mastery tables, or effect bundles.
    """

    catalog = catalog or load_breakthrough_catalog()
    state = sync_qi_reserve_max(state)
    readiness = evaluate_breakthrough_readiness(
        state,
        catalog=catalog,
        modifiers=modifiers,
    )

    if readiness.mode == "opening":
        raise EngineValidationError(
            "Opening breakthrough must use the Milestone 3 story adapter"
        )

    if not readiness.eligible:
        reason = "; ".join(readiness.blocking_reasons) or "Breakthrough is unavailable"
        return BreakthroughAttemptResult(
            outcome_type="blocked",
            transition_id=readiness.transition_id,
            success=False,
            qi_before=state.qi_reserve_current,
            qi_after=state.qi_reserve_current,
            progress_before=state.cultivation_progress,
            progress_after=state.cultivation_progress,
            comprehension_before=state.realm_comprehension,
            comprehension_after=state.realm_comprehension,
            stability_before=state.foundation_stability,
            stability_after=state.foundation_stability,
            realm_before=state.realm_id,
            realm_after=state.realm_id,
            stage_before=state.stage_id,
            stage_after=state.stage_id,
            success_chance=readiness.success_chance,
            roll=None,
            summary=reason,
            state=state,
            events=(),
            blocked_reason=reason,
            attempts_before=state.breakthrough_attempts_current_stage,
            attempts_after=state.breakthrough_attempts_current_stage,
        )

    transition = find_transition_for_state(state, catalog=catalog)
    if transition is None or readiness.target_realm_id is None or readiness.target_stage_id is None:
        raise EngineValidationError("No breakthrough transition available")

    # Hard backend guards against client bypass / out-of-range state.
    if state.cultivation_progress < transition.progress_required:
        raise EngineValidationError("Insufficient cultivation progress for breakthrough")
    if state.realm_comprehension < transition.comprehension_required:
        raise EngineValidationError("Insufficient realm comprehension for breakthrough")
    if state.qi_reserve_current < readiness.qi_cost:
        raise EngineValidationError("Insufficient Qi for breakthrough")
    if state.path_status == PATH_STATUS_PROVISIONAL:
        raise EngineValidationError("Story-gated: path is still provisional")

    rng = rng or Random()
    chance = readiness.success_chance
    roll = rng.random()
    attempts_before = state.breakthrough_attempts_current_stage
    qi_before = state.qi_reserve_current
    progress_before = state.cultivation_progress
    comprehension_before = state.realm_comprehension
    stability_before = state.foundation_stability

    events: list[CultivationEvent] = [
        CultivationEvent(
            event_type=EVENT_TYPE_BREAKTHROUGH_ATTEMPT,
            payload={
                "transition_id": transition.id,
                "realm_id": state.realm_id,
                "stage_id": state.stage_id,
                "success_chance": chance,
                "qi_cost": readiness.qi_cost,
            },
        )
    ]

    if roll < chance:
        new_qi_max = recalculate_qi_reserve_max(state, new_realm_id=readiness.target_realm_id)
        new_comprehension = apply_comprehension_carryover(
            state.realm_comprehension,
            ratio=catalog.comprehension_carry_ratio,
        )
        updated = replace(
            state,
            realm_id=readiness.target_realm_id,
            stage_id=readiness.target_stage_id,
            cultivation_progress=0,
            realm_comprehension=new_comprehension,
            qi_reserve_current=max(0, state.qi_reserve_current - readiness.qi_cost),
            qi_reserve_max=new_qi_max,
            breakthrough_readiness=BREAKTHROUGH_NOT_READY,
            breakthrough_attempts_current_stage=0,
            foundation_quality=sync_foundation_quality(
                state.foundation_stability,
                state.foundation_quality,
            ),
        )
        updated = sync_qi_reserve_max(updated)
        updated = replace(
            updated,
            qi_reserve_current=min(updated.qi_reserve_current, updated.qi_reserve_max),
        )
        events.append(
            CultivationEvent(
                event_type=EVENT_TYPE_BREAKTHROUGH_SUCCESS,
                payload={
                    "transition_id": transition.id,
                    "from_realm_id": state.realm_id,
                    "from_stage_id": state.stage_id,
                    "to_realm_id": updated.realm_id,
                    "to_stage_id": updated.stage_id,
                },
            )
        )
        summary = (
            f"Breakthrough succeeds: "
            f"{realm_display_name(updated.realm_id)} ({stage_display_name(updated.stage_id)})."
        )
        return BreakthroughAttemptResult(
            outcome_type="success",
            transition_id=transition.id,
            success=True,
            qi_before=qi_before,
            qi_after=updated.qi_reserve_current,
            progress_before=progress_before,
            progress_after=updated.cultivation_progress,
            comprehension_before=comprehension_before,
            comprehension_after=updated.realm_comprehension,
            stability_before=stability_before,
            stability_after=updated.foundation_stability,
            realm_before=state.realm_id,
            realm_after=updated.realm_id,
            stage_before=state.stage_id,
            stage_after=updated.stage_id,
            success_chance=chance,
            roll=roll,
            summary=summary,
            state=updated,
            events=tuple(events),
            attempts_before=attempts_before,
            attempts_after=0,
        )

    # Failure: consume partial Qi, small stability/progress loss, no stage change.
    fail_qi = max(1, int(readiness.qi_cost * catalog.failure_qi_cost_ratio))
    new_qi = max(0, state.qi_reserve_current - fail_qi)
    new_stability = clamp_stability(state.foundation_stability - catalog.failure_stability_loss)
    new_progress = clamp_int(
        state.cultivation_progress - catalog.failure_progress_loss,
        0,
        CULTIVATION_PROGRESS_MAX,
    )
    updated = replace(
        state,
        qi_reserve_current=new_qi,
        foundation_stability=new_stability,
        foundation_quality=sync_foundation_quality(new_stability, state.foundation_quality),
        cultivation_progress=new_progress,
        breakthrough_readiness=BREAKTHROUGH_NOT_READY,
        breakthrough_attempts_current_stage=attempts_before + 1,
    )
    summary = (
        "Breakthrough fails. Some Qi scatters and your foundation wavers, "
        "but your realm and stage hold."
    )
    return BreakthroughAttemptResult(
        outcome_type="failure",
        transition_id=transition.id,
        success=False,
        qi_before=qi_before,
        qi_after=updated.qi_reserve_current,
        progress_before=progress_before,
        progress_after=updated.cultivation_progress,
        comprehension_before=comprehension_before,
        comprehension_after=updated.realm_comprehension,
        stability_before=stability_before,
        stability_after=updated.foundation_stability,
        realm_before=state.realm_id,
        realm_after=updated.realm_id,
        stage_before=state.stage_id,
        stage_after=updated.stage_id,
        success_chance=chance,
        roll=roll,
        summary=summary,
        state=updated,
        events=tuple(events),
        attempts_before=attempts_before,
        attempts_after=updated.breakthrough_attempts_current_stage,
    )


def breakthrough_result_to_dict(result: BreakthroughAttemptResult) -> dict[str, Any]:
    """Serialize a breakthrough result for persistence / templates."""

    return {
        "outcome_type": result.outcome_type,
        "transition_id": result.transition_id,
        "success": result.success,
        "qi_before": result.qi_before,
        "qi_after": result.qi_after,
        "progress_before": result.progress_before,
        "progress_after": result.progress_after,
        "comprehension_before": result.comprehension_before,
        "comprehension_after": result.comprehension_after,
        "stability_before": result.stability_before,
        "stability_after": result.stability_after,
        "realm_before": result.realm_before,
        "realm_after": result.realm_after,
        "stage_before": result.stage_before,
        "stage_after": result.stage_after,
        "success_chance": result.success_chance,
        "success_chance_percent": int(round(result.success_chance * 100)),
        "success_chance_band": chance_band(result.success_chance),
        "summary": result.summary,
        "blocked_reason": result.blocked_reason,
        "attempts_before": result.attempts_before,
        "attempts_after": result.attempts_after,
    }


def readiness_to_dict(readiness: BreakthroughReadiness) -> dict[str, Any]:
    """Serialize readiness for the play UI."""

    return {
        "eligible": readiness.eligible,
        "transition_id": readiness.transition_id,
        "target_realm_id": readiness.target_realm_id,
        "target_stage_id": readiness.target_stage_id,
        "target_realm_name": readiness.target_realm_name,
        "target_stage_name": readiness.target_stage_name,
        "progress_required": readiness.progress_required,
        "progress_current": readiness.progress_current,
        "comprehension_required": readiness.comprehension_required,
        "comprehension_current": readiness.comprehension_current,
        "stability_recommended": readiness.stability_recommended,
        "stability_current": readiness.stability_current,
        "qi_cost": readiness.qi_cost,
        "qi_current": readiness.qi_current,
        "qi_max": readiness.qi_max,
        "success_chance": readiness.success_chance,
        "success_chance_band": readiness.success_chance_band,
        "success_chance_percent": readiness.success_chance_percent,
        "warnings": list(readiness.warnings),
        "blocking_reasons": list(readiness.blocking_reasons),
        "mode": readiness.mode,
        "base_difficulty": readiness.base_difficulty,
    }


# Architecture note: techniques affect breakthroughs only via ModifierSnapshot
# (BREAKTHROUGH_SUPPORTED_EFFECT_TYPES). Boundless path math stays outside modifiers.
# Later consumers (events, combat) will declare their own allowlists.
