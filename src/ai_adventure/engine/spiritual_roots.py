"""Spiritual root catalog and ownership → EffectInstance source adapter (Phase 7).

Spiritual roots are the second Modifier Framework source. Consumers must never
read this module for math — they receive a ``ModifierSnapshot`` only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Sequence

from pydantic import BaseModel, Field, field_validator

from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.modifiers import (
    EffectBundleCatalog,
    EffectInstance,
    EffectTypeRegistry,
    load_effect_bundle_catalog,
    load_effect_type_registry,
)

_ROOTS_PATH = Path(__file__).resolve().parents[1] / "data" / "cultivation" / "spiritual_roots.json"

STARTER_ROOT_ID = "root_wood_steady"


class SpiritualRootDefinition(BaseModel):
    """One spiritual root catalog record."""

    id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    element: str = Field(min_length=1)
    grade_rank: int = Field(ge=1)
    effect_bundle_id: str = Field(min_length=1)
    description: str = Field(min_length=1)


class SpiritualRootCatalog(BaseModel):
    """Authored spiritual root catalog."""

    schema_version: int = Field(ge=1)
    roots: list[SpiritualRootDefinition] = Field(min_length=1)

    @field_validator("roots")
    @classmethod
    def _unique_ids(cls, value: list[SpiritualRootDefinition]) -> list[SpiritualRootDefinition]:
        ids = [item.id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate spiritual root ids")
        return value


@dataclass(frozen=True, slots=True)
class SpiritualRootOwnershipRecord:
    """Mutable ownership facts for one actor/root (engine DTO, not ORM)."""

    actor_id: str
    root_id: str
    awakened: bool
    grade_rank: int


@lru_cache(maxsize=1)
def load_spiritual_root_catalog(path: str | None = None) -> SpiritualRootCatalog:
    """Load the spiritual root catalog."""

    catalog_path = Path(path) if path else _ROOTS_PATH
    if not catalog_path.is_file():
        raise EngineValidationError(f"Spiritual root catalog missing: {catalog_path}")
    try:
        raw = json.loads(catalog_path.read_text(encoding="utf-8"))
        return SpiritualRootCatalog.model_validate(raw)
    except json.JSONDecodeError as exc:
        raise EngineValidationError(f"Corrupted spiritual root catalog: {catalog_path.name}") from exc
    except Exception as exc:  # noqa: BLE001
        raise EngineValidationError(f"Invalid spiritual root catalog: {exc}") from exc


def clear_spiritual_root_catalog_cache() -> None:
    """Clear cached spiritual root catalog (tests)."""

    load_spiritual_root_catalog.cache_clear()


def list_spiritual_roots(path: str | None = None) -> list[SpiritualRootDefinition]:
    """Return roots in catalog order."""

    return list(load_spiritual_root_catalog(path).roots)


def get_spiritual_root(root_id: str, path: str | None = None) -> SpiritualRootDefinition:
    """Return one root or raise."""

    for item in list_spiritual_roots(path):
        if item.id == root_id:
            return item
    raise EngineValidationError(f"Unknown spiritual root: {root_id}")


def validate_spiritual_root_catalog_against_bundles(
    catalog: SpiritualRootCatalog | None = None,
    *,
    bundles: EffectBundleCatalog | None = None,
    type_registry: EffectTypeRegistry | None = None,
) -> None:
    """Ensure every root references a known, valid effect bundle."""

    catalog = catalog or load_spiritual_root_catalog()
    registry = type_registry or load_effect_type_registry()
    bundle_catalog = bundles or load_effect_bundle_catalog(type_registry=registry)
    for root in catalog.roots:
        try:
            bundle_catalog.get(root.effect_bundle_id)
        except EngineValidationError as exc:
            raise EngineValidationError(
                f"Spiritual root {root.id!r} references unknown bundle {root.effect_bundle_id!r}"
            ) from exc


def grade_rank_to_magnitude_scale(grade_rank: int) -> float:
    """Map root grade to modifier magnitude scale (Phase 7: grade 1 = 1.0)."""

    if grade_rank < 1:
        raise EngineValidationError("grade_rank must be >= 1")
    return 1.0 + 0.0 * (grade_rank - 1)


def spiritual_root_ownership_to_effect_instances(
    ownership_rows: Sequence[SpiritualRootOwnershipRecord],
    *,
    catalog: SpiritualRootCatalog | None = None,
) -> list[EffectInstance]:
    """Convert awakened spiritual roots into EffectInstances.

    This is a **source adapter** only. Consumers must not call this — they
    receive a ``ModifierSnapshot`` from the service layer.
    """

    catalog = catalog or load_spiritual_root_catalog()
    by_id = {item.id: item for item in catalog.roots}
    instances: list[EffectInstance] = []
    for row in ownership_rows:
        if not row.awakened:
            continue
        root = by_id.get(row.root_id)
        if root is None:
            raise EngineValidationError(
                f"Ownership references unknown spiritual root: {row.root_id!r}"
            )
        instances.append(
            EffectInstance(
                source_kind="spiritual_root",
                source_id=row.root_id,
                actor_id=row.actor_id,
                bundle_id=root.effect_bundle_id,
                magnitude_scale=grade_rank_to_magnitude_scale(row.grade_rank),
            )
        )
    return instances


__all__ = [
    "STARTER_ROOT_ID",
    "SpiritualRootCatalog",
    "SpiritualRootDefinition",
    "SpiritualRootOwnershipRecord",
    "clear_spiritual_root_catalog_cache",
    "get_spiritual_root",
    "grade_rank_to_magnitude_scale",
    "list_spiritual_roots",
    "load_spiritual_root_catalog",
    "spiritual_root_ownership_to_effect_instances",
    "validate_spiritual_root_catalog_against_bundles",
]
