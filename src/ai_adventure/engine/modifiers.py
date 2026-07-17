"""Modifier Framework (Phase 6b): deterministic influence aggregation.

Answers one question only: what mechanical influences apply to this actor
right now? Not an ability system, scripting engine, or mutation pipeline.

Snapshots are ephemeral and never persisted. Consumers (Phase 6c+) read
``ModifierSnapshot`` only — never technique tables for math.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, Mapping, Sequence

from pydantic import BaseModel, Field, field_validator, model_validator

from ai_adventure.engine.errors import EngineValidationError

_MODIFIERS_DIR = Path(__file__).resolve().parents[1] / "data" / "modifiers"
_EFFECT_TYPES_PATH = _MODIFIERS_DIR / "effect_types.json"
_EFFECT_BUNDLES_PATH = _MODIFIERS_DIR / "effect_bundles.json"

ValueType = Literal["number", "boolean"]
AggregationRule = Literal["sum", "multiply", "or"]
ParamKey = Literal["flat", "mult", "flag"]

ModifierSourceKind = Literal[
    "technique_mastery",
    "spiritual_root",
    "alchemy",
    "equipment",
    "artifact",
    "temporary_status",
    "sect_bonus",
    "location_aura",
    "cultivation_path",
    "test_fixture",
]

KNOWN_ACTIVITIES: frozenset[str] = frozenset(
    {
        "cultivate_session",
        "breakthrough",
        "world_event",
        "travel",
        "combat",
    }
)


class EffectTypeDefinition(BaseModel):
    """One allowlisted effect type — sole authority for interpretation."""

    id: str = Field(min_length=1)
    value_type: ValueType
    aggregation: AggregationRule
    param_key: ParamKey
    identity: float | bool
    cap_min: float | None = None
    cap_max: float | None = None
    allowed_contexts: list[str] = Field(min_length=1)
    description: str = ""

    @field_validator("allowed_contexts")
    @classmethod
    def _unique_nonempty_contexts(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if not cleaned:
            raise ValueError("allowed_contexts must be non-empty")
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("duplicate allowed_contexts")
        unknown = sorted(set(cleaned) - KNOWN_ACTIVITIES)
        if unknown:
            raise ValueError(f"unknown allowed_contexts: {unknown}")
        return cleaned

    @model_validator(mode="after")
    def _consistent_type_rules(self) -> EffectTypeDefinition:
        if self.value_type == "number" and self.aggregation == "or":
            raise ValueError(f"{self.id}: number types cannot use aggregation 'or'")
        if self.value_type == "boolean" and self.aggregation != "or":
            raise ValueError(f"{self.id}: boolean types must use aggregation 'or'")
        if self.aggregation == "sum" and self.param_key != "flat":
            raise ValueError(f"{self.id}: sum aggregation requires param_key 'flat'")
        if self.aggregation == "multiply" and self.param_key != "mult":
            raise ValueError(f"{self.id}: multiply aggregation requires param_key 'mult'")
        if self.aggregation == "or" and self.param_key != "flag":
            raise ValueError(f"{self.id}: or aggregation requires param_key 'flag'")
        if self.aggregation == "sum" and self.identity != 0 and self.identity != 0.0:
            raise ValueError(f"{self.id}: sum identity must be 0")
        if self.aggregation == "multiply" and self.identity != 1 and self.identity != 1.0:
            raise ValueError(f"{self.id}: multiply identity must be 1")
        if self.aggregation == "or" and self.identity is not False:
            raise ValueError(f"{self.id}: or identity must be false")
        if self.cap_min is not None and self.cap_max is not None and self.cap_min > self.cap_max:
            raise ValueError(f"{self.id}: cap_min cannot exceed cap_max")
        return self


class EffectTypeRegistry(BaseModel):
    """Authoritative effect-type registry."""

    schema_version: int = Field(ge=1)
    effect_types: list[EffectTypeDefinition] = Field(min_length=1)

    @field_validator("effect_types")
    @classmethod
    def _unique_ids(cls, value: list[EffectTypeDefinition]) -> list[EffectTypeDefinition]:
        ids = [item.id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate effect type ids")
        return value

    def get(self, type_id: str) -> EffectTypeDefinition:
        """Return a type definition or raise."""

        for item in self.effect_types:
            if item.id == type_id:
                return item
        raise EngineValidationError(f"Unknown effect type: {type_id!r}")

    def as_map(self) -> dict[str, EffectTypeDefinition]:
        """Return id → definition mapping."""

        return {item.id: item for item in self.effect_types}


class EffectSpec(BaseModel):
    """One parametric effect entry inside a bundle or inline instance.

    Optional ``category`` buckets numeric aggregation (e.g. event category
    ``cultivation``). Omit for a global contribution of that effect type.
    """

    type: str = Field(min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)
    applies_to: list[str] = Field(min_length=1)
    category: str | None = None

    @field_validator("applies_to")
    @classmethod
    def _unique_applies_to(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if not cleaned:
            raise ValueError("applies_to must be non-empty")
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("duplicate applies_to entries")
        return cleaned

    @field_validator("category")
    @classmethod
    def _normalize_category(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("category must be non-empty when provided")
        return cleaned


class EffectBundle(BaseModel):
    """Reusable pack of typed effects."""

    id: str = Field(min_length=1)
    schema_version: int = Field(ge=1)
    effects: list[EffectSpec] = Field(min_length=1)


class EffectBundleCatalog(BaseModel):
    """Catalog of effect bundles."""

    schema_version: int = Field(ge=1)
    bundles: list[EffectBundle] = Field(default_factory=list)

    @field_validator("bundles")
    @classmethod
    def _unique_bundle_ids(cls, value: list[EffectBundle]) -> list[EffectBundle]:
        ids = [item.id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate effect bundle ids")
        return value

    def get(self, bundle_id: str) -> EffectBundle:
        """Return a bundle or raise."""

        for item in self.bundles:
            if item.id == bundle_id:
                return item
        raise EngineValidationError(f"Unknown effect bundle: {bundle_id!r}")


class EffectInstance(BaseModel):
    """One active source contribution for an actor."""

    source_kind: ModifierSourceKind
    source_id: str = Field(min_length=1)
    actor_id: str = Field(min_length=1)
    bundle_id: str | None = None
    inline_effects: list[EffectSpec] | None = None
    expires_world_day: int | None = Field(default=None, ge=0)
    magnitude_scale: float = Field(default=1.0, gt=0.0)

    @model_validator(mode="after")
    def _require_effects_source(self) -> EffectInstance:
        has_bundle = bool(self.bundle_id)
        has_inline = bool(self.inline_effects)
        if has_bundle == has_inline:
            raise ValueError("EffectInstance requires exactly one of bundle_id or inline_effects")
        return self


@dataclass(frozen=True, slots=True)
class ModifierContext:
    """Aggregation context for one actor activity."""

    actor_id: str
    world_day: int
    activity: str


@dataclass(frozen=True, slots=True)
class ModifierContribution:
    """Audit trail entry explaining one contribution toward a resolved value."""

    source_kind: str
    source_id: str
    effect_type: str
    detail: str
    raw: float | str | bool
    applied: float | str | bool
    category: str | None = None


@dataclass(frozen=True, slots=True)
class ModifierSnapshot:
    """Ephemeral resolved influences. Never persist this object."""

    numbers: Mapping[str, float]
    flags: frozenset[str]
    contributions: tuple[ModifierContribution, ...]
    categorized_numbers: Mapping[str, Mapping[str, float]] = field(default_factory=dict)

    def number(
        self,
        effect_type_id: str,
        default: float = 0.0,
        *,
        category: str | None = None,
    ) -> float:
        """Return a resolved numeric modifier, or ``default`` if absent.

        ``category=None`` reads the global (uncategorized) bucket.
        """

        if category is None:
            return float(self.numbers.get(effect_type_id, default))
        by_cat = self.categorized_numbers.get(effect_type_id)
        if by_cat is None:
            return float(default)
        return float(by_cat.get(category, default))

    def has_flag(self, flag_id: str) -> bool:
        """Return whether a capability flag is granted."""

        return flag_id in self.flags


def consumer_number(
    snapshot: ModifierSnapshot | None,
    effect_type_id: str,
    *,
    supported: frozenset[str],
    default: float,
    category: str | None = None,
) -> float:
    """Read one numeric effect for a consumer.

    Unsupported types are never interpreted: if ``effect_type_id`` is not in
    the consumer's explicit allowlist, ``default`` is returned even when the
    snapshot contains that key.
    """

    if snapshot is None or effect_type_id not in supported:
        return default
    return snapshot.number(effect_type_id, default=default, category=category)


def ignored_snapshot_effect_types(
    snapshot: ModifierSnapshot | None,
    *,
    supported: frozenset[str],
) -> frozenset[str]:
    """Return snapshot effect type ids this consumer will not apply."""

    if snapshot is None:
        return frozenset()
    present = set(snapshot.numbers.keys()) | set(snapshot.categorized_numbers.keys())
    # Flags are a separate channel; only count typed numeric keys here.
    return frozenset(present - set(supported))


def _clamp(value: float, cap_min: float | None, cap_max: float | None) -> float:
    result = value
    if cap_min is not None:
        result = max(cap_min, result)
    if cap_max is not None:
        result = min(cap_max, result)
    return result


def _scaled_numeric(raw: float, *, aggregation: AggregationRule, magnitude_scale: float) -> float:
    if aggregation == "sum":
        return raw * magnitude_scale
    if aggregation == "multiply":
        return 1.0 + (raw - 1.0) * magnitude_scale
    raise EngineValidationError(f"Cannot scale aggregation {aggregation!r} as numeric")


def validate_effect_spec(spec: EffectSpec, type_def: EffectTypeDefinition) -> None:
    """Validate one effect spec against its type definition."""

    unknown_contexts = sorted(set(spec.applies_to) - set(type_def.allowed_contexts))
    if unknown_contexts:
        raise EngineValidationError(
            f"Effect type {type_def.id!r} applies_to not in allowed_contexts: {unknown_contexts}"
        )
    if type_def.param_key not in spec.params:
        raise EngineValidationError(
            f"Effect type {type_def.id!r} requires params.{type_def.param_key}"
        )
    unknown_keys = sorted(set(spec.params) - {type_def.param_key})
    if unknown_keys:
        raise EngineValidationError(
            f"Effect type {type_def.id!r} unknown params: {unknown_keys}"
        )
    value = spec.params[type_def.param_key]
    if type_def.param_key == "flag":
        if not isinstance(value, str) or not value.strip():
            raise EngineValidationError(f"Effect type {type_def.id!r} flag must be a non-empty string")
    else:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise EngineValidationError(
                f"Effect type {type_def.id!r} params.{type_def.param_key} must be a number"
            )


def validate_bundle_against_registry(
    bundle: EffectBundle,
    registry: EffectTypeRegistry,
) -> None:
    """Fail fast if a bundle references unknown or illegal effect types."""

    for index, spec in enumerate(bundle.effects):
        try:
            type_def = registry.get(spec.type)
            validate_effect_spec(spec, type_def)
        except EngineValidationError as exc:
            raise EngineValidationError(f"bundle {bundle.id!r} effects[{index}]: {exc}") from exc


def validate_bundle_catalog(
    catalog: EffectBundleCatalog,
    registry: EffectTypeRegistry,
) -> None:
    """Validate every bundle in a catalog against the type registry."""

    for bundle in catalog.bundles:
        validate_bundle_against_registry(bundle, registry)


@lru_cache(maxsize=1)
def load_effect_type_registry(path: str | None = None) -> EffectTypeRegistry:
    """Load and validate the effect type registry."""

    registry_path = Path(path) if path else _EFFECT_TYPES_PATH
    if not registry_path.is_file():
        raise EngineValidationError(f"Effect type registry missing: {registry_path}")
    try:
        raw = json.loads(registry_path.read_text(encoding="utf-8"))
        return EffectTypeRegistry.model_validate(raw)
    except json.JSONDecodeError as exc:
        raise EngineValidationError(f"Corrupted effect type registry: {registry_path.name}") from exc
    except EngineValidationError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise EngineValidationError(f"Invalid effect type registry: {exc}") from exc


@lru_cache(maxsize=1)
def _load_effect_bundle_catalog_raw(path: str | None = None) -> EffectBundleCatalog:
    """Load bundle catalog JSON without cross-registry validation."""

    catalog_path = Path(path) if path else _EFFECT_BUNDLES_PATH
    if not catalog_path.is_file():
        raise EngineValidationError(f"Effect bundle catalog missing: {catalog_path}")
    try:
        raw = json.loads(catalog_path.read_text(encoding="utf-8"))
        return EffectBundleCatalog.model_validate(raw)
    except json.JSONDecodeError as exc:
        raise EngineValidationError(f"Corrupted effect bundle catalog: {catalog_path.name}") from exc
    except EngineValidationError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise EngineValidationError(f"Invalid effect bundle catalog: {exc}") from exc


def load_effect_bundle_catalog(
    path: str | None = None,
    *,
    type_registry: EffectTypeRegistry | None = None,
) -> EffectBundleCatalog:
    """Load effect bundles and validate against the type registry."""

    catalog = _load_effect_bundle_catalog_raw(path)
    registry = type_registry or load_effect_type_registry()
    validate_bundle_catalog(catalog, registry)
    return catalog


def clear_modifier_catalog_caches() -> None:
    """Clear cached modifier catalogs (tests / alternate content roots)."""

    load_effect_type_registry.cache_clear()
    _load_effect_bundle_catalog_raw.cache_clear()


def _resolve_effects(
    instance: EffectInstance,
    bundles: EffectBundleCatalog,
) -> list[EffectSpec]:
    if instance.inline_effects is not None:
        return list(instance.inline_effects)
    assert instance.bundle_id is not None
    return list(bundles.get(instance.bundle_id).effects)


def aggregate(
    instances: Sequence[EffectInstance],
    context: ModifierContext,
    *,
    type_registry: EffectTypeRegistry | None = None,
    bundles: EffectBundleCatalog | None = None,
) -> ModifierSnapshot:
    """Aggregate active sources into an ephemeral modifier snapshot.

    Pure and deterministic for a given inputs set. Does not mutate state.
    """

    registry = type_registry or load_effect_type_registry()
    bundle_catalog = bundles or load_effect_bundle_catalog(type_registry=registry)

    if context.activity not in KNOWN_ACTIVITIES:
        raise EngineValidationError(f"Unknown modifier activity context: {context.activity!r}")

    numeric_acc: dict[tuple[str, str | None], float] = {}
    flag_acc: set[str] = set()
    contributions: list[ModifierContribution] = []

    for instance in instances:
        if instance.actor_id != context.actor_id:
            continue
        if instance.expires_world_day is not None and context.world_day >= instance.expires_world_day:
            continue

        for spec in _resolve_effects(instance, bundle_catalog):
            type_def = registry.get(spec.type)
            validate_effect_spec(spec, type_def)
            if context.activity not in spec.applies_to:
                continue

            bucket_category = spec.category

            if type_def.aggregation == "or":
                flag_id = str(spec.params["flag"]).strip()
                if instance.magnitude_scale <= 0:
                    continue
                flag_acc.add(flag_id)
                contributions.append(
                    ModifierContribution(
                        source_kind=instance.source_kind,
                        source_id=instance.source_id,
                        effect_type=type_def.id,
                        detail=flag_id,
                        raw=flag_id,
                        applied=True,
                        category=bucket_category,
                    )
                )
                continue

            raw_value = float(spec.params[type_def.param_key])
            scaled = _scaled_numeric(
                raw_value,
                aggregation=type_def.aggregation,
                magnitude_scale=instance.magnitude_scale,
            )
            key = (type_def.id, bucket_category)
            if key not in numeric_acc:
                numeric_acc[key] = float(type_def.identity)
            if type_def.aggregation == "sum":
                numeric_acc[key] += scaled
            else:
                numeric_acc[key] *= scaled
            contributions.append(
                ModifierContribution(
                    source_kind=instance.source_kind,
                    source_id=instance.source_id,
                    effect_type=type_def.id,
                    detail=type_def.param_key,
                    raw=raw_value,
                    applied=scaled,
                    category=bucket_category,
                )
            )

    numbers: dict[str, float] = {}
    categorized: dict[str, dict[str, float]] = {}
    for (type_id, cat), total in numeric_acc.items():
        type_def = registry.get(type_id)
        clamped = _clamp(total, type_def.cap_min, type_def.cap_max)
        if cat is None:
            numbers[type_id] = clamped
        else:
            categorized.setdefault(type_id, {})[cat] = clamped

    return ModifierSnapshot(
        numbers=numbers,
        categorized_numbers=categorized,
        flags=frozenset(flag_acc),
        contributions=tuple(contributions),
    )


__all__ = [
    "KNOWN_ACTIVITIES",
    "AggregationRule",
    "EffectBundle",
    "EffectBundleCatalog",
    "EffectInstance",
    "EffectSpec",
    "EffectTypeDefinition",
    "EffectTypeRegistry",
    "ModifierContext",
    "ModifierContribution",
    "ModifierSnapshot",
    "ModifierSourceKind",
    "ParamKey",
    "ValueType",
    "aggregate",
    "clear_modifier_catalog_caches",
    "consumer_number",
    "ignored_snapshot_effect_types",
    "load_effect_bundle_catalog",
    "load_effect_type_registry",
    "validate_bundle_against_registry",
    "validate_bundle_catalog",
    "validate_effect_spec",
]
