"""Data-driven location catalog and presence helpers (Phase 5a).

World content is organized as modular packs under ``data/world/packs/``.
Packs merge into one in-memory catalog with globally unique location ids.
Display names and mechanical metadata live in the catalog; saves store only
mutable presence / current location references.

Travel (5b) is a first-class LocationService action. Location actions (5c)
define what the player may do while present (explore, inspect, …) via an
action catalog + per-location offers. Technique site hooks remain Phase 6.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from ai_adventure.engine.constants import EVENT_TYPE_TRAVEL_RESOLVED
from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.time import advance_world_days, current_world_day

_WORLD_DIR = Path(__file__).resolve().parents[1] / "data" / "world"
_WORLD_MANIFEST_PATH = _WORLD_DIR / "world_manifest.json"
_PACKS_DIR = _WORLD_DIR / "packs"

LocationKind = Literal["region", "settlement", "site"]

# Reserved action ids for Phase 5c+; empty lists are valid in 5a.
KNOWN_LOCATION_ACTIONS: frozenset[str] = frozenset(
    {
        "cultivate",
        "explore",
        "inspect",
        "rest",
        "talk",
        "train",
        "leave",
        "travel",
        "study",
        "trade",
    }
)


class LocationPresentation(BaseModel):
    """Presentation-only metadata. Never affects mechanics."""

    music: str | None = None
    artwork: str | None = None
    ambience: str | None = None


class TravelEdgeDefinition(BaseModel):
    """Authored travel edge between two catalog locations.

    Phase 5b uses ``to``, ``days``, and ``requirements``. Remaining fields are
    reserved for future systems and must not be required to be populated.
    """

    to: str = Field(min_length=1)
    days: int = Field(default=1, ge=0)
    requirements: dict[str, Any] = Field(default_factory=dict)
    travel_method: str | None = None
    travel_danger: int | None = Field(default=None, ge=0)
    travel_restrictions: list[str] = Field(default_factory=list)
    travel_cost: dict[str, Any] = Field(default_factory=dict)
    visibility: Literal["public", "hidden", "secret"] = "public"
    hidden_route: bool = False
    unlock_requirements: dict[str, Any] = Field(default_factory=dict)


class LocationDefinition(BaseModel):
    """One authored location from a world content pack."""

    id: str = Field(min_length=1)
    kind: LocationKind
    display_name: str = Field(min_length=1)
    parent_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    sect_id: str | None = None
    travel: list[TravelEdgeDefinition] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    weather_tags: list[str] = Field(default_factory=list)
    spiritual_density: int | None = Field(default=None, ge=0)
    danger_rating: int | None = Field(default=None, ge=0)
    recommended_realm: str | None = None
    resources: list[str] = Field(default_factory=list)
    npc_spawn_tags: list[str] = Field(default_factory=list)
    event_weight_modifiers: dict[str, float] = Field(default_factory=dict)
    cultivation_tags: list[str] = Field(default_factory=list)
    environment_tags: list[str] = Field(default_factory=list)
    technique_tags: list[str] = Field(default_factory=list)
    technique_ids: list[str] = Field(default_factory=list)
    presentation: LocationPresentation = Field(default_factory=LocationPresentation)
    pack_id: str = Field(default="", min_length=0)

    @field_validator("actions")
    @classmethod
    def _known_actions(cls, value: list[str]) -> list[str]:
        unknown = sorted({item for item in value if item not in KNOWN_LOCATION_ACTIONS})
        if unknown:
            raise ValueError(f"unknown location actions: {unknown}")
        return value


class LocationFile(BaseModel):
    """One pack locations content file."""

    schema_version: int = Field(ge=1)
    locations: list[LocationDefinition] = Field(default_factory=list)


class WorldPackManifest(BaseModel):
    """Manifest for one modular world content pack."""

    pack_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    depends_on: list[str] = Field(default_factory=list)
    content_files: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _require_locations_key(self) -> WorldPackManifest:
        if "locations" not in self.content_files:
            raise ValueError("content_files must include 'locations'")
        return self


class WorldManifest(BaseModel):
    """Top-level ordered list of world packs to load."""

    schema_version: int = Field(ge=1)
    packs: list[str] = Field(min_length=1)


class LocationCatalog(BaseModel):
    """Merged location catalog across all enabled packs."""

    locations: list[LocationDefinition] = Field(default_factory=list)
    pack_ids: list[str] = Field(default_factory=list)

    @property
    def by_id(self) -> dict[str, LocationDefinition]:
        """Index locations by stable id."""

        return {item.id: item for item in self.locations}


@dataclass(frozen=True, slots=True)
class LocationValidationIssue:
    """One catalog validation finding."""

    severity: Literal["error", "warning"]
    code: str
    message: str
    pack_id: str | None = None
    location_id: str | None = None


@dataclass(frozen=True, slots=True)
class LocationCatalogValidationReport:
    """Result of validating the world location catalog."""

    errors: tuple[LocationValidationIssue, ...]
    warnings: tuple[LocationValidationIssue, ...]

    @property
    def ok(self) -> bool:
        """True when there are no errors."""

        return not self.errors


@dataclass(frozen=True, slots=True)
class PresenceUpsert:
    """Pure description of a presence row change (repositories apply it)."""

    location_id: str
    discovered_world_day: int
    first_visited_world_day: int
    last_visited_world_day: int
    visit_count: int
    is_new: bool


def clear_location_catalog_cache() -> None:
    """Drop cached catalog (tests / hot reload)."""

    load_location_catalog.cache_clear()


@lru_cache(maxsize=1)
def load_location_catalog(world_dir: str | None = None) -> LocationCatalog:
    """Load and validate the merged location catalog from world packs."""

    root = Path(world_dir) if world_dir is not None else _WORLD_DIR
    catalog, report = _load_location_catalog_unchecked(root)
    if not report.ok:
        messages = "; ".join(issue.message for issue in report.errors)
        raise EngineValidationError(f"Invalid location catalog: {messages}")
    return catalog


def validate_location_catalog(world_dir: str | Path | None = None) -> LocationCatalogValidationReport:
    """Validate packs and merged catalog without raising (devtools / startup)."""

    root = Path(world_dir) if world_dir is not None else _WORLD_DIR
    try:
        _, report = _load_location_catalog_unchecked(root)
        return report
    except (OSError, json.JSONDecodeError, ValueError, EngineValidationError) as exc:
        return LocationCatalogValidationReport(
            errors=(
                LocationValidationIssue(
                    severity="error",
                    code="load_failed",
                    message=str(exc),
                ),
            ),
            warnings=(),
        )


def assert_location_catalog_valid(world_dir: str | Path | None = None) -> None:
    """Raise if the location catalog fails validation."""

    report = validate_location_catalog(world_dir)
    if not report.ok:
        messages = "; ".join(issue.message for issue in report.errors)
        raise EngineValidationError(f"Invalid location catalog: {messages}")

    # Deferred import avoids circular dependency with location_actions.
    from ai_adventure.engine.location_actions import validate_location_actions_against_catalog

    action_errors = validate_location_actions_against_catalog(world_dir=world_dir)
    if action_errors:
        raise EngineValidationError(
            "Invalid location catalog actions: " + "; ".join(action_errors)
        )


def get_location(location_id: str, *, catalog: LocationCatalog | None = None) -> LocationDefinition:
    """Return a location definition or raise if unknown."""

    cat = catalog if catalog is not None else load_location_catalog()
    location = cat.by_id.get(location_id)
    if location is None:
        raise EngineValidationError(f"Unknown location_id: {location_id}")
    return location


def resolve_location_display_name(
    location_id: str,
    *,
    catalog: LocationCatalog | None = None,
) -> str:
    """Authoritative display name from the catalog."""

    return get_location(location_id, catalog=catalog).display_name


def require_known_location(location_id: str, *, catalog: LocationCatalog | None = None) -> str:
    """Validate ``location_id`` exists; return it unchanged."""

    get_location(location_id, catalog=catalog)
    return location_id


def compute_presence_upsert(
    *,
    location_id: str,
    world_day: int,
    existing_visit_count: int | None,
    existing_discovered_world_day: int | None,
    existing_first_visited_world_day: int | None,
    catalog: LocationCatalog | None = None,
) -> PresenceUpsert:
    """Compute presence fields for a visit without touching persistence."""

    if world_day < 1:
        raise EngineValidationError("world_day must be >= 1")
    require_known_location(location_id, catalog=catalog)

    if existing_visit_count is None:
        return PresenceUpsert(
            location_id=location_id,
            discovered_world_day=world_day,
            first_visited_world_day=world_day,
            last_visited_world_day=world_day,
            visit_count=1,
            is_new=True,
        )

    return PresenceUpsert(
        location_id=location_id,
        discovered_world_day=int(existing_discovered_world_day or world_day),
        first_visited_world_day=int(existing_first_visited_world_day or world_day),
        last_visited_world_day=world_day,
        visit_count=int(existing_visit_count) + 1,
        is_new=False,
    )


TravelMode = Literal["travel", "story"]
TravelOutcomeType = Literal["success", "blocked", "noop"]


@dataclass(frozen=True, slots=True)
class TravelPlan:
    """Pure planned location change (no persistence)."""

    from_location_id: str
    to_location_id: str
    to_display_name: str
    days: int
    mode: TravelMode
    edge: TravelEdgeDefinition | None
    fire_travel_events: bool
    world_day_before: int
    world_day_after: int


@dataclass(frozen=True, slots=True)
class TravelResolution:
    """Completed mechanical travel / relocate result."""

    outcome_type: TravelOutcomeType
    plan: TravelPlan | None
    summary: str
    blocked_reason: str | None = None
    event_payload: dict[str, Any] | None = None


def find_travel_edge(
    from_location_id: str,
    to_location_id: str,
    *,
    catalog: LocationCatalog | None = None,
) -> TravelEdgeDefinition | None:
    """Return the authored edge from ``from`` to ``to``, if any."""

    origin = get_location(from_location_id, catalog=catalog)
    for edge in origin.travel:
        if edge.to == to_location_id:
            return edge
    return None


def list_travel_destinations(
    from_location_id: str,
    *,
    catalog: LocationCatalog | None = None,
    include_hidden: bool = False,
) -> list[TravelEdgeDefinition]:
    """List outbound edges from a location (optionally including hidden routes)."""

    origin = get_location(from_location_id, catalog=catalog)
    edges: list[TravelEdgeDefinition] = []
    for edge in origin.travel:
        if edge.hidden_route or edge.visibility in {"hidden", "secret"}:
            if not include_hidden:
                continue
        edges.append(edge)
    return edges


def _edge_is_hidden(edge: TravelEdgeDefinition) -> bool:
    return bool(edge.hidden_route) or edge.visibility in {"hidden", "secret"}


def plan_travel(
    *,
    from_location_id: str,
    to_location_id: str,
    world_day: int,
    mode: TravelMode,
    days_override: int | None = None,
    catalog: LocationCatalog | None = None,
) -> TravelResolution:
    """Validate and plan a location change without touching persistence.

    ``mode="travel"`` requires a public (or unlocked) catalog edge and uses
    edge ``days`` unless ``days_override`` is provided for tests.

    ``mode="story"`` requires the same edge graph so story and free travel
    cannot diverge; ``days_override`` supplies authored story day costs.
    """

    current_world_day(world_day)
    require_known_location(from_location_id, catalog=catalog)
    require_known_location(to_location_id, catalog=catalog)

    if from_location_id == to_location_id:
        day = current_world_day(world_day)
        plan = TravelPlan(
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            to_display_name=resolve_location_display_name(to_location_id, catalog=catalog),
            days=0,
            mode=mode,
            edge=None,
            fire_travel_events=False,
            world_day_before=day,
            world_day_after=day,
        )
        return TravelResolution(
            outcome_type="noop",
            plan=plan,
            summary="Already at destination.",
        )

    edge = find_travel_edge(from_location_id, to_location_id, catalog=catalog)
    if edge is None:
        return TravelResolution(
            outcome_type="blocked",
            plan=None,
            summary="No travel route exists between these locations.",
            blocked_reason="no_edge",
        )

    if mode == "travel" and _edge_is_hidden(edge):
        # Unlock requirements reserved; hidden routes block free travel for now.
        return TravelResolution(
            outcome_type="blocked",
            plan=None,
            summary="That route is not available.",
            blocked_reason="hidden_route",
        )

    if edge.requirements:
        # Reserved: future flag/realm/item gates. Unknown keys fail closed.
        return TravelResolution(
            outcome_type="blocked",
            plan=None,
            summary="Travel requirements are not satisfied.",
            blocked_reason="requirements_unmet",
        )

    if edge.travel_restrictions:
        return TravelResolution(
            outcome_type="blocked",
            plan=None,
            summary="Travel is restricted on this route.",
            blocked_reason="restricted",
        )

    if edge.travel_cost:
        return TravelResolution(
            outcome_type="blocked",
            plan=None,
            summary="Travel cost cannot be paid yet.",
            blocked_reason="cost_unmet",
        )

    if mode == "travel":
        days = int(edge.days if days_override is None else days_override)
    else:
        days = int(0 if days_override is None else days_override)
    if days < 0:
        return TravelResolution(
            outcome_type="blocked",
            plan=None,
            summary="Travel cannot reverse the world clock.",
            blocked_reason="negative_days",
        )

    world_day_after = advance_world_days(world_day, days)
    fire_events = mode == "travel" or days > 0
    plan = TravelPlan(
        from_location_id=from_location_id,
        to_location_id=to_location_id,
        to_display_name=resolve_location_display_name(to_location_id, catalog=catalog),
        days=days,
        mode=mode,
        edge=edge,
        fire_travel_events=fire_events,
        world_day_before=world_day,
        world_day_after=world_day_after,
    )
    return TravelResolution(
        outcome_type="success",
        plan=plan,
        summary=(
            f"Traveled to {plan.to_display_name}."
            if days
            else f"Arrived at {plan.to_display_name}."
        ),
        event_payload={
            "from_location_id": from_location_id,
            "to_location_id": to_location_id,
            "days": days,
            "mode": mode,
            "event_type": EVENT_TYPE_TRAVEL_RESOLVED,
        },
    )


def plan_world_day_advance(*, world_day: int, days: int) -> int:
    """Pure WorldClock advance used by LocationService for time-only beats."""

    return advance_world_days(world_day, days)


def _load_location_catalog_unchecked(
    root: Path,
) -> tuple[LocationCatalog, LocationCatalogValidationReport]:
    errors: list[LocationValidationIssue] = []
    warnings: list[LocationValidationIssue] = []

    manifest_path = root / "world_manifest.json"
    if not manifest_path.is_file():
        errors.append(
            LocationValidationIssue(
                severity="error",
                code="missing_world_manifest",
                message=f"Missing world manifest: {manifest_path}",
            )
        )
        return LocationCatalog(), LocationCatalogValidationReport(tuple(errors), tuple(warnings))

    try:
        world_manifest = WorldManifest.model_validate(json.loads(manifest_path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, ValueError) as exc:
        errors.append(
            LocationValidationIssue(
                severity="error",
                code="invalid_world_manifest",
                message=f"Invalid world manifest: {exc}",
            )
        )
        return LocationCatalog(), LocationCatalogValidationReport(tuple(errors), tuple(warnings))

    packs_dir = root / "packs"
    loaded_pack_ids: list[str] = []
    pack_manifests: dict[str, WorldPackManifest] = {}
    locations: list[LocationDefinition] = []
    seen_ids: dict[str, str] = {}

    for pack_id in world_manifest.packs:
        if pack_id in pack_manifests:
            errors.append(
                LocationValidationIssue(
                    severity="error",
                    code="duplicate_pack",
                    message=f"Duplicate pack id in world manifest: {pack_id}",
                    pack_id=pack_id,
                )
            )
            continue

        pack_dir = packs_dir / pack_id
        pack_manifest_path = pack_dir / "manifest.json"
        if not pack_manifest_path.is_file():
            errors.append(
                LocationValidationIssue(
                    severity="error",
                    code="missing_pack_manifest",
                    message=f"Missing pack manifest: {pack_manifest_path}",
                    pack_id=pack_id,
                )
            )
            continue

        try:
            pack_manifest = WorldPackManifest.model_validate(
                json.loads(pack_manifest_path.read_text(encoding="utf-8"))
            )
        except (json.JSONDecodeError, ValueError) as exc:
            errors.append(
                LocationValidationIssue(
                    severity="error",
                    code="invalid_pack_manifest",
                    message=f"Invalid pack manifest for {pack_id}: {exc}",
                    pack_id=pack_id,
                )
            )
            continue

        if pack_manifest.pack_id != pack_id:
            errors.append(
                LocationValidationIssue(
                    severity="error",
                    code="pack_id_mismatch",
                    message=(
                        f"Pack directory '{pack_id}' does not match "
                        f"manifest pack_id '{pack_manifest.pack_id}'"
                    ),
                    pack_id=pack_id,
                )
            )
            continue

        for dep in pack_manifest.depends_on:
            if dep not in world_manifest.packs:
                errors.append(
                    LocationValidationIssue(
                        severity="error",
                        code="missing_dependency",
                        message=f"Pack '{pack_id}' depends on unknown pack '{dep}'",
                        pack_id=pack_id,
                    )
                )
            elif world_manifest.packs.index(dep) > world_manifest.packs.index(pack_id):
                errors.append(
                    LocationValidationIssue(
                        severity="error",
                        code="dependency_order",
                        message=(
                            f"Pack '{pack_id}' depends on '{dep}' but appears "
                            f"before it in world_manifest.packs"
                        ),
                        pack_id=pack_id,
                    )
                )

        pack_manifests[pack_id] = pack_manifest
        locations_rel = pack_manifest.content_files["locations"]
        locations_path = pack_dir / locations_rel
        if not locations_path.is_file():
            errors.append(
                LocationValidationIssue(
                    severity="error",
                    code="missing_locations_file",
                    message=f"Missing locations file: {locations_path}",
                    pack_id=pack_id,
                )
            )
            continue

        try:
            location_file = LocationFile.model_validate(
                json.loads(locations_path.read_text(encoding="utf-8"))
            )
        except (json.JSONDecodeError, ValueError) as exc:
            errors.append(
                LocationValidationIssue(
                    severity="error",
                    code="invalid_locations_file",
                    message=f"Invalid locations file for {pack_id}: {exc}",
                    pack_id=pack_id,
                )
            )
            continue

        for reserved_key, rel_path in pack_manifest.content_files.items():
            if reserved_key == "locations":
                continue
            if not (pack_dir / rel_path).is_file():
                warnings.append(
                    LocationValidationIssue(
                        severity="warning",
                        code="optional_content_missing",
                        message=(
                            f"Pack '{pack_id}' declares content_files['{reserved_key}']="
                            f"'{rel_path}' but file is missing (ok until that system ships)"
                        ),
                        pack_id=pack_id,
                    )
                )

        for raw in location_file.locations:
            location = raw.model_copy(update={"pack_id": pack_id})
            if location.id in seen_ids:
                errors.append(
                    LocationValidationIssue(
                        severity="error",
                        code="duplicate_location_id",
                        message=(
                            f"Duplicate location id '{location.id}' in packs "
                            f"'{seen_ids[location.id]}' and '{pack_id}'"
                        ),
                        pack_id=pack_id,
                        location_id=location.id,
                    )
                )
                continue
            seen_ids[location.id] = pack_id
            locations.append(location)

        loaded_pack_ids.append(pack_id)

    by_id = {item.id: item for item in locations}
    for location in locations:
        if location.parent_id is None:
            continue
        if location.parent_id not in by_id:
            errors.append(
                LocationValidationIssue(
                    severity="error",
                    code="missing_parent",
                    message=(
                        f"Location '{location.id}' parent_id "
                        f"'{location.parent_id}' is not in the catalog"
                    ),
                    pack_id=location.pack_id or None,
                    location_id=location.id,
                )
            )
        for edge in location.travel:
            if edge.to not in by_id:
                errors.append(
                    LocationValidationIssue(
                        severity="error",
                        code="invalid_travel_target",
                        message=(
                            f"Location '{location.id}' travel edge targets "
                            f"unknown id '{edge.to}'"
                        ),
                        pack_id=location.pack_id or None,
                        location_id=location.id,
                    )
                )

    catalog = LocationCatalog(locations=locations, pack_ids=loaded_pack_ids)
    return catalog, LocationCatalogValidationReport(tuple(errors), tuple(warnings))
