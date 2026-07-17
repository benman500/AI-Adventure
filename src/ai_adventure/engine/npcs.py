"""NPC catalog + interaction rules (Phase 9a–9b).

Catalogs define identity. Saves store mutable ``npc_world_state`` only.
Story spawns by ``npc_id``. Consumers of presentation read catalog names.
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
    LocationCatalog,
    WorldManifest,
    WorldPackManifest,
    _WORLD_DIR,
    _PACKS_DIR,
    _WORLD_MANIFEST_PATH,
    load_location_catalog,
)
from ai_adventure.engine.sects import SectCatalog, load_sect_catalog

NpcStatus = Literal["active", "dead", "absent"]

RELATIONSHIP_SCORE_MIN = -100
RELATIONSHIP_SCORE_MAX = 100
GREET_RELATIONSHIP_DELTA = 5

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
    }
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


@dataclass(frozen=True, slots=True)
class NpcInteractionResolution:
    """Pure result of one NPC interaction."""

    npc_id: str
    action_id: str
    relationship_before: int
    relationship_after: int
    met: bool
    summary: str
    presentation_text: str


def clear_npc_catalog_cache() -> None:
    """Drop cached NPC catalog (tests)."""

    load_npc_catalog.cache_clear()


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


def plan_greet(
    *,
    definition: NpcDefinition,
    state: NpcWorldStateRecord,
    player_location_id: str,
) -> NpcInteractionResolution:
    """Pure greet interaction: colocated active NPC → relationship delta."""

    if state.status != "active":
        raise EngineValidationError(f"NPC {definition.npc_id!r} is not active")
    if not state.discovered:
        raise EngineValidationError(f"NPC {definition.npc_id!r} has not been discovered")
    if state.current_location_id != player_location_id:
        raise EngineValidationError(
            f"NPC {definition.display_name} is not at your current location"
        )

    before = int(state.relationship_score)
    after = clamp_relationship_score(before + GREET_RELATIONSHIP_DELTA)
    text = (
        f"You greet {definition.display_name}. "
        f"They acknowledge you with a measured nod."
    )
    return NpcInteractionResolution(
        npc_id=definition.npc_id,
        action_id="greet",
        relationship_before=before,
        relationship_after=after,
        met=True,
        summary=f"Greeted {definition.display_name}.",
        presentation_text=text,
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
    "KNOWN_NPC_ROLE_TAGS",
    "NpcCatalog",
    "NpcDefinition",
    "NpcFile",
    "NpcInteractionResolution",
    "NpcStatus",
    "NpcWorldStateRecord",
    "RELATIONSHIP_SCORE_MAX",
    "RELATIONSHIP_SCORE_MIN",
    "assert_npc_catalog_valid",
    "clamp_relationship_score",
    "clear_npc_catalog_cache",
    "get_npc",
    "list_npcs",
    "load_npc_catalog",
    "plan_greet",
    "resolve_npc_sect_id",
    "validate_npc_catalog",
]
