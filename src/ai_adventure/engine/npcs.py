"""NPC catalog + interaction rules (Phase 9a–9c).

Catalogs define identity. Saves store mutable ``npc_world_state`` only.
Story spawns by ``npc_id``. Interactions are data-driven and deterministic.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.locations import (
    WorldManifest,
    WorldPackManifest,
    _WORLD_DIR,
    _PACKS_DIR,
    _WORLD_MANIFEST_PATH,
    load_location_catalog,
)
from ai_adventure.engine.sects import (
    apply_standing_delta,
    load_sect_catalog,
    required_standing_for_npc_action,
)

NpcStatus = Literal["active", "dead", "absent"]

RELATIONSHIP_SCORE_MIN = -100
RELATIONSHIP_SCORE_MAX = 100
# Compatibility alias — authoritative deltas live in npc_action_catalog.json rewards.
GREET_RELATIONSHIP_DELTA = 5

_NPC_ACTION_CATALOG_PATH = _WORLD_DIR / "npc_action_catalog.json"

KNOWN_NPC_ROLE_TAGS: frozenset[str] = frozenset(
    {
        "elder",
        "disciple",
        "merchant",
        "teacher",
        "rival",
        "examiner",
        "instructor",
        "passing_cultivator",
        "foundation_elder",
        "sect_examiner",
        "sect_instructor",
        "herb_steward",
    }
)

# Implemented reward types only — catalogs may not use reserved types yet.
IMPLEMENTED_NPC_REWARD_TYPES: frozenset[str] = frozenset(
    {
        "adjust_relationship",
        "adjust_sect_standing",
        "learn_technique",
        "set_flag",
        "grant_item",
        "emit_trigger",
        "unlock_location",
    }
)

# Extension points: reject if authored until a later phase wires them.
RESERVED_NPC_REWARD_TYPES: frozenset[str] = frozenset(
    {
        "unlock_dialogue",
        "start_story",
        "grant_reputation",
        "modify_modifier_source",
        "begin_mission",
    }
)

# Legacy alias — action ids are catalog-driven; this set is informational only.
KNOWN_NPC_ACTION_IDS: frozenset[str] = frozenset(
    {"inspect", "greet", "ask_guidance", "request_instruction"}
)


class CultivationSummary(BaseModel):
    """Authored cultivation snapshot — not a live simulation state."""

    realm_id: str = Field(min_length=1)
    stage_id: str = Field(min_length=1)
    path_tags: list[str] = Field(default_factory=list)


class NpcDefinition(BaseModel):
    """One authored NPC from a world content pack."""

    npc_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    role_tags: list[str] = Field(min_length=1)
    home_location_id: str = Field(min_length=1)
    default_location_id: str = Field(min_length=1)
    sect_id: str | None = None
    cultivation_summary: CultivationSummary
    description: str = Field(min_length=1)
    pack_id: str = Field(default="", min_length=0)

    @field_validator("role_tags")
    @classmethod
    def _known_roles(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if not cleaned:
            raise ValueError("role_tags must be non-empty")
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("duplicate role_tags")
        unknown = sorted(set(cleaned) - KNOWN_NPC_ROLE_TAGS)
        if unknown:
            raise ValueError(f"unknown role_tags: {unknown}")
        return cleaned


class NpcFile(BaseModel):
    """One pack NPC content file."""

    schema_version: int = Field(ge=1)
    npcs: list[NpcDefinition] = Field(default_factory=list)


class NpcCatalog(BaseModel):
    """Merged NPC catalog across world packs."""

    npcs: list[NpcDefinition] = Field(default_factory=list)
    pack_ids: list[str] = Field(default_factory=list)

    @property
    def by_id(self) -> dict[str, NpcDefinition]:
        """Index NPCs by stable catalog id."""

        return {item.npc_id: item for item in self.npcs}


@dataclass(frozen=True, slots=True)
class NpcWorldStateRecord:
    """Engine DTO for mutable NPC world state."""

    actor_id: str
    npc_id: str
    current_location_id: str
    status: NpcStatus
    discovered: bool
    met: bool
    relationship_score: int
    sect_id_override: str | None
    state_flags: dict[str, bool]
    last_interaction_world_day: int | None


class NpcInteractionRequirements(BaseModel):
    """Allowlisted gates for one authored NPC interaction."""

    min_relationship: int | None = None
    min_sect_standing: int | None = None
    min_sect_standing_by_role: dict[str, int] = Field(default_factory=dict)
    required_sect_id: str | None = None
    required_sect_rank_ids: list[str] = Field(default_factory=list)
    required_realm_ids: list[str] = Field(default_factory=list)
    min_realm_order: int | None = Field(default=None, ge=1)
    required_stage_ids: list[str] = Field(default_factory=list)
    required_location_ids: list[str] = Field(default_factory=list)
    flags_all: list[str] = Field(default_factory=list)
    flags_none: list[str] = Field(default_factory=list)
    required_role_tags_any: list[str] = Field(default_factory=list)
    allowed_npc_ids: list[str] = Field(default_factory=list)


class NpcInteractionReward(BaseModel):
    """One allowlisted reward object from the interaction catalog."""

    type: str = Field(min_length=1)
    delta: int | None = None
    technique_id: str | None = None
    flag: str | None = None
    value: bool | None = None
    item_code: str | None = None
    quantity: int | None = Field(default=None, ge=1)
    trigger_kind: str | None = None
    location_id: str | None = None

    @field_validator("type")
    @classmethod
    def _known_reward_type(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned in RESERVED_NPC_REWARD_TYPES:
            raise ValueError(
                f"reward type {cleaned!r} is reserved and not implemented yet"
            )
        if cleaned not in IMPLEMENTED_NPC_REWARD_TYPES:
            raise ValueError(f"unknown NPC reward type: {cleaned!r}")
        return cleaned


class NpcActionDefinition(BaseModel):
    """One authored NPC interaction in the permanent interaction catalog."""

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    description: str = ""
    duration_days: int = Field(default=0, ge=0)
    marks_met: bool = True
    requirements: NpcInteractionRequirements = Field(
        default_factory=NpcInteractionRequirements
    )
    rewards: list[NpcInteractionReward] = Field(default_factory=list)
    presentation_template: str = Field(min_length=1)

    @field_validator("id")
    @classmethod
    def _non_empty_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("action id must be non-empty")
        if not cleaned.replace("_", "").isalnum():
            raise ValueError(f"invalid action id: {cleaned!r}")
        return cleaned


class NpcActionCatalog(BaseModel):
    """Global authored NPC interaction catalog."""

    schema_version: int = Field(ge=1)
    actions: list[NpcActionDefinition] = Field(min_length=1)

    @field_validator("actions")
    @classmethod
    def _unique_ids(cls, value: list[NpcActionDefinition]) -> list[NpcActionDefinition]:
        ids = [item.id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate NPC action ids")
        return value

    @property
    def by_id(self) -> dict[str, NpcActionDefinition]:
        """Index actions by id."""

        return {item.id: item for item in self.actions}


@dataclass(frozen=True, slots=True)
class NpcInteractionPlayerContext:
    """Player-side facts needed to validate interaction requirements."""

    location_id: str
    realm_id: str
    stage_id: str
    sect_id: str | None
    sect_rank_id: str | None
    sect_standing: int | None
    story_flags: dict[str, bool]


@dataclass(frozen=True, slots=True)
class PlannedNpcReward:
    """Validated reward ready for service-layer application."""

    type: str
    delta: int | None = None
    technique_id: str | None = None
    flag: str | None = None
    value: bool | None = None
    item_code: str | None = None
    quantity: int | None = None
    trigger_kind: str | None = None
    location_id: str | None = None


@dataclass(frozen=True, slots=True)
class NpcInteractionResolution:
    """Pure result of one NPC interaction plan."""

    npc_id: str
    action_id: str
    relationship_before: int
    relationship_after: int
    met: bool
    duration_days: int
    trigger_kind: str | None
    summary: str
    presentation_text: str
    sect_id: str | None = None
    sect_standing_before: int | None = None
    sect_standing_after: int | None = None
    sect_standing_delta: int = 0
    planned_rewards: tuple[PlannedNpcReward, ...] = ()
    flag_updates: tuple[tuple[str, bool], ...] = ()
    technique_ids_to_learn: tuple[str, ...] = ()
    items_to_grant: tuple[tuple[str, int], ...] = ()
    location_ids_to_unlock: tuple[str, ...] = ()


def clear_npc_action_catalog_cache() -> None:
    """Drop cached NPC action catalog (tests)."""

    load_npc_action_catalog.cache_clear()


@lru_cache(maxsize=1)
def load_npc_action_catalog(path: str | None = None) -> NpcActionCatalog:
    """Load and cross-validate the NPC interaction catalog."""

    catalog_path = Path(path) if path else _NPC_ACTION_CATALOG_PATH
    if not catalog_path.is_file():
        raise EngineValidationError(f"NPC action catalog missing: {catalog_path}")
    try:
        raw = json.loads(catalog_path.read_text(encoding="utf-8"))
        catalog = NpcActionCatalog.model_validate(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        raise EngineValidationError(f"Invalid NPC action catalog: {exc}") from exc
    errors = validate_npc_action_catalog(catalog)
    if errors:
        raise EngineValidationError("Invalid NPC action catalog: " + "; ".join(errors))
    return catalog


def validate_npc_action_catalog(
    catalog: NpcActionCatalog | None = None,
) -> list[str]:
    """Return catalog validation errors (empty if ok)."""

    cat = catalog if catalog is not None else None
    if cat is None:
        try:
            path = _NPC_ACTION_CATALOG_PATH
            raw = json.loads(path.read_text(encoding="utf-8"))
            cat = NpcActionCatalog.model_validate(raw)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            return [str(exc)]

    errors: list[str] = []
    from ai_adventure.engine.techniques import list_techniques

    technique_ids = {tech.id for tech in list_techniques()}
    for action in cat.actions:
        for reward in action.rewards:
            if reward.type == "learn_technique":
                if not reward.technique_id:
                    errors.append(f"{action.id}: learn_technique missing technique_id")
                elif reward.technique_id not in technique_ids:
                    errors.append(
                        f"{action.id}: unknown technique_id {reward.technique_id!r}"
                    )
            if reward.type == "adjust_relationship" and reward.delta is None:
                errors.append(f"{action.id}: adjust_relationship missing delta")
            if reward.type == "adjust_sect_standing" and reward.delta is None:
                errors.append(f"{action.id}: adjust_sect_standing missing delta")
            if reward.type == "set_flag" and not reward.flag:
                errors.append(f"{action.id}: set_flag missing flag")
            if reward.type == "grant_item":
                if not reward.item_code or reward.quantity is None:
                    errors.append(f"{action.id}: grant_item needs item_code and quantity")
            if reward.type == "emit_trigger" and not reward.trigger_kind:
                errors.append(f"{action.id}: emit_trigger missing trigger_kind")
            if reward.type == "unlock_location" and not reward.location_id:
                errors.append(f"{action.id}: unlock_location missing location_id")
    return errors


def get_npc_action(action_id: str, *, catalog: NpcActionCatalog | None = None) -> NpcActionDefinition:
    """Return one NPC action definition or raise."""

    cat = catalog if catalog is not None else load_npc_action_catalog()
    action = cat.by_id.get(action_id)
    if action is None:
        raise EngineValidationError(f"Unknown NPC action: {action_id!r}")
    return action


def list_npc_actions(*, catalog: NpcActionCatalog | None = None) -> list[NpcActionDefinition]:
    """Return NPC actions in catalog order."""

    cat = catalog if catalog is not None else load_npc_action_catalog()
    return list(cat.actions)


def action_offered_by_npc(
    action: NpcActionDefinition,
    definition: NpcDefinition,
) -> bool:
    """Return whether this NPC may offer the action (binding only, not full gates)."""

    req = action.requirements
    if req.allowed_npc_ids and definition.npc_id not in req.allowed_npc_ids:
        return False
    if req.required_role_tags_any:
        if not set(definition.role_tags) & set(req.required_role_tags_any):
            return False
    return True


def list_offered_actions_for_npc(
    definition: NpcDefinition,
    *,
    catalog: NpcActionCatalog | None = None,
) -> list[NpcActionDefinition]:
    """Return catalog actions offered by this NPC (binding filter only)."""

    return [
        action
        for action in list_npc_actions(catalog=catalog)
        if action_offered_by_npc(action, definition)
    ]


def clear_npc_catalog_cache() -> None:
    """Drop cached NPC catalog (tests)."""

    load_npc_catalog.cache_clear()
    clear_npc_action_catalog_cache()


@lru_cache(maxsize=1)
def load_npc_catalog(world_dir: str | None = None) -> NpcCatalog:
    """Load and validate the merged NPC catalog."""

    root = Path(world_dir) if world_dir is not None else _WORLD_DIR
    catalog, errors = _load_npc_catalog_unchecked(root)
    if errors:
        raise EngineValidationError("Invalid NPC catalog: " + "; ".join(errors))
    return catalog


def validate_npc_catalog(world_dir: str | Path | None = None) -> list[str]:
    """Return validation error messages (empty if ok)."""

    root = Path(world_dir) if world_dir is not None else _WORLD_DIR
    try:
        _, errors = _load_npc_catalog_unchecked(root)
        return list(errors)
    except (OSError, json.JSONDecodeError, ValueError, EngineValidationError) as exc:
        return [str(exc)]


def assert_npc_catalog_valid(world_dir: str | Path | None = None) -> None:
    """Raise if NPC catalog validation fails."""

    errors = validate_npc_catalog(world_dir)
    if errors:
        raise EngineValidationError("Invalid NPC catalog: " + "; ".join(errors))
    action_errors = validate_npc_action_catalog()
    if action_errors:
        raise EngineValidationError(
            "Invalid NPC action catalog: " + "; ".join(action_errors)
        )


def get_npc(npc_id: str, *, catalog: NpcCatalog | None = None) -> NpcDefinition:
    """Return one NPC definition or raise."""

    cat = catalog if catalog is not None else load_npc_catalog()
    npc = cat.by_id.get(npc_id)
    if npc is None:
        raise EngineValidationError(f"Unknown NPC: {npc_id!r}")
    return npc


def list_npcs(*, catalog: NpcCatalog | None = None) -> list[NpcDefinition]:
    """Return all NPCs in catalog order."""

    cat = catalog if catalog is not None else load_npc_catalog()
    return list(cat.npcs)


def clamp_relationship_score(score: int) -> int:
    """Clamp relationship into the allowed band."""

    return max(RELATIONSHIP_SCORE_MIN, min(RELATIONSHIP_SCORE_MAX, int(score)))


def resolve_npc_sect_id(
    definition: NpcDefinition,
    *,
    sect_id_override: str | None,
) -> str | None:
    """Effective sect id: override wins when set."""

    if sect_id_override:
        return sect_id_override
    return definition.sect_id


def _validate_requirements(
    *,
    action: NpcActionDefinition,
    definition: NpcDefinition,
    state: NpcWorldStateRecord,
    player: NpcInteractionPlayerContext,
    npc_sect_id: str | None,
) -> None:
    """Raise with a clear message on the first unmet requirement."""

    req = action.requirements
    if not action_offered_by_npc(action, definition):
        raise EngineValidationError(
            f"{definition.display_name} does not offer {action.label}."
        )

    if req.required_location_ids and player.location_id not in req.required_location_ids:
        raise EngineValidationError(
            f"You must be at a valid location to {action.label.lower()}."
        )

    if req.required_sect_id is not None:
        if player.sect_id != req.required_sect_id:
            raise EngineValidationError(
                f"You must be a member of {req.required_sect_id} to "
                f"{action.label.lower()}."
            )

    if req.required_sect_rank_ids:
        if player.sect_rank_id not in req.required_sect_rank_ids:
            raise EngineValidationError(
                f"Your sect rank does not permit {action.label.lower()}."
            )

    if req.required_realm_ids and player.realm_id not in req.required_realm_ids:
        raise EngineValidationError(
            f"Your realm does not permit {action.label.lower()}."
        )

    if req.min_realm_order is not None:
        from ai_adventure.engine.realms import get_realm

        if get_realm(player.realm_id).order_index < int(req.min_realm_order):
            raise EngineValidationError(
                f"Your realm is too low to {action.label.lower()}."
            )

    if req.required_stage_ids and player.stage_id not in req.required_stage_ids:
        raise EngineValidationError(
            f"Your stage does not permit {action.label.lower()}."
        )

    standing_value = 0 if player.sect_standing is None else int(player.sect_standing)
    role_floor = required_standing_for_npc_action(
        action_min_sect_standing=req.min_sect_standing,
        min_sect_standing_by_role=dict(req.min_sect_standing_by_role),
        npc_role_tags=list(definition.role_tags),
    )
    if role_floor is not None:
        if npc_sect_id is None:
            raise EngineValidationError(
                f"{definition.display_name} has no sect standing to evaluate."
            )
        if standing_value < role_floor:
            raise EngineValidationError(
                f"Sect standing {standing_value} is below the requirement "
                f"{role_floor} to {action.label.lower()} {definition.display_name}."
            )

    if req.min_relationship is not None:
        if int(state.relationship_score) < int(req.min_relationship):
            raise EngineValidationError(
                f"Relationship {state.relationship_score} is below the requirement "
                f"{req.min_relationship} to {action.label.lower()} "
                f"{definition.display_name}."
            )

    flags = player.story_flags
    for flag in req.flags_all:
        if not flags.get(flag, False):
            raise EngineValidationError(
                f"Missing required progress flag to {action.label.lower()}."
            )
    for flag in req.flags_none:
        if flags.get(flag, False):
            raise EngineValidationError(
                f"You have already done this with {definition.display_name}."
            )


def npc_action_eligible(
    *,
    action: NpcActionDefinition,
    definition: NpcDefinition,
    state: NpcWorldStateRecord,
    player: NpcInteractionPlayerContext,
    npc_sect_id: str | None,
) -> bool:
    """True when the action's requirements are met (no raise)."""

    try:
        _validate_requirements(
            action=action,
            definition=definition,
            state=state,
            player=player,
            npc_sect_id=npc_sect_id,
        )
    except EngineValidationError:
        return False
    return True


