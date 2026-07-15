"""Data-driven background definitions (pre-game life history seeds)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from ai_adventure.engine.errors import EngineValidationError

_BACKGROUNDS_DIR = Path(__file__).resolve().parents[1] / "data" / "backgrounds"


class SeedPossession(BaseModel):
    """A starting item stack defined in background content."""

    item_code: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    quantity: int = Field(gt=0)


class ReputationSeed(BaseModel):
    """Local reputation seed for later social simulation."""

    scope_id: str = Field(min_length=1)
    scope_label: str = Field(min_length=1)
    standing: str = Field(min_length=1)
    notes: str = ""


class RelationshipSeed(BaseModel):
    """Relationship seed for later NPC/relationship systems."""

    seed_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    bond: str = Field(min_length=1)
    notes: str = ""


class ContactSeed(BaseModel):
    """Known contact seed (not a live NPC in Milestone 2)."""

    contact_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    role: str = Field(min_length=1)
    notes: str = ""


class OpportunitySeed(BaseModel):
    """Opportunity seed for later quests/introductions."""

    opportunity_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    notes: str = ""


class BackgroundHistory(BaseModel):
    """Structured pre-game life history."""

    family_or_household: str = Field(min_length=1)
    hometown: str = Field(min_length=1)
    upbringing: str = Field(min_length=1)
    education: str = Field(min_length=1)
    former_occupation: str = Field(min_length=1)
    memories: list[str] = Field(min_length=1)
    existing_obligations: list[str] = Field(default_factory=list)
    favors: list[str] = Field(default_factory=list)


class BackgroundDefinition(BaseModel):
    """One upbringing background loaded from content data."""

    id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    intro_flavor: str = Field(min_length=1)
    starting_location_id: str = Field(min_length=1)
    starting_location_name: str = Field(min_length=1)
    starting_money_copper: int = Field(ge=0)
    history: BackgroundHistory
    reputation_seeds: list[ReputationSeed] = Field(default_factory=list)
    relationship_seeds: list[RelationshipSeed] = Field(default_factory=list)
    known_contacts: list[ContactSeed] = Field(default_factory=list)
    opportunities: list[OpportunitySeed] = Field(default_factory=list)
    starting_knowledge: list[str] = Field(min_length=1)
    starting_possessions: list[SeedPossession] = Field(min_length=1)

    @field_validator("starting_knowledge")
    @classmethod
    def _knowledge_non_empty_strings(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("starting_knowledge entries must be non-empty")
        return value

    def history_payload(self) -> dict[str, Any]:
        """Return the full structured history seed for persistence."""

        return {
            "background_id": self.id,
            "display_name": self.display_name,
            "history": self.history.model_dump(),
            "reputation_seeds": [item.model_dump() for item in self.reputation_seeds],
            "relationship_seeds": [item.model_dump() for item in self.relationship_seeds],
            "known_contacts": [item.model_dump() for item in self.known_contacts],
            "opportunities": [item.model_dump() for item in self.opportunities],
            "starting_knowledge": list(self.starting_knowledge),
        }


def _load_background_file(path: Path) -> BackgroundDefinition:
    """Parse and validate a single background JSON file."""

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EngineValidationError(f"Corrupted background data file: {path.name}") from exc
    try:
        definition = BackgroundDefinition.model_validate(raw)
    except Exception as exc:  # noqa: BLE001 — surface as engine validation
        raise EngineValidationError(f"Invalid background data in {path.name}: {exc}") from exc
    if definition.id != path.stem:
        raise EngineValidationError(
            f"Background id {definition.id!r} must match filename stem {path.stem!r}"
        )
    return definition


@lru_cache(maxsize=1)
def load_background_registry(
    backgrounds_dir: str | None = None,
) -> dict[str, BackgroundDefinition]:
    """Load all background JSON files from the content directory.

    Adding a new selectable background requires only a new valid JSON file—no
    engine code changes.
    """

    directory = Path(backgrounds_dir) if backgrounds_dir else _BACKGROUNDS_DIR
    if not directory.is_dir():
        raise EngineValidationError(f"Backgrounds directory missing: {directory}")

    registry: dict[str, BackgroundDefinition] = {}
    for path in sorted(directory.glob("*.json")):
        definition = _load_background_file(path)
        if definition.id in registry:
            raise EngineValidationError(f"Duplicate background id: {definition.id}")
        registry[definition.id] = definition
    if not registry:
        raise EngineValidationError("No background data files found")
    return registry


def clear_background_registry_cache() -> None:
    """Clear the cached registry (tests / alternate content roots)."""

    load_background_registry.cache_clear()


def list_backgrounds(
    backgrounds_dir: str | None = None,
) -> list[BackgroundDefinition]:
    """Return selectable backgrounds sorted by display name."""

    registry = load_background_registry(backgrounds_dir)
    return sorted(registry.values(), key=lambda item: item.display_name.lower())


def get_background(
    background_id: str,
    backgrounds_dir: str | None = None,
) -> BackgroundDefinition:
    """Return a background by id or raise validation error."""

    registry = load_background_registry(backgrounds_dir)
    try:
        return registry[background_id]
    except KeyError as exc:
        raise EngineValidationError(f"Unknown background: {background_id}") from exc
