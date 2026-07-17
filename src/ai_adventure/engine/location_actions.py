"""Data-driven location action catalog (Phase 5c).

Locations list action ids they offer. The action catalog owns labels, duration,
reserved requirement/cost fields, and which event trigger fires after success.
Only actions marked ``implemented`` may be executed via LocationService.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from ai_adventure.engine.constants import EVENT_TYPE_LOCATION_ACTION
from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.locations import get_location, load_location_catalog
from ai_adventure.engine.time import advance_world_days, current_world_day

_WORLD_DIR = Path(__file__).resolve().parents[1] / "data" / "world"
_ACTION_CATALOG_PATH = _WORLD_DIR / "action_catalog.json"

ActionOutcomeType = Literal["success", "blocked"]


class ActionPresentation(BaseModel):
    """Presentation-only text for an action."""

    placeholder_summary: str = Field(min_length=1)


class LocationActionDefinition(BaseModel):
    """One global location action template."""

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    description: str = ""
    enabled: bool = True
    implemented: bool = False
    duration_days: int = Field(default=0, ge=0)
    requirements: dict[str, Any] = Field(default_factory=dict)
    required_realm: str | None = None
    required_technique_ids: list[str] = Field(default_factory=list)
    required_items: list[str] = Field(default_factory=list)
    required_reputation: dict[str, Any] = Field(default_factory=dict)
    cooldown_days: int = Field(default=0, ge=0)
    stamina_cost: int | None = Field(default=None, ge=0)
    resource_costs: dict[str, Any] = Field(default_factory=dict)
    event_weight_modifiers: dict[str, float] = Field(default_factory=dict)
    trigger_kind: str | None = None
    presentation: ActionPresentation

    @field_validator("id")
    @classmethod
    def _non_empty_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("action id must be non-empty")
        return cleaned


class LocationActionCatalog(BaseModel):
    """Merged action catalog."""

    schema_version: int = Field(ge=1)
    actions: list[LocationActionDefinition] = Field(min_length=1)

    @field_validator("actions")
    @classmethod
    def _unique_ids(cls, value: list[LocationActionDefinition]) -> list[LocationActionDefinition]:
        ids = [item.id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate action ids in catalog")
        return value

    @property
    def by_id(self) -> dict[str, LocationActionDefinition]:
        """Index actions by id."""

        return {item.id: item for item in self.actions}


@dataclass(frozen=True, slots=True)
class AvailableLocationAction:
    """UI/engine view of one action offered at the current location."""

    id: str
    label: str
    description: str
    duration_days: int
    implemented: bool
    available: bool
    blocked_reason: str | None = None


@dataclass(frozen=True, slots=True)
class LocationActionPlan:
    """Pure planned location action (no persistence)."""

    action_id: str
    location_id: str
    duration_days: int
    trigger_kind: str | None
    world_day_before: int
    world_day_after: int
    summary: str


@dataclass(frozen=True, slots=True)
class LocationActionResolution:
    """Result of planning a location action."""

    outcome_type: ActionOutcomeType
    plan: LocationActionPlan | None
    summary: str
    blocked_reason: str | None = None
    event_payload: dict[str, Any] | None = None


def clear_location_action_catalog_cache() -> None:
    """Drop cached action catalog (tests / hot reload)."""

    load_location_action_catalog.cache_clear()


@lru_cache(maxsize=1)
def load_location_action_catalog(path: str | None = None) -> LocationActionCatalog:
    """Load the global location action catalog."""

    catalog_path = Path(path) if path is not None else _ACTION_CATALOG_PATH
    try:
        raw = json.loads(catalog_path.read_text(encoding="utf-8"))
        return LocationActionCatalog.model_validate(raw)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise EngineValidationError(f"Invalid location action catalog: {exc}") from exc


def get_location_action(
    action_id: str,
    *,
    catalog: LocationActionCatalog | None = None,
) -> LocationActionDefinition:
    """Return an action definition or raise."""

    cat = catalog if catalog is not None else load_location_action_catalog()
    action = cat.by_id.get(action_id)
    if action is None:
        raise EngineValidationError(f"Unknown location action: {action_id}")
    return action


def known_location_action_ids(*, catalog: LocationActionCatalog | None = None) -> frozenset[str]:
    """All action ids defined in the catalog."""

    cat = catalog if catalog is not None else load_location_action_catalog()
    return frozenset(cat.by_id)


def list_available_location_actions(
    location_id: str,
    *,
    catalog: LocationActionCatalog | None = None,
) -> list[AvailableLocationAction]:
    """Return actions offered by a location (implemented and reserved)."""

    location = get_location(location_id)
    action_catalog = catalog if catalog is not None else load_location_action_catalog()
    offered: list[AvailableLocationAction] = []
    for action_id in location.actions:
        action = action_catalog.by_id.get(action_id)
        if action is None:
            continue
        if not action.enabled:
            offered.append(
                AvailableLocationAction(
                    id=action.id,
                    label=action.label,
                    description=action.description,
                    duration_days=action.duration_days,
                    implemented=action.implemented,
                    available=False,
                    blocked_reason="disabled",
                )
            )
            continue
        if not action.implemented:
            offered.append(
                AvailableLocationAction(
                    id=action.id,
                    label=action.label,
                    description=action.description,
                    duration_days=action.duration_days,
                    implemented=False,
                    available=False,
                    blocked_reason="not_implemented",
                )
            )
            continue
        offered.append(
            AvailableLocationAction(
                id=action.id,
                label=action.label,
                description=action.description,
                duration_days=action.duration_days,
                implemented=True,
                available=True,
                blocked_reason=None,
            )
        )
    return offered


def plan_location_action(
    *,
    location_id: str,
    action_id: str,
    world_day: int,
    catalog: LocationActionCatalog | None = None,
) -> LocationActionResolution:
    """Validate a location action without persistence."""

    current_world_day(world_day)
    location = get_location(location_id)
    action = get_location_action(action_id, catalog=catalog)

    if action_id not in location.actions:
        return LocationActionResolution(
            outcome_type="blocked",
            plan=None,
            summary=f"{action.label} is not available here.",
            blocked_reason="not_offered",
        )
    if not action.enabled:
        return LocationActionResolution(
            outcome_type="blocked",
            plan=None,
            summary=f"{action.label} is disabled.",
            blocked_reason="disabled",
        )
    if not action.implemented:
        return LocationActionResolution(
            outcome_type="blocked",
            plan=None,
            summary=f"{action.label} is not available yet.",
            blocked_reason="not_implemented",
        )

    # Reserved gates: fail closed if content authors fill them early.
    if action.requirements:
        return LocationActionResolution(
            outcome_type="blocked",
            plan=None,
            summary="Action requirements are not satisfied.",
            blocked_reason="requirements_unmet",
        )
    if action.required_realm is not None:
        return LocationActionResolution(
            outcome_type="blocked",
            plan=None,
            summary="Realm requirement is not satisfied.",
            blocked_reason="realm_gate",
        )
    if action.required_technique_ids or action.required_items or action.required_reputation:
        return LocationActionResolution(
            outcome_type="blocked",
            plan=None,
            summary="Action prerequisites are not satisfied.",
            blocked_reason="prerequisites_unmet",
        )
    if action.resource_costs or action.stamina_cost:
        return LocationActionResolution(
            outcome_type="blocked",
            plan=None,
            summary="Action cost cannot be paid yet.",
            blocked_reason="cost_unmet",
        )

    world_day_after = advance_world_days(world_day, action.duration_days)
    plan = LocationActionPlan(
        action_id=action.id,
        location_id=location_id,
        duration_days=action.duration_days,
        trigger_kind=action.trigger_kind,
        world_day_before=world_day,
        world_day_after=world_day_after,
        summary=action.presentation.placeholder_summary,
    )
    return LocationActionResolution(
        outcome_type="success",
        plan=plan,
        summary=action.presentation.placeholder_summary,
        event_payload={
            "event_type": EVENT_TYPE_LOCATION_ACTION,
            "action_id": action.id,
            "location_id": location_id,
            "duration_days": action.duration_days,
            "trigger_kind": action.trigger_kind,
        },
    )


def validate_location_actions_against_catalog(
    *,
    world_dir: str | Path | None = None,
    actions_path: str | Path | None = None,
) -> list[str]:
    """Return error messages if locations reference unknown action ids."""

    action_ids = known_location_action_ids(
        catalog=load_location_action_catalog(
            str(actions_path) if actions_path is not None else None
        )
    )
    catalog = load_location_catalog(str(world_dir) if world_dir is not None else None)
    errors: list[str] = []
    for location in catalog.locations:
        for action_id in location.actions:
            if action_id not in action_ids:
                errors.append(
                    f"Location '{location.id}' references unknown action '{action_id}'"
                )
    return errors