def plan_npc_interaction(
    *,
    definition: NpcDefinition,
    state: NpcWorldStateRecord,
    player: NpcInteractionPlayerContext,
    action_id: str,
    action_catalog: NpcActionCatalog | None = None,
) -> NpcInteractionResolution:
    """Pure NPC interaction plan: validate requirements and compute rewards."""

    action = get_npc_action(action_id, catalog=action_catalog)
    if state.status != "active":
        raise EngineValidationError(f"NPC {definition.npc_id!r} is not active")
    if not state.discovered:
        raise EngineValidationError(f"NPC {definition.npc_id!r} has not been discovered")
    if state.current_location_id != player.location_id:
        raise EngineValidationError(
            f"NPC {definition.display_name} is not at your current location"
        )

    npc_sect_id = resolve_npc_sect_id(definition, sect_id_override=state.sect_id_override)
    _validate_requirements(
        action=action,
        definition=definition,
        state=state,
        player=player,
        npc_sect_id=npc_sect_id,
    )

    relationship_before = int(state.relationship_score)
    relationship_delta = 0
    standing_delta = 0
    planned: list[PlannedNpcReward] = []
    flag_updates: list[tuple[str, bool]] = []
    technique_ids: list[str] = []
    items: list[tuple[str, int]] = []
    unlock_location_ids: list[str] = []
    trigger_kind: str | None = None

    for reward in action.rewards:
        planned.append(
            PlannedNpcReward(
                type=reward.type,
                delta=reward.delta,
                technique_id=reward.technique_id,
                flag=reward.flag,
                value=reward.value,
                item_code=reward.item_code,
                quantity=reward.quantity,
                trigger_kind=reward.trigger_kind,
                location_id=reward.location_id,
            )
        )
        if reward.type == "adjust_relationship":
            relationship_delta += int(reward.delta or 0)
        elif reward.type == "adjust_sect_standing":
            standing_delta += int(reward.delta or 0)
        elif reward.type == "learn_technique" and reward.technique_id:
            technique_ids.append(reward.technique_id)
        elif reward.type == "set_flag" and reward.flag:
            flag_updates.append((reward.flag, bool(True if reward.value is None else reward.value)))
        elif reward.type == "grant_item" and reward.item_code and reward.quantity:
            items.append((reward.item_code, int(reward.quantity)))
        elif reward.type == "emit_trigger" and reward.trigger_kind:
            trigger_kind = reward.trigger_kind
        elif reward.type == "unlock_location" and reward.location_id:
            unlock_location_ids.append(reward.location_id)

    relationship_after = clamp_relationship_score(relationship_before + relationship_delta)

    standing_before: int | None = None
    standing_after: int | None = None
    applies_standing = any(r.type == "adjust_sect_standing" for r in action.rewards)
    if npc_sect_id is not None and applies_standing:
        standing_before = 0 if player.sect_standing is None else int(player.sect_standing)
        standing_after = apply_standing_delta(
            current=standing_before,
            delta=standing_delta,
        )

    met = bool(state.met) or bool(action.marks_met)
    text = action.presentation_template.format(
        display_name=definition.display_name,
        description=definition.description,
        realm_id=definition.cultivation_summary.realm_id,
        stage_id=definition.cultivation_summary.stage_id,
    )
    return NpcInteractionResolution(
        npc_id=definition.npc_id,
        action_id=action.id,
        relationship_before=relationship_before,
        relationship_after=relationship_after,
        met=met,
        duration_days=int(action.duration_days),
        trigger_kind=trigger_kind,
        summary=f"{action.label}: {definition.display_name}.",
        presentation_text=text,
        sect_id=npc_sect_id,
        sect_standing_before=standing_before,
        sect_standing_after=standing_after,
        sect_standing_delta=standing_delta,
        planned_rewards=tuple(planned),
        flag_updates=tuple(flag_updates),
        technique_ids_to_learn=tuple(technique_ids),
        items_to_grant=tuple(items),
        location_ids_to_unlock=tuple(unlock_location_ids),
    )


