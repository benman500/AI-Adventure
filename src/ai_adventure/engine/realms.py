"""Data-driven major realm and stage catalog.

Phase 1: Body Tempering and Qi Gathering are playable; later realms are
placeholders. Realm advancement is not enabled yet (see breakthroughs TODO).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from ai_adventure.engine.errors import EngineValidationError

_REALMS_PATH = Path(__file__).resolve().parents[1] / "data" / "cultivation" / "realms.json"

RealmStatus = Literal["playable", "placeholder"]


class StageDefinition(BaseModel):
    """One minor stage within a major realm (Early / Middle / Late / Peak)."""

    id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    order_index: int = Field(ge=1)


class RealmDefinition(BaseModel):
    """One major cultivation realm on the shared ladder."""

    id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    order_index: int = Field(ge=1)
    status: RealmStatus
    cosmology_layer: str = Field(min_length=1)
    stage_scheme_id: str = Field(min_length=1)
    base_qi_max: int = Field(gt=0)
    notes: str = ""


class RealmCatalog(BaseModel):
    """Full realm + stage catalog loaded from content data."""

    stage_scheme_id: str = Field(min_length=1)
    stages: list[StageDefinition] = Field(min_length=4)
    realms: list[RealmDefinition] = Field(min_length=1)

    @field_validator("stages")
    @classmethod
    def _unique_stage_ids(cls, value: list[StageDefinition]) -> list[StageDefinition]:
        ids = [item.id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate stage ids")
        return value

    @field_validator("realms")
    @classmethod
    def _unique_realm_ids(cls, value: list[RealmDefinition]) -> list[RealmDefinition]:
        ids = [item.id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate realm ids")
        return value


# Legacy stage id used by Milestone 3 saves before Phase 1 rename mid → middle.
STAGE_ID_ALIASES: dict[str, str] = {
    "mid": "middle",
}

# Legacy realm id from pre-Phase-1 docs (Qi Condensation → Qi Gathering).
REALM_ID_ALIASES: dict[str, str] = {
    "qi_condensation": "qi_gathering",
}


@lru_cache(maxsize=1)
def load_realm_catalog(path: str | None = None) -> RealmCatalog:
    """Load and validate the realm/stage catalog."""

    catalog_path = Path(path) if path else _REALMS_PATH
    if not catalog_path.is_file():
        raise EngineValidationError(f"Realm catalog missing: {catalog_path}")
    try:
        raw = json.loads(catalog_path.read_text(encoding="utf-8"))
        catalog = RealmCatalog.model_validate(raw)
    except json.JSONDecodeError as exc:
        raise EngineValidationError(f"Corrupted realm catalog: {catalog_path.name}") from exc
    except Exception as exc:  # noqa: BLE001
        raise EngineValidationError(f"Invalid realm catalog: {exc}") from exc
    return catalog


def clear_realm_catalog_cache() -> None:
    """Clear cached catalog (tests / alternate content roots)."""

    load_realm_catalog.cache_clear()


def list_realms(*, playable_only: bool = False, path: str | None = None) -> list[RealmDefinition]:
    """Return realms ordered by ladder position."""

    catalog = load_realm_catalog(path)
    realms = sorted(catalog.realms, key=lambda item: item.order_index)
    if playable_only:
        return [item for item in realms if item.status == "playable"]
    return realms


def get_realm(realm_id: str, path: str | None = None) -> RealmDefinition:
    """Return a realm by stable id."""

    resolved = normalize_realm_id(realm_id)
    for realm in load_realm_catalog(path).realms:
        if realm.id == resolved:
            return realm
    raise EngineValidationError(f"Unknown realm: {realm_id}")


def list_stages(path: str | None = None) -> list[StageDefinition]:
    """Return minor stages ordered by index."""

    catalog = load_realm_catalog(path)
    return sorted(catalog.stages, key=lambda item: item.order_index)


def get_stage(stage_id: str, path: str | None = None) -> StageDefinition:
    """Return a stage by stable id (resolves legacy aliases)."""

    resolved = normalize_stage_id(stage_id)
    for stage in load_realm_catalog(path).stages:
        if stage.id == resolved:
            return stage
    raise EngineValidationError(f"Unknown stage: {stage_id}")


def normalize_stage_id(stage_id: str) -> str:
    """Map legacy stage ids to the Phase 1 canonical set."""

    return STAGE_ID_ALIASES.get(stage_id, stage_id)


def normalize_realm_id(realm_id: str) -> str:
    """Map legacy realm ids (e.g. qi_condensation) to canonical Phase 1 ids."""

    return REALM_ID_ALIASES.get(realm_id, realm_id)


def is_playable_realm(realm_id: str, path: str | None = None) -> bool:
    """True when the realm is Phase-1 (or later) playable content."""

    return get_realm(normalize_realm_id(realm_id), path).status == "playable"


def next_stage_id(stage_id: str, path: str | None = None) -> str | None:
    """Return the next stage id within the same realm, or None at Peak."""

    stages = list_stages(path)
    current = normalize_stage_id(stage_id)
    ids = [item.id for item in stages]
    if current not in ids:
        raise EngineValidationError(f"Unknown stage: {stage_id}")
    index = ids.index(current)
    if index >= len(ids) - 1:
        return None
    return ids[index + 1]


def realm_display_name(realm_id: str, path: str | None = None) -> str:
    """Player-facing realm name."""

    return get_realm(normalize_realm_id(realm_id), path).display_name


def stage_display_name(stage_id: str, path: str | None = None) -> str:
    """Player-facing stage name."""

    return get_stage(stage_id, path).display_name


def realm_stage_display(realm_id: str, stage_id: str, path: str | None = None) -> str:
    """Combined realm + stage label."""

    return f"{realm_display_name(realm_id, path)} ({stage_display_name(stage_id, path)})"


# ---------------------------------------------------------------------------
# Future extension points
# ---------------------------------------------------------------------------

# TODO(Phase 5+): techniques — technique records with realm/stage gates.
# TODO(Phase 6): spiritual roots — affinity modifiers shared by players and NPCs.
# TODO(Phase 7): pills / consumables — temporary breakthrough modifiers.
# TODO(Phase 8+): tribulations — unique trials on major realm breakthroughs.
# TODO(Phase 10): environmental modifiers and AI-generated breakthrough scenes.
