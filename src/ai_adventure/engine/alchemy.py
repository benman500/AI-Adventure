"""Alchemy (Phase 8): catalog + adapter → EffectInstances.

Alchemy is the next Modifier Framework source. It must not introduce a new
calculation system; it only converts awakened ownership → allowlisted
EffectInstances so `ModifierSnapshot` aggregation stays unchanged.
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

_ALCHEMY_DIR = Path(__file__).resolve().parents[1] / "data" / "alchemy"
_RECIPES_PATH = _ALCHEMY_DIR / "alchemy_recipes.json"


class AlchemyRecipeDefinition(BaseModel):
    """One alchemy recipe record (catalog authority)."""

    id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    grade_rank: int = Field(ge=1)
    effect_bundle_id: str = Field(min_length=1)
    description: str = Field(min_length=1)


class AlchemyRecipeCatalog(BaseModel):
    """Authored alchemy recipe catalog."""

    schema_version: int = Field(ge=1)
    recipes: list[AlchemyRecipeDefinition] = Field(min_length=1)

    @field_validator("recipes")
    @classmethod
    def _unique_ids(cls, value: list[AlchemyRecipeDefinition]) -> list[AlchemyRecipeDefinition]:
        ids = [item.id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate alchemy recipe ids")
        return value


@dataclass(frozen=True, slots=True)
class AlchemyRecipeOwnershipRecord:
    """Mutable ownership facts for one actor/recipe (engine DTO)."""

    actor_id: str
    recipe_id: str
    awakened: bool
    grade_rank: int


@lru_cache(maxsize=1)
def load_alchemy_recipe_catalog(path: str | None = None) -> AlchemyRecipeCatalog:
    """Load and validate the alchemy recipe catalog."""

    catalog_path = Path(path) if path else _RECIPES_PATH
    if not catalog_path.is_file():
        raise EngineValidationError(f"Alchemy recipe catalog missing: {catalog_path}")
    try:
        raw = json.loads(catalog_path.read_text(encoding="utf-8"))
        return AlchemyRecipeCatalog.model_validate(raw)
    except json.JSONDecodeError as exc:
        raise EngineValidationError(
            f"Corrupted alchemy recipe catalog: {catalog_path.name}"
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise EngineValidationError(f"Invalid alchemy recipe catalog: {exc}") from exc


def clear_alchemy_recipe_catalog_cache() -> None:
    """Clear cached alchemy catalog (tests)."""

    load_alchemy_recipe_catalog.cache_clear()


def list_alchemy_recipes(path: str | None = None) -> list[AlchemyRecipeDefinition]:
    """Return roots in catalog order."""

    return list(load_alchemy_recipe_catalog(path).recipes)


def get_alchemy_recipe(
    recipe_id: str, path: str | None = None
) -> AlchemyRecipeDefinition:
    """Return one recipe or raise."""

    for item in list_alchemy_recipes(path):
        if item.id == recipe_id:
            return item
    raise EngineValidationError(f"Unknown alchemy recipe: {recipe_id}")


def validate_alchemy_recipe_catalog_against_bundles(
    catalog: AlchemyRecipeCatalog | None = None,
    *,
    bundles: EffectBundleCatalog | None = None,
    type_registry: EffectTypeRegistry | None = None,
) -> None:
    """Ensure every recipe references a known valid effect bundle."""

    catalog = catalog or load_alchemy_recipe_catalog()
    registry = type_registry or load_effect_type_registry()
    bundle_catalog = bundles or load_effect_bundle_catalog(type_registry=registry)
    for recipe in catalog.recipes:
        try:
            bundle_catalog.get(recipe.effect_bundle_id)
        except EngineValidationError as exc:
            raise EngineValidationError(
                f"Alchemy recipe {recipe.id!r} references unknown bundle {recipe.effect_bundle_id!r}"
            ) from exc


def grade_rank_to_magnitude_scale(grade_rank: int) -> float:
    """Map alchemy grade to EffectInstance magnitude scale (Phase 8)."""

    if grade_rank < 1:
        raise EngineValidationError("grade_rank must be >= 1")
    return 1.0 + 0.0 * (grade_rank - 1)


def alchemy_ownership_to_effect_instances(
    ownership_rows: Sequence[AlchemyRecipeOwnershipRecord],
    *,
    catalog: AlchemyRecipeCatalog | None = None,
) -> list[EffectInstance]:
    """Convert awakened alchemy ownership into EffectInstances."""

    catalog = catalog or load_alchemy_recipe_catalog()
    by_id = {item.id: item for item in catalog.recipes}
    instances: list[EffectInstance] = []
    for row in ownership_rows:
        if not row.awakened:
            continue
        recipe = by_id.get(row.recipe_id)
        if recipe is None:
            raise EngineValidationError(
                f"Ownership references unknown alchemy recipe: {row.recipe_id!r}"
            )
        instances.append(
            EffectInstance(
                source_kind="alchemy",
                source_id=row.recipe_id,
                actor_id=row.actor_id,
                bundle_id=recipe.effect_bundle_id,
                magnitude_scale=grade_rank_to_magnitude_scale(row.grade_rank),
            )
        )
    return instances


__all__ = [
    "AlchemyRecipeCatalog",
    "AlchemyRecipeDefinition",
    "AlchemyRecipeOwnershipRecord",
    "clear_alchemy_recipe_catalog_cache",
    "grade_rank_to_magnitude_scale",
    "get_alchemy_recipe",
    "list_alchemy_recipes",
    "load_alchemy_recipe_catalog",
    "alchemy_ownership_to_effect_instances",
    "validate_alchemy_recipe_catalog_against_bundles",
]