def plan_greet(
    *,
    definition: NpcDefinition,
    state: NpcWorldStateRecord,
    player_location_id: str,
    player: NpcInteractionPlayerContext | None = None,
) -> NpcInteractionResolution:
    """Compatibility wrapper for the greet action."""

    ctx = player or NpcInteractionPlayerContext(
        location_id=player_location_id,
        realm_id="body_tempering",
        stage_id="early",
        sect_id=None,
        sect_rank_id=None,
        sect_standing=None,
        story_flags={},
    )
    return plan_npc_interaction(
        definition=definition,
        state=state,
        player=NpcInteractionPlayerContext(
            location_id=player_location_id,
            realm_id=ctx.realm_id,
            stage_id=ctx.stage_id,
            sect_id=ctx.sect_id,
            sect_rank_id=ctx.sect_rank_id,
            sect_standing=ctx.sect_standing,
            story_flags=dict(ctx.story_flags),
        ),
        action_id="greet",
    )


def _load_npc_catalog_unchecked(root: Path) -> tuple[NpcCatalog, list[str]]:
    errors: list[str] = []
    manifest_path = root / "world_manifest.json" if root != _WORLD_DIR else _WORLD_MANIFEST_PATH
    packs_dir = root / "packs" if root != _WORLD_DIR else _PACKS_DIR

    try:
        world = WorldManifest.model_validate(
            json.loads(manifest_path.read_text(encoding="utf-8"))
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return NpcCatalog(), [f"world manifest: {exc}"]

    locations = load_location_catalog(str(root) if root != _WORLD_DIR else None)
    try:
        sects = load_sect_catalog(str(root) if root != _WORLD_DIR else None)
    except EngineValidationError as exc:
        return NpcCatalog(), [str(exc)]

    merged: list[NpcDefinition] = []
    seen_ids: set[str] = set()
    loaded_packs: list[str] = []

    for pack_id in world.packs:
        pack_dir = packs_dir / pack_id
        pack_manifest_path = pack_dir / "manifest.json"
        if not pack_manifest_path.is_file():
            errors.append(f"pack {pack_id!r}: missing manifest.json")
            continue
        try:
            pack_manifest = WorldPackManifest.model_validate(
                json.loads(pack_manifest_path.read_text(encoding="utf-8"))
            )
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"pack {pack_id!r}: {exc}")
            continue
        if pack_manifest.pack_id != pack_id:
            errors.append(
                f"pack {pack_id!r}: manifest pack_id {pack_manifest.pack_id!r} mismatch"
            )
            continue

        rel = pack_manifest.content_files.get("npcs")
        if not rel:
            loaded_packs.append(pack_id)
            continue
        npc_path = pack_dir / rel
        if not npc_path.is_file():
            errors.append(f"pack {pack_id!r}: missing npcs file {rel!r}")
            continue
        try:
            raw = json.loads(npc_path.read_text(encoding="utf-8"))
            npc_file = NpcFile.model_validate(raw)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"pack {pack_id!r} npcs: {exc}")
            continue

        for npc in npc_file.npcs:
            if npc.npc_id in seen_ids:
                errors.append(f"duplicate npc_id {npc.npc_id!r}")
                continue
            seen_ids.add(npc.npc_id)
            if npc.home_location_id not in locations.by_id:
                errors.append(
                    f"NPC {npc.npc_id!r}: unknown home_location_id {npc.home_location_id!r}"
                )
            if npc.default_location_id not in locations.by_id:
                errors.append(
                    f"NPC {npc.npc_id!r}: unknown default_location_id {npc.default_location_id!r}"
                )
            if npc.sect_id is not None and npc.sect_id not in sects.by_id:
                errors.append(f"NPC {npc.npc_id!r}: unknown sect_id {npc.sect_id!r}")
            merged.append(npc.model_copy(update={"pack_id": pack_id}))
        loaded_packs.append(pack_id)

    return NpcCatalog(npcs=merged, pack_ids=loaded_packs), errors


