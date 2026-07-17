"""Technique catalog and mastery → EffectInstance source adapter (Phase 6c).

Techniques are the first Modifier Framework source. Consumers must never read
this module for math — they receive a ``ModifierSnapshot`` only.
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
from ai_adventure.engine.realms import get_realm

_TECHNIQUES_PATH = Path(__file__).resolve().parents[1] / "data" / "techniques" / "techniques.json"


class TechniqueDefinition(BaseModel):
    """One encyclopedia technique record (catalog authority)."""

    id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    primary_category: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    grade_rank: int = Field(ge=1)
    min_realm_order: int = Field(ge=1)
    effect_bundle_id: str = Field(min_length=1)
    description: str = Field(min_length=1)


class TechniqueCatalog(BaseModel):
    """Authored technique encyclopedia (MVP starter set)."""

    schema_version: int = Field(ge=1)
    techniques: list[TechniqueDefinition] = Field(min_length=1)

    @field_validator("techniques")
    @classmethod
    def _unique_ids(cls, value: list[TechniqueDefinition]) -> list[TechniqueDefinition]:
        ids = [item.id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate technique ids")
        return value


@dataclass(frozen=True, slots=True)
class TechniqueMasteryRecord:
    """Mutable mastery facts for one actor/technique (engine DTO, not ORM)."""

    actor_id: str
    technique_id: str
    known: bool
    equipped: bool
    mastery_rank: int
    mastery_progress: int = 0


@lru_cache(maxsize=1)
def load_technique_catalog(path: str | None = None) -> TechniqueCatalog:
    """Load the technique catalog."""

    catalog_path = Path(path) if path else _TECHNIQUES_PATH
    if not catalog_path.is_file():
        raise EngineValidationError(f"Technique catalog missing: {catalog_path}")
    try:
        raw = json.loads(catalog_path.read_text(encoding="utf-8"))
        return TechniqueCatalog.model_validate(raw)
    except json.JSONDecodeError as exc:
        raise EngineValidationError(f"Corrupted technique catalog: {catalog_path.name}") from exc
    except Exception as exc:  # noqa: BLE001
        raise EngineValidationError(f"Invalid technique catalog: {exc}") from exc


def clear_technique_catalog_cache() -> None:
    """Clear cached technique catalog (tests)."""

    load_technique_catalog.cache_clear()


def list_techniques(path: str | None = None) -> list[TechniqueDefinition]:
    """Return techniques in catalog order."""

    return list(load_technique_catalog(path).techniques)


def get_technique(technique_id: str, path: str | None = None) -> TechniqueDefinition:
    """Return one technique or raise."""

    for item in list_techniques(path):
        if item.id == technique_id:
            return item
    raise EngineValidationError(f"Unknown technique: {technique_id}")


def validate_technique_catalog_against_bundles(
    catalog: TechniqueCatalog | None = None,
    *,
    bundles: EffectBundleCatalog | None = None,
    type_registry: EffectTypeRegistry | None = None,
) -> None:
    """Ensure every technique references a known, valid effect bundle."""

    catalog = catalog or load_technique_catalog()
    registry = type_registry or load_effect_type_registry()
    bundle_catalog = bundles or load_effect_bundle_catalog(type_registry=registry)
    for tech in catalog.techniques:
        try:
            bundle_catalog.get(tech.effect_bundle_id)
        except EngineValidationError as exc:
            raise EngineValidationError(
                f"Technique {tech.id!r} references unknown bundle {tech.effect_bundle_id!r}"
            ) from exc


def can_learn_technique(
    technique: TechniqueDefinition,
    *,
    realm_id: str,
) -> tuple[bool, str | None]:
    """Return whether an actor may learn a technique given realm order."""

    realm = get_realm(realm_id)
    if realm.order_index < technique.min_realm_order:
        return False, (
            f"Requires realm order {technique.min_realm_order} "
            f"(current: {realm.order_index})."
        )
    return True, None


def mastery_rank_to_magnitude_scale(mastery_rank: int) -> float:
    """Map mastery rank to modifier magnitude scale (Phase 6c: rank 1 = 1.0)."""

    if mastery_rank < 1:
        raise EngineValidationError("mastery_rank must be >= 1")
    return 1.0 + 0.0 * (mastery_rank - 1)


def technique_mastery_to_effect_instances(
    mastery_rows: Sequence[TechniqueMasteryRecord],
    *,
    catalog: TechniqueCatalog | None = None,
) -> list[EffectInstance]:
    """Convert equipped known techniques into EffectInstances.

    This is a **source adapter** only. Session/combat consumers must not call
    this — they receive a ``ModifierSnapshot`` from the service layer.
    """

    catalog = catalog or load_technique_catalog()
    by_id = {item.id: item for item in catalog.techniques}
    instances: list[EffectInstance] = []
    for row in mastery_rows:
        if not row.known or not row.equipped:
            continue
        technique = by_id.get(row.technique_id)
        if technique is None:
            raise EngineValidationError(
                f"Mastery references unknown technique: {row.technique_id!r}"
            )
        instances.append(
            EffectInstance(
                source_kind="technique_mastery",
                source_id=row.technique_id,
                actor_id=row.actor_id,
                bundle_id=technique.effect_bundle_id,
                magnitude_scale=mastery_rank_to_magnitude_scale(row.mastery_rank),
            )
        )
    return instances


__all__ = [
    "TechniqueCatalog",
    "TechniqueDefinition",
    "TechniqueMasteryRecord",
    "can_learn_technique",
    "clear_technique_catalog_cache",
    "get_technique",
    "list_techniques",
    "load_technique_catalog",
    "mastery_rank_to_magnitude_scale",
    "technique_mastery_to_effect_instances",
    "validate_technique_catalog_against_bundles",
]
