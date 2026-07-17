"""Data-driven world event engine (Phase 4a core).

Owns catalog loading, eligibility, weighted selection, activation chance, and
pure effect resolution. Persistence and live hooks are application-layer
concerns (Phase 4b+).

RNG: all rolls require an injected ``random.Random``. The save-level
``world_rng_counter`` seeds that RNG in services; cultivation keeps a separate
``cultivation_rng_counter`` so existing cultivation tests stay deterministic
and event rolls do not share stream state with session/breakthrough rolls.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path
from random import Random
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from ai_adventure.engine.actors import ActorRef
from ai_adventure.engine.constants import (
    CULTIVATION_PROGRESS_MAX,
    EVENT_TYPE_WORLD_EVENT_RESOLVED,
    PATH_STATUS_CONFIRMED_BOUNDLESS,
    PATH_STATUS_CONFIRMED_ORDINARY,
    PATH_STATUS_PROVISIONAL,
    REALM_COMPREHENSION_MAX,
)
from ai_adventure.engine.cultivation_state import CultivationState, clamp_int
from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.foundation import clamp_stability, sync_foundation_quality
from ai_adventure.engine.modifiers import ModifierSnapshot, consumer_number
from ai_adventure.engine.realms import get_realm, normalize_realm_id
from ai_adventure.engine.time import advance_world_days, current_world_day

_EVENTS_DIR = Path(__file__).resolve().parents[1] / "data" / "events"
_MANIFEST_PATH = _EVENTS_DIR / "event_manifest.json"

EventCategory = Literal[
    "cultivation",
    "exploration",
    "npc_encounter",
    "discovery",
    "environment",
    "combat",
    "story",
]

ALLOWED_EFFECT_TYPES: frozenset[str] = frozenset(
    {
        "modify_cultivation",
        "modify_money",
        "grant_item",
        "advance_world_days",
        "set_flag",
        "noop",
        "emit_log",
    }
)

ALLOWED_TRIGGER_KINDS: frozenset[str] = frozenset(
    {
        "after_cultivation_session",
        "after_story_travel",
        "after_explore",
        "after_inspect",
        "manual_debug",
        "on_day_advance",
    }
)

NoEventReason = Literal[
    "no_eligible",
    "chance_missed",
    "empty_catalog",
    "max_events_zero",
]

PHASE4_MAX_EVENTS_PER_TRIGGER = 1

# Soft selection bias only — hard eligibility stays in EventRequirements.
EVENT_SUPPORTED_EFFECT_TYPES: frozenset[str] = frozenset(
    {
        "weight_mult",
        "chance_flat",
    }
)
EVENT_MIN_EFFECTIVE_WEIGHT = 1e-9


# ---------------------------------------------------------------------------
# Catalog models
# ---------------------------------------------------------------------------


class EventTriggerDef(BaseModel):
    """When and how often a template may activate."""

    kinds: list[str] = Field(min_length=1)
    chance: float = Field(ge=0.0, le=1.0)

    @field_validator("kinds")
    @classmethod
    def _known_kinds(cls, value: list[str]) -> list[str]:
        unknown = [item for item in value if item not in ALLOWED_TRIGGER_KINDS]
        if unknown:
            raise ValueError(f"unknown trigger kinds: {unknown}")
        if len(value) != len(set(value)):
            raise ValueError("duplicate trigger kinds")
        return value


class EventRequirements(BaseModel):
    """Hard eligibility gates evaluated against EventContext.

    ``modifier_flags_all`` is a soft unlock checked against an optional
    ``ModifierSnapshot`` (Phase 6d). Empty means no flag gate.
    """

    path_status_in: list[str] = Field(default_factory=list)
    min_realm_order: int | None = Field(default=None, ge=1)
    max_realm_order: int | None = Field(default=None, ge=1)
    flags_all: list[str] = Field(default_factory=list)
    flags_none: list[str] = Field(default_factory=list)
    modifier_flags_all: list[str] = Field(default_factory=list)
    location_ids: list[str] = Field(default_factory=list)
    min_world_day: int = Field(default=1, ge=1)
    subject_must_be_player: bool = True

    @model_validator(mode="after")
    def _realm_order_range(self) -> EventRequirements:
        if (
            self.min_realm_order is not None
            and self.max_realm_order is not None
            and self.min_realm_order > self.max_realm_order
        ):
            raise ValueError("min_realm_order cannot exceed max_realm_order")
        allowed = {
            PATH_STATUS_PROVISIONAL,
            PATH_STATUS_CONFIRMED_ORDINARY,
            PATH_STATUS_CONFIRMED_BOUNDLESS,
        }
        unknown = [item for item in self.path_status_in if item not in allowed]
        if unknown:
            raise ValueError(f"unknown path_status_in values: {unknown}")
        return self


class EventEffectDef(BaseModel):
    """One allowlisted mechanical effect."""

    type: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("type")
    @classmethod
    def _allowlisted(cls, value: str) -> str:
        if value not in ALLOWED_EFFECT_TYPES:
            raise ValueError(f"unknown effect type: {value}")
        return value


class EventPresentation(BaseModel):
    """Display-only text. Never authoritative game state."""

    placeholder_text: str = Field(min_length=1)
    narration_keys: list[str] = Field(default_factory=list)


class EventContextTags(BaseModel):
    """Soft context tags for future matching and narration (not hard gates).

    Hard eligibility stays in ``requirements``. Empty lists mean unrestricted /
    unspecified context for that facet.
    """

    location_tags: list[str] = Field(default_factory=list)
    weather_tags: list[str] = Field(default_factory=list)
    time_tags: list[str] = Field(default_factory=list)
    cultivation_tags: list[str] = Field(default_factory=list)
    npc_tags: list[str] = Field(default_factory=list)
    environment_tags: list[str] = Field(default_factory=list)


class EventTemplate(BaseModel):
    """One data-driven world event definition."""

    id: str = Field(min_length=1)
    category: EventCategory
    label: str = Field(min_length=1)
    enabled: bool = True
    weight: int = Field(ge=1)
    cooldown_days: int = Field(default=0, ge=0)
    max_fires_per_save: int | None = Field(default=None, ge=1)
    trigger: EventTriggerDef
    requirements: EventRequirements = Field(default_factory=EventRequirements)
    context: EventContextTags = Field(default_factory=EventContextTags)
    effects: list[EventEffectDef] = Field(default_factory=list)
    presentation: EventPresentation
    # Optional reference to a future AI narration template id (not implemented yet).
    ai_prompt_key: str | None = None

    @property
    def is_one_time(self) -> bool:
        """True when the template may fire at most once per save/subject."""

        return self.max_fires_per_save == 1

    @property
    def is_repeatable(self) -> bool:
        """True when the template may fire more than once (cooldown permitting)."""

        return self.max_fires_per_save is None or self.max_fires_per_save > 1


class EventFile(BaseModel):
    """One content file in the event catalog."""

    schema_version: int = Field(ge=1)
    events: list[EventTemplate] = Field(default_factory=list)

    @field_validator("events")
    @classmethod
    def _unique_ids(cls, value: list[EventTemplate]) -> list[EventTemplate]:
        ids = [item.id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate event ids in file")
        return value


class EventManifest(BaseModel):
    """Registry of event content files."""

    content_files: list[str] = Field(default_factory=list)


class EventCatalog(BaseModel):
    """Merged validated catalog."""

    events: list[EventTemplate] = Field(default_factory=list)

    @field_validator("events")
    @classmethod
    def _unique_ids(cls, value: list[EventTemplate]) -> list[EventTemplate]:
        ids = [item.id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate event ids across catalog")
        return value

    def get(self, event_id: str) -> EventTemplate:
        """Return a template by id or raise."""

        for item in self.events:
            if item.id == event_id:
                return item
        raise EngineValidationError(f"Unknown event template: {event_id}")


# ---------------------------------------------------------------------------
# Runtime DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CooldownState:
    """Current cooldown row snapshot for eligibility (mutable store elsewhere)."""

    event_template_id: str
    subject_actor_id: str
    last_fired_world_day: int
    fire_count: int


@dataclass(frozen=True, slots=True)
class EventContext:
    """Inputs for eligibility and resolution (engine-pure)."""

    save_id: str
    subject: ActorRef
    world_day: int
    location_id: str
    story_flags: dict[str, bool]
    cultivation: CultivationState
    money_copper: int
    trigger_kind: str
    cooldowns: tuple[CooldownState, ...] = ()
    max_events: int = PHASE4_MAX_EVENTS_PER_TRIGGER
    action_id: str | None = None


@dataclass(frozen=True, slots=True)
class AppliedEffect:
    """One resolved mechanical effect (facts for persistence / narration)."""

    type: str
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class EventResolution:
    """Completed mechanical result for one fired event.

    ``presentation_placeholder`` is display-only and must never be treated as
    authoritative state.
    """

    instance_id: str
    template_id: str
    category: str
    label: str
    subject_actor_id: str
    world_day_before: int
    world_day_after: int
    effects_applied: tuple[AppliedEffect, ...]
    presentation_placeholder: str
    cultivation: CultivationState
    money_copper: int
    granted_items: tuple[dict[str, Any], ...]
    flags_set: dict[str, bool]
    facts: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class NoEventResult:
    """Structured result when a trigger slot does not fire an event."""

    reason: NoEventReason
    trigger_kind: str
    facts: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EventSlotOutcome:
    """One slot in a trigger batch (Phase 4: always a single slot)."""

    kind: Literal["event", "no_event"]
    resolution: EventResolution | None = None
    no_event: NoEventResult | None = None


@dataclass(frozen=True, slots=True)
class EventTriggerBatch:
    """Result of evaluating a trigger.

    Phase 4 always uses ``max_events=1`` and ``len(slots)==1``. The batch shape
    allows future multi-event triggers without changing cooldown / event_log
    row shapes (each fired event remains one resolution + one log payload).
    """

    trigger_kind: str
    max_events: int
    slots: tuple[EventSlotOutcome, ...]

    @property
    def fired(self) -> bool:
        """True if any slot produced an EventResolution."""

        return any(slot.kind == "event" and slot.resolution is not None for slot in self.slots)

    @property
    def first_resolution(self) -> EventResolution | None:
        """Convenience accessor for the Phase 4 single-event path."""

        for slot in self.slots:
            if slot.kind == "event" and slot.resolution is not None:
                return slot.resolution
        return None

    @property
    def first_no_event(self) -> NoEventResult | None:
        """Convenience accessor when nothing fired."""

        for slot in self.slots:
            if slot.kind == "no_event" and slot.no_event is not None:
                return slot.no_event
        return None


# ---------------------------------------------------------------------------
# Catalog load
# ---------------------------------------------------------------------------


@lru_cache(maxsize=4)
def load_event_catalog(events_dir: str | None = None) -> EventCatalog:
    """Load and validate the event catalog; reject unknown effects at load."""

    root = Path(events_dir) if events_dir else _EVENTS_DIR
    manifest_path = root / "event_manifest.json"
    if not manifest_path.is_file():
        raise EngineValidationError(f"Event manifest missing: {manifest_path}")
    try:
        manifest = EventManifest.model_validate(
            json.loads(manifest_path.read_text(encoding="utf-8"))
        )
    except json.JSONDecodeError as exc:
        raise EngineValidationError("Corrupted event manifest") from exc
    except Exception as exc:  # noqa: BLE001
        raise EngineValidationError(f"Invalid event manifest: {exc}") from exc

    merged: list[EventTemplate] = []
    for relative in manifest.content_files:
        path = root / relative
        if not path.is_file():
            raise EngineValidationError(f"Event content file missing: {relative}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            file_model = EventFile.model_validate(raw)
        except json.JSONDecodeError as exc:
            raise EngineValidationError(f"Corrupted event file: {relative}") from exc
        except Exception as exc:  # noqa: BLE001
            raise EngineValidationError(f"Invalid event file {relative}: {exc}") from exc
        merged.extend(file_model.events)

    try:
        return EventCatalog(events=merged)
    except Exception as exc:  # noqa: BLE001
        raise EngineValidationError(f"Invalid event catalog: {exc}") from exc


def clear_event_catalog_cache() -> None:
    """Clear cached catalogs (tests / alternate roots)."""

    load_event_catalog.cache_clear()


# ---------------------------------------------------------------------------
# Eligibility
# ---------------------------------------------------------------------------


def _cooldown_for(
    template_id: str,
    subject_actor_id: str,
    cooldowns: tuple[CooldownState, ...],
) -> CooldownState | None:
    for row in cooldowns:
        if (
            row.event_template_id == template_id
            and row.subject_actor_id == subject_actor_id
        ):
            return row
    return None


def is_template_eligible(
    template: EventTemplate,
    context: EventContext,
    *,
    modifiers: ModifierSnapshot | None = None,
) -> bool:
    """Return whether a template may be selected for this context.

    Hard gates use ``EventContext`` only. Optional ``modifier_flags_all`` soft
    unlocks are checked against ``modifiers`` when provided.
    """

    if not template.enabled:
        return False
    if context.trigger_kind not in template.trigger.kinds:
        return False

    req = template.requirements
    if req.subject_must_be_player and context.subject.kind != "player":
        return False
    if context.world_day < req.min_world_day:
        return False
    if req.path_status_in and context.cultivation.path_status not in req.path_status_in:
        return False
    if req.location_ids and context.location_id not in req.location_ids:
        return False
    for flag in req.flags_all:
        if not context.story_flags.get(flag, False):
            return False
    for flag in req.flags_none:
        if context.story_flags.get(flag, False):
            return False
    for flag in req.modifier_flags_all:
        if modifiers is None or not modifiers.has_flag(flag):
            return False

    realm = get_realm(normalize_realm_id(context.cultivation.realm_id))
    if req.min_realm_order is not None and realm.order_index < req.min_realm_order:
        return False
    if req.max_realm_order is not None and realm.order_index > req.max_realm_order:
        return False

    cool = _cooldown_for(template.id, context.subject.actor_id, context.cooldowns)
    if cool is not None:
        if (
            template.max_fires_per_save is not None
            and cool.fire_count >= template.max_fires_per_save
        ):
            return False
        if template.cooldown_days > 0:
            earliest = cool.last_fired_world_day + template.cooldown_days
            if context.world_day < earliest:
                return False
    return True


def list_eligible_templates(
    catalog: EventCatalog,
    context: EventContext,
    *,
    modifiers: ModifierSnapshot | None = None,
) -> list[EventTemplate]:
    """Filter enabled templates for the current trigger context."""

    return [
        item
        for item in catalog.events
        if is_template_eligible(item, context, modifiers=modifiers)
    ]


# ---------------------------------------------------------------------------
# Selection + activation (soft bias via ModifierSnapshot)
# ---------------------------------------------------------------------------


def effective_event_weight(
    template: EventTemplate,
    modifiers: ModifierSnapshot | None,
) -> float:
    """Catalog weight × global ``weight_mult`` × category ``weight_mult``."""

    base = float(template.weight)
    global_mult = consumer_number(
        modifiers,
        "weight_mult",
        supported=EVENT_SUPPORTED_EFFECT_TYPES,
        default=1.0,
        category=None,
    )
    category_mult = consumer_number(
        modifiers,
        "weight_mult",
        supported=EVENT_SUPPORTED_EFFECT_TYPES,
        default=1.0,
        category=template.category,
    )
    return max(base * global_mult * category_mult, EVENT_MIN_EFFECTIVE_WEIGHT)


def effective_activation_chance(
    template: EventTemplate,
    modifiers: ModifierSnapshot | None,
) -> float:
    """Catalog chance + global ``chance_flat`` + category ``chance_flat``, clamped."""

    base = float(template.trigger.chance)
    global_flat = consumer_number(
        modifiers,
        "chance_flat",
        supported=EVENT_SUPPORTED_EFFECT_TYPES,
        default=0.0,
        category=None,
    )
    category_flat = consumer_number(
        modifiers,
        "chance_flat",
        supported=EVENT_SUPPORTED_EFFECT_TYPES,
        default=0.0,
        category=template.category,
    )
    chance = base + global_flat + category_flat
    if chance <= 0.0:
        return 0.0
    if chance >= 1.0:
        return 1.0
    return chance


def select_weighted_template(
    eligible: list[EventTemplate],
    rng: Random,
    *,
    modifiers: ModifierSnapshot | None = None,
) -> EventTemplate | None:
    """Pick one template by effective weight, or None if the list is empty."""

    if not eligible:
        return None
    weights = [effective_event_weight(item, modifiers) for item in eligible]
    return rng.choices(eligible, weights=weights, k=1)[0]


def roll_activation_chance(chance: float, rng: Random) -> bool:
    """Return True when the activation chance succeeds."""

    if chance <= 0.0:
        return False
    if chance >= 1.0:
        return True
    return rng.random() < chance


# ---------------------------------------------------------------------------
# Effect application (pure)
# ---------------------------------------------------------------------------


def _apply_modify_cultivation(
    state: CultivationState,
    payload: dict[str, Any],
) -> tuple[CultivationState, dict[str, Any]]:
    qi_delta = int(payload.get("qi_reserve_delta", 0))
    progress_delta = int(payload.get("cultivation_progress_delta", 0))
    comprehension_delta = int(payload.get("realm_comprehension_delta", 0))
    stability_delta = int(payload.get("foundation_stability_delta", 0))

    new_qi = clamp_int(
        state.qi_reserve_current + qi_delta,
        0,
        state.qi_reserve_max,
    )
    new_progress = clamp_int(
        state.cultivation_progress + progress_delta,
        0,
        CULTIVATION_PROGRESS_MAX,
    )
    new_comprehension = clamp_int(
        state.realm_comprehension + comprehension_delta,
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
    )
    return updated, {
        "qi_reserve_delta": qi_delta,
        "cultivation_progress_delta": progress_delta,
        "realm_comprehension_delta": comprehension_delta,
        "foundation_stability_delta": stability_delta,
        "qi_reserve_current": new_qi,
        "cultivation_progress": new_progress,
        "realm_comprehension": new_comprehension,
        "foundation_stability": new_stability,
    }


def apply_event_effects(
    template: EventTemplate,
    context: EventContext,
) -> EventResolution:
    """Apply template effects purely; raise if any effect is illegal.

    Callers must persist the full resolution atomically or not at all.
    """

    world_day = current_world_day(context.world_day)
    state = context.cultivation
    money = context.money_copper
    flags = dict(context.story_flags)
    granted: list[dict[str, Any]] = []
    applied: list[AppliedEffect] = []

    for effect in template.effects:
        payload = dict(effect.payload)
        if effect.type == "noop":
            applied.append(AppliedEffect(type="noop", payload={}))
            continue
        if effect.type == "emit_log":
            applied.append(AppliedEffect(type="emit_log", payload=payload))
            continue
        if effect.type == "advance_world_days":
            days = int(payload.get("days", 0))
            world_day = advance_world_days(world_day, days)
            applied.append(AppliedEffect(type="advance_world_days", payload={"days": days}))
            continue
        if effect.type == "set_flag":
            flag = str(payload.get("flag", ""))
            if not flag:
                raise EngineValidationError("set_flag requires flag")
            value = bool(payload.get("value", True))
            flags[flag] = value
            applied.append(
                AppliedEffect(type="set_flag", payload={"flag": flag, "value": value})
            )
            continue
        if effect.type == "modify_money":
            delta = int(payload.get("copper_delta", 0))
            new_money = money + delta
            if new_money < 0:
                raise EngineValidationError("Event would reduce money below zero")
            money = new_money
            applied.append(
                AppliedEffect(
                    type="modify_money",
                    payload={"copper_delta": delta, "money_copper": money},
                )
            )
            continue
        if effect.type == "grant_item":
            item_code = str(payload.get("item_code", ""))
            display_name = str(payload.get("display_name", item_code))
            quantity = int(payload.get("quantity", 1))
            if not item_code or quantity < 1:
                raise EngineValidationError("grant_item requires item_code and quantity >= 1")
            item = {
                "item_code": item_code,
                "display_name": display_name,
                "quantity": quantity,
            }
            granted.append(item)
            applied.append(AppliedEffect(type="grant_item", payload=item))
            continue
        if effect.type == "modify_cultivation":
            state, detail = _apply_modify_cultivation(state, payload)
            applied.append(AppliedEffect(type="modify_cultivation", payload=detail))
            continue
        raise EngineValidationError(f"Unhandled effect type: {effect.type}")

    instance_id = str(uuid4())
    facts = {
        "event_template_id": template.id,
        "instance_id": instance_id,
        "category": template.category,
        "subject_actor_id": context.subject.actor_id,
        "effects": [{"type": effect.type, "payload": effect.payload} for effect in applied],
        "world_day_before": context.world_day,
        "world_day_after": world_day,
        # Presentation is explicitly non-authoritative.
        "presentation_placeholder": template.presentation.placeholder_text,
        "presentation_authoritative": False,
        "context": template.context.model_dump(),
        "ai_prompt_key": template.ai_prompt_key,
    }
    return EventResolution(
        instance_id=instance_id,
        template_id=template.id,
        category=template.category,
        label=template.label,
        subject_actor_id=context.subject.actor_id,
        world_day_before=context.world_day,
        world_day_after=world_day,
        effects_applied=tuple(applied),
        presentation_placeholder=template.presentation.placeholder_text,
        cultivation=state,
        money_copper=money,
        granted_items=tuple(granted),
        flags_set={k: v for k, v in flags.items() if context.story_flags.get(k) != v},
        facts=facts,
    )


def resolution_to_event_log_payload(resolution: EventResolution) -> dict[str, Any]:
    """Build immutable event_log payload (id + mechanical effects)."""

    return {
        "event_template_id": resolution.template_id,
        "instance_id": resolution.instance_id,
        "category": resolution.category,
        "label": resolution.label,
        "subject_actor_id": resolution.subject_actor_id,
        "world_day_before": resolution.world_day_before,
        "world_day_after": resolution.world_day_after,
        "effects_applied": [
            {"type": item.type, "payload": item.payload} for item in resolution.effects_applied
        ],
        "granted_items": list(resolution.granted_items),
        "flags_set": dict(resolution.flags_set),
        "money_copper": resolution.money_copper,
        "cultivation": {
            "qi_reserve_current": resolution.cultivation.qi_reserve_current,
            "cultivation_progress": resolution.cultivation.cultivation_progress,
            "realm_comprehension": resolution.cultivation.realm_comprehension,
            "foundation_stability": resolution.cultivation.foundation_stability,
            "path_status": resolution.cultivation.path_status,
            "realm_id": resolution.cultivation.realm_id,
            "stage_id": resolution.cultivation.stage_id,
        },
        # Placeholder text stored for replay flavor only — not mechanical truth.
        "presentation_placeholder": resolution.presentation_placeholder,
        "presentation_authoritative": False,
        "context": resolution.facts.get("context", {}),
        "ai_prompt_key": resolution.facts.get("ai_prompt_key"),
        "event_type": EVENT_TYPE_WORLD_EVENT_RESOLVED,
    }


# ---------------------------------------------------------------------------
# Public evaluate API
# ---------------------------------------------------------------------------


def evaluate_trigger(
    context: EventContext,
    *,
    rng: Random,
    catalog: EventCatalog | None = None,
    events_dir: str | None = None,
    modifiers: ModifierSnapshot | None = None,
) -> EventTriggerBatch:
    """Evaluate a trigger: eligibility → weighted pick → activation chance.

    Always returns a batch with ``max_events`` slots (Phase 4: one slot).
    Requires an injected ``rng`` — never uses module-global randomness.

    ``modifiers`` is an ephemeral ``ModifierSnapshot`` for soft selection bias
    only. Hard eligibility, cooldowns, mutations, and persistence stay here.
    ``modifiers=None`` preserves Phase 4 weight/chance behavior.
    """

    if rng is None:  # type: ignore[truthy-bool]
        raise EngineValidationError("Event evaluation requires an injected Random")
    if context.max_events < 0:
        raise EngineValidationError("max_events must be >= 0")
    if context.trigger_kind not in ALLOWED_TRIGGER_KINDS:
        raise EngineValidationError(f"Unknown trigger kind: {context.trigger_kind}")

    cat = catalog if catalog is not None else load_event_catalog(events_dir)
    slots: list[EventSlotOutcome] = []

    # Phase 4: single pass. Future multi-event can loop while updating a
    # working cooldown snapshot without changing persisted row shapes.
    for _ in range(max(context.max_events, 0)):
        eligible = list_eligible_templates(cat, context, modifiers=modifiers)
        if not cat.events:
            slots.append(
                EventSlotOutcome(
                    kind="no_event",
                    no_event=NoEventResult(
                        reason="empty_catalog",
                        trigger_kind=context.trigger_kind,
                        facts={"eligible_count": 0},
                    ),
                )
            )
            continue
        if not eligible:
            slots.append(
                EventSlotOutcome(
                    kind="no_event",
                    no_event=NoEventResult(
                        reason="no_eligible",
                        trigger_kind=context.trigger_kind,
                        facts={"eligible_count": 0},
                    ),
                )
            )
            continue

        selected = select_weighted_template(eligible, rng, modifiers=modifiers)
        assert selected is not None
        activation_chance = effective_activation_chance(selected, modifiers)
        activated = roll_activation_chance(activation_chance, rng)
        if not activated:
            slots.append(
                EventSlotOutcome(
                    kind="no_event",
                    no_event=NoEventResult(
                        reason="chance_missed",
                        trigger_kind=context.trigger_kind,
                        facts={
                            "selected_template_id": selected.id,
                            "chance": activation_chance,
                            "catalog_chance": selected.trigger.chance,
                            "eligible_count": len(eligible),
                        },
                    ),
                )
            )
            continue

        resolution = apply_event_effects(selected, context)
        slots.append(EventSlotOutcome(kind="event", resolution=resolution))

    if context.max_events == 0:
        slots = [
            EventSlotOutcome(
                kind="no_event",
                no_event=NoEventResult(
                    reason="max_events_zero",
                    trigger_kind=context.trigger_kind,
                ),
            )
        ]

    return EventTriggerBatch(
        trigger_kind=context.trigger_kind,
        max_events=context.max_events,
        slots=tuple(slots),
    )