__all__ = [
    "CultivationSummary",
    "GREET_RELATIONSHIP_DELTA",
    "IMPLEMENTED_NPC_REWARD_TYPES",
    "KNOWN_NPC_ACTION_IDS",
    "KNOWN_NPC_ROLE_TAGS",
    "NpcActionCatalog",
    "NpcActionDefinition",
    "NpcCatalog",
    "NpcDefinition",
    "NpcFile",
    "NpcInteractionPlayerContext",
    "NpcInteractionRequirements",
    "NpcInteractionResolution",
    "NpcInteractionReward",
    "NpcStatus",
    "NpcWorldStateRecord",
    "PlannedNpcReward",
    "RELATIONSHIP_SCORE_MAX",
    "RELATIONSHIP_SCORE_MIN",
    "RESERVED_NPC_REWARD_TYPES",
    "action_offered_by_npc",
    "assert_npc_catalog_valid",
    "clamp_relationship_score",
    "clear_npc_action_catalog_cache",
    "clear_npc_catalog_cache",
    "get_npc",
    "get_npc_action",
    "list_npc_actions",
    "list_npcs",
    "list_offered_actions_for_npc",
    "load_npc_action_catalog",
    "load_npc_catalog",
    "npc_action_eligible",
    "plan_greet",
    "plan_npc_interaction",
    "resolve_npc_sect_id",
    "validate_npc_action_catalog",
    "validate_npc_catalog",
]
