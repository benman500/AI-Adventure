"""Sect catalog (Phase 9a) — pack-local authored factions.

Player membership remains on ``sect_membership``. This module is catalog
authority for sect identity and rank ladders; NPC ``sect_id`` refs validate here.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

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


class SectRankDefinition(BaseModel):
    """One authored rank on a sect ladder."""

    rank_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    order: int = Field(ge=0)


class SectDefinition(BaseModel):
    """One authored sect from a world content pack."""

    sect_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    home_location_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    ranks: list[SectRankDefinition] = Field(min_length=1)
    pack_id: str = Field(default="", min_length=0)

    @field_validator("ranks")
    @classmethod
    def _unique_ranks(cls, value: list[SectRankDefinition]) -> list[SectRankDefinition]:
        ids = [item.rank_id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate rank_id values")
        return value


class SectFile(BaseModel):
    """One pack sects content file."""

    schema_version: int = Field(ge=1)
    sects: list[SectDefinition] = Field(default_factory=list)


class SectCatalog(BaseModel):
    """Merged sect catalog across world packs."""

    sects: list[SectDefinition] = Field(default_factory=list)
    pack_ids: list[str] = Field(default_factory=list)

    @property
    def by_id(self) -> dict[str, SectDefinition]:
        """Index sects by stable id."""

        return {item.sect_id: item for item in self.sects}


def clear_sect_catalog_cache() -> None:
    """Drop cached sect catalog (tests)."""

    load_sect_catalog.cache_clear()


@lru_cache(maxsize=1)
def load_sect_catalog(world_dir: str | None = None) -> SectCatalog:
    """Load and validate the merged sect catalog."""

    root = Path(world_dir) if world_dir is not None else _WORLD_DIR
    catalog, errors = _load_sect_catalog_unchecked(root)
    if errors:
        raise EngineValidationError("Invalid sect catalog: " + "; ".join(errors))
    return catalog


def validate_sect_catalog(world_dir: str | Path | None = None) -> list[str]:
    """Return validation error messages (empty if ok)."""

    root = Path(world_dir) if world_dir is not None else _WORLD_DIR
    try:
        _, errors = _load_sect_catalog_unchecked(root)
        return list(errors)
    except (OSError, json.JSONDecodeError, ValueError, EngineValidationError) as exc:
        return [str(exc)]


def assert_sect_catalog_valid(world_dir: str | Path | None = None) -> None:
    """Raise if sect catalog validation fails."""

    errors = validate_sect_catalog(world_dir)
    if errors:
        raise EngineValidationError("Invalid sect catalog: " + "; ".join(errors))


def get_sect(sect_id: str, *, catalog: SectCatalog | None = None) -> SectDefinition:
    """Return one sect definition or raise."""

    cat = catalog if catalog is not None else load_sect_catalog()
    sect = cat.by_id.get(sect_id)
    if sect is None:
        raise EngineValidationError(f"Unknown sect: {sect_id!r}")
    return sect


def _load_sect_catalog_unchecked(root: Path) -> tuple[SectCatalog, list[str]]:
    errors: list[str] = []
    manifest_path = root / "world_manifest.json" if root != _WORLD_DIR else _WORLD_MANIFEST_PATH
    packs_dir = root / "packs" if root != _WORLD_DIR else _PACKS_DIR

    try:
        world = WorldManifest.model_validate(
            json.loads(manifest_path.read_text(encoding="utf-8"))
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return SectCatalog(), [f"world manifest: {exc}"]

    locations = load_location_catalog(str(root) if root != _WORLD_DIR else None)

    merged: list[SectDefinition] = []
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

        rel = pack_manifest.content_files.get("sects")
        if not rel:
            loaded_packs.append(pack_id)
            continue
        sect_path = pack_dir / rel
        if not sect_path.is_file():
            errors.append(f"pack {pack_id!r}: missing sects file {rel!r}")
            continue
        try:
            raw = json.loads(sect_path.read_text(encoding="utf-8"))
            sect_file = SectFile.model_validate(raw)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"pack {pack_id!r} sects: {exc}")
            continue

        for sect in sect_file.sects:
            if sect.sect_id in seen_ids:
                errors.append(f"duplicate sect_id {sect.sect_id!r}")
                continue
            seen_ids.add(sect.sect_id)
            if sect.home_location_id not in locations.by_id:
                errors.append(
                    f"sect {sect.sect_id!r}: unknown home_location_id {sect.home_location_id!r}"
                )
            merged.append(sect.model_copy(update={"pack_id": pack_id}))
        loaded_packs.append(pack_id)

    return SectCatalog(sects=merged, pack_ids=loaded_packs), errors


__all__ = [
    "SectCatalog",
    "SectDefinition",
    "SectFile",
    "SectRankDefinition",
    "assert_sect_catalog_valid",
    "clear_sect_catalog_cache",
    "get_sect",
    "load_sect_catalog",
    "validate_sect_catalog",
]
