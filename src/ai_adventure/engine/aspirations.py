"""Aspiration catalog + read-only eligibility (Phase 11a).

Aspirations never mutate world state. They evaluate durable facts written by
other systems (sects, NPCs, techniques, story flags, presence, cultivation).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.npcs import get_npc, load_npc_catalog
from ai_adventure.engine.realms import get_realm, load_realm_catalog
from ai_adventure.engine.sects import get_sect, load_sect_catalog
from ai_adventure.engine.techniques import get_technique, load_technique_catalog

AspirationKind = Literal["primary", "optional"]

_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "aspirations"
_CATALOG_PATH = _DATA_DIR / "aspirations.json"


class NpcRelationshipRequirement(BaseModel):
    """Minimum relationship score with one authored NPC."""

    npc_id: str = Field(min_length=1)
    min: int = Field(ge=-100, le=100)


class AspirationRequirementSet(BaseModel):
    """Allowlisted fact gates for availability or a single facet."""

    flags_all: list[str] = Field(default_factory=list)
    flags_none: list[str] = Field(default_factory=list)
    path_status_any: list[str] = Field(default_factory=list)
    min_sect_standing: int | None = Field(default=None, ge=-100, le=100)
    required_sect_id: str | None = None
    min_npc_relationship: NpcRelationshipRequirement | None = None
    known_technique_ids_any: list[str] = Field(default_factory=list)
    known_technique_ids_all: list[str] = Field(default_factory=list)
    min_foundation_stability: int | None = Field(default=None, ge=0, le=100)
    min_realm_order: int | None = Field(default=None, ge=1)
    discovered_location_ids_any: list[str] = Field(default_factory=list)

    @field_validator(
        "flags_all",
        "flags_none",
        "path_status_any",
        "known_technique_ids_any",
        "known_technique_ids_all",
        "discovered_location_ids_any",
    )
    @classmethod
    def _strip_nonempty(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("duplicate entries in requirement list")
        return cleaned


class AspirationFacetDefinition(BaseModel):
    """One named progress gap on an aspiration."""

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    description: str = Field(min_length=1)
    hint: str = Field(min_length=1)
    requirements: AspirationRequirementSet = Field(default_factory=AspirationRequirementSet)


class AspirationDefinition(BaseModel):
    """One authored aspiration (north star)."""

    id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    fantasy: str = Field(min_length=1)
    kind: AspirationKind
    sort_order: int = Field(ge=0)
    possible_paths: list[str] = Field(default_factory=list)
    available_when: AspirationRequirementSet = Field(default_factory=AspirationRequirementSet)
    requires_aspiration_ids: list[str] = Field(default_factory=list)
    facets: list[AspirationFacetDefinition] = Field(min_length=1)

    @field_validator("requires_aspiration_ids")
    @classmethod
    def _unique_prereqs(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("duplicate requires_aspiration_ids")
        return cleaned

    @model_validator(mode="after")
    def _unique_facet_ids(self) -> AspirationDefinition:
        ids = [facet.id for facet in self.facets]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate facet ids on aspiration {self.id!r}")
        return self


class AspirationCatalogFile(BaseModel):
    """On-disk aspiration catalog."""

    schema_version: int = Field(ge=1)
    aspirations: list[AspirationDefinition] = Field(default_factory=list)


class AspirationCatalog(BaseModel):
    """Validated in-memory aspiration catalog."""

    aspirations: list[AspirationDefinition] = Field(default_factory=list)

    @property
    def by_id(self) -> dict[str, AspirationDefinition]:
        """Index by stable aspiration id."""

        return {item.id: item for item in self.aspirations}


@dataclass(frozen=True, slots=True)
class AspirationFactSnapshot:
    """Durable facts aspirations may read. Never written by this module."""

    path_status: str
    story_flags: dict[str, bool] = field(default_factory=dict)
    sect_id: str | None = None
    sect_standing: int = 0
    npc_relationships: dict[str, int] = field(default_factory=dict)
    known_technique_ids: frozenset[str] = field(default_factory=frozenset)
    foundation_stability: int = 0
    realm_order: int = 1
    discovered_location_ids: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True, slots=True)
class FacetEvaluation:
    """Result of evaluating one facet against facts."""

    facet_id: str
    label: str
    description: str
    hint: str
    met: bool
    unmet_reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AspirationEvaluation:
    """Result of evaluating one aspiration against facts."""

    aspiration_id: str
    display_name: str
    summary: str
    fantasy: str
    kind: AspirationKind
    sort_order: int
    available: bool
    prerequisites_met: bool
    fulfilled: bool
    facets: tuple[FacetEvaluation, ...]
    possible_paths: tuple[str, ...] = ()

    @property
    def gaps(self) -> tuple[FacetEvaluation, ...]:
        """Unmet facets only."""

        return tuple(facet for facet in self.facets if not facet.met)

    @property
    def progress_met(self) -> int:
        """Count of satisfied facets."""

        return sum(1 for facet in self.facets if facet.met)

    @property
    def progress_total(self) -> int:
        """Total facet count."""

        return len(self.facets)


def clear_aspiration_catalog_cache() -> None:
    """Drop cached aspiration catalog (tests / hot reload)."""

    load_aspiration_catalog.cache_clear()


@lru_cache(maxsize=1)
def load_aspiration_catalog(path: str | None = None) -> AspirationCatalog:
    """Load and validate the aspiration catalog from disk."""

    catalog_path = Path(path) if path else _CATALOG_PATH
    raw = AspirationCatalogFile.model_validate_json(catalog_path.read_text(encoding="utf-8"))
    catalog = AspirationCatalog(aspirations=list(raw.aspirations))
    validate_aspiration_catalog(catalog)
    return catalog


def list_aspirations(path: str | None = None) -> list[AspirationDefinition]:
    """Return all aspirations in catalog order."""

    catalog = load_aspiration_catalog(path)
    return sorted(catalog.aspirations, key=lambda item: (item.sort_order, item.id))


def get_aspiration(aspiration_id: str, path: str | None = None) -> AspirationDefinition:
    """Return one aspiration or raise."""

    catalog = load_aspiration_catalog(path)
    aspiration = catalog.by_id.get(aspiration_id)
    if aspiration is None:
        raise EngineValidationError(f"Unknown aspiration_id: {aspiration_id!r}")
    return aspiration


def validate_aspiration_catalog(catalog: AspirationCatalog | None = None) -> None:
    """Fail closed on duplicate ids, bad refs, and unknown cross-catalog ids."""

    cat = catalog if catalog is not None else load_aspiration_catalog()
    ids = [item.id for item in cat.aspirations]
    if len(ids) != len(set(ids)):
        raise EngineValidationError("duplicate aspiration ids in catalog")

    by_id = cat.by_id
    load_npc_catalog()
    load_technique_catalog()
    load_sect_catalog()
    load_realm_catalog()

    for aspiration in cat.aspirations:
        for prereq in aspiration.requires_aspiration_ids:
            if prereq not in by_id:
                raise EngineValidationError(
                    f"aspiration {aspiration.id!r} requires unknown {prereq!r}"
                )
            if prereq == aspiration.id:
                raise EngineValidationError(
                    f"aspiration {aspiration.id!r} cannot require itself"
                )
        _validate_requirement_refs(aspiration.available_when, owner=aspiration.id)
        for facet in aspiration.facets:
            _validate_requirement_refs(
                facet.requirements,
                owner=f"{aspiration.id}.{facet.id}",
            )


def assert_aspiration_catalog_valid() -> None:
    """Startup / test helper."""

    validate_aspiration_catalog()


def _validate_requirement_refs(reqs: AspirationRequirementSet, *, owner: str) -> None:
    if reqs.required_sect_id:
        get_sect(reqs.required_sect_id)
    if reqs.min_npc_relationship is not None:
        get_npc(reqs.min_npc_relationship.npc_id)
    for technique_id in (*reqs.known_technique_ids_any, *reqs.known_technique_ids_all):
        get_technique(technique_id)
    if reqs.min_realm_order is not None:
        # Ensure realm catalog loads; order bounds checked at evaluate time.
        load_realm_catalog()
    _ = owner


def requirements_met(
    reqs: AspirationRequirementSet,
    facts: AspirationFactSnapshot,
) -> tuple[bool, tuple[str, ...]]:
    """Return whether ``reqs`` are satisfied and human-readable unmet reasons."""

    reasons: list[str] = []

    for flag in reqs.flags_all:
        if not facts.story_flags.get(flag, False):
            reasons.append(f"missing flag {flag}")
    for flag in reqs.flags_none:
        if facts.story_flags.get(flag, False):
            reasons.append(f"blocking flag {flag}")

    if reqs.path_status_any and facts.path_status not in reqs.path_status_any:
        reasons.append("path status not eligible")

    if reqs.required_sect_id is not None and facts.sect_id != reqs.required_sect_id:
        reasons.append("not a member of the required sect")

    if reqs.min_sect_standing is not None:
        if facts.sect_standing < reqs.min_sect_standing:
            reasons.append(
                f"sect standing {facts.sect_standing} < {reqs.min_sect_standing}"
            )

    if reqs.min_npc_relationship is not None:
        npc_id = reqs.min_npc_relationship.npc_id
        score = facts.npc_relationships.get(npc_id, 0)
        if score < reqs.min_npc_relationship.min:
            reasons.append(
                f"relationship with {npc_id} is {score} < {reqs.min_npc_relationship.min}"
            )

    if reqs.known_technique_ids_any:
        if not any(tid in facts.known_technique_ids for tid in reqs.known_technique_ids_any):
            reasons.append("missing required technique (any)")

    if reqs.known_technique_ids_all:
        missing = [
            tid for tid in reqs.known_technique_ids_all if tid not in facts.known_technique_ids
        ]
        if missing:
            reasons.append(f"missing techniques: {', '.join(missing)}")

    if reqs.min_foundation_stability is not None:
        if facts.foundation_stability < reqs.min_foundation_stability:
            reasons.append("foundation stability too low")

    if reqs.min_realm_order is not None:
        if facts.realm_order < reqs.min_realm_order:
            reasons.append("realm too low")

    if reqs.discovered_location_ids_any:
        if not any(
            loc in facts.discovered_location_ids for loc in reqs.discovered_location_ids_any
        ):
            reasons.append("required location not discovered")

    return (not reasons, tuple(reasons))


def evaluate_facet(
    facet: AspirationFacetDefinition,
    facts: AspirationFactSnapshot,
) -> FacetEvaluation:
    """Evaluate one facet."""

    met, reasons = requirements_met(facet.requirements, facts)
    return FacetEvaluation(
        facet_id=facet.id,
        label=facet.label,
        description=facet.description,
        hint=facet.hint,
        met=met,
        unmet_reasons=reasons,
    )


def is_aspiration_fulfilled(
    aspiration: AspirationDefinition,
    facts: AspirationFactSnapshot,
) -> bool:
    """True when every facet is satisfied."""

    return all(evaluate_facet(facet, facts).met for facet in aspiration.facets)


def evaluate_aspiration(
    aspiration: AspirationDefinition,
    facts: AspirationFactSnapshot,
    *,
    catalog: AspirationCatalog | None = None,
) -> AspirationEvaluation:
    """Evaluate availability, prerequisites, facets, and fulfillment."""

    cat = catalog if catalog is not None else load_aspiration_catalog()
    available, _ = requirements_met(aspiration.available_when, facts)

    prereqs_ok = True
    for prereq_id in aspiration.requires_aspiration_ids:
        prereq = cat.by_id[prereq_id]
        if not is_aspiration_fulfilled(prereq, facts):
            prereqs_ok = False
            break

    facets = tuple(evaluate_facet(facet, facts) for facet in aspiration.facets)
    fulfilled = bool(facets) and all(facet.met for facet in facets)

    return AspirationEvaluation(
        aspiration_id=aspiration.id,
        display_name=aspiration.display_name,
        summary=aspiration.summary,
        fantasy=aspiration.fantasy,
        kind=aspiration.kind,
        sort_order=aspiration.sort_order,
        available=available,
        prerequisites_met=prereqs_ok,
        fulfilled=fulfilled,
        facets=facets,
        possible_paths=tuple(aspiration.possible_paths),
    )


def evaluate_all_aspirations(
    facts: AspirationFactSnapshot,
    *,
    path: str | None = None,
) -> list[AspirationEvaluation]:
    """Evaluate every catalog aspiration against ``facts``."""

    catalog = load_aspiration_catalog(path)
    return [
        evaluate_aspiration(item, facts, catalog=catalog)
        for item in list_aspirations(path)
    ]


def select_primary_aspiration(
    evaluations: list[AspirationEvaluation],
) -> AspirationEvaluation | None:
    """First available primary with prerequisites met that is not yet fulfilled."""

    primaries = sorted(
        (item for item in evaluations if item.kind == "primary"),
        key=lambda item: (item.sort_order, item.aspiration_id),
    )
    for item in primaries:
        if item.available and item.prerequisites_met and not item.fulfilled:
            return item
    return None


def select_next_primary_preview(
    evaluations: list[AspirationEvaluation],
    *,
    current: AspirationEvaluation | None,
) -> AspirationEvaluation | None:
    """Next primary after ``current`` once current would be fulfilled (preview)."""

    if current is None:
        return None
    primaries = sorted(
        (item for item in evaluations if item.kind == "primary"),
        key=lambda item: (item.sort_order, item.aspiration_id),
    )
    found_current = False
    for item in primaries:
        if item.aspiration_id == current.aspiration_id:
            found_current = True
            continue
        if not found_current:
            continue
        if item.available:
            return item
    return None


def evaluation_to_card(evaluation: AspirationEvaluation) -> dict[str, Any]:
    """Presentation dict for play UI / tests."""

    return {
        "id": evaluation.aspiration_id,
        "display_name": evaluation.display_name,
        "summary": evaluation.summary,
        "fantasy": evaluation.fantasy,
        "kind": evaluation.kind,
        "status": "fulfilled" if evaluation.fulfilled else "in_progress",
        "progress_met": evaluation.progress_met,
        "progress_total": evaluation.progress_total,
        "possible_paths": list(evaluation.possible_paths),
        "gaps": [
            {
                "id": gap.facet_id,
                "label": gap.label,
                "description": gap.description,
                "hint": gap.hint,
                "met": False,
            }
            for gap in evaluation.gaps
        ],
        "facets": [
            {
                "id": facet.facet_id,
                "label": facet.label,
                "description": facet.description,
                "hint": facet.hint,
                "met": facet.met,
            }
            for facet in evaluation.facets
        ],
    }


def realm_order_for_id(realm_id: str) -> int:
    """Helper for assembling fact snapshots."""

    return int(get_realm(realm_id).order_index)


__all__ = [
    "AspirationCatalog",
    "AspirationDefinition",
    "AspirationEvaluation",
    "AspirationFactSnapshot",
    "AspirationFacetDefinition",
    "AspirationRequirementSet",
    "FacetEvaluation",
    "NpcRelationshipRequirement",
    "assert_aspiration_catalog_valid",
    "clear_aspiration_catalog_cache",
    "evaluate_all_aspirations",
    "evaluate_aspiration",
    "evaluation_to_card",
    "get_aspiration",
    "is_aspiration_fulfilled",
    "list_aspirations",
    "load_aspiration_catalog",
    "realm_order_for_id",
    "requirements_met",
    "select_next_primary_preview",
    "select_primary_aspiration",
    "validate_aspiration_catalog",
]
