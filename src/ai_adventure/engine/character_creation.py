"""Character creation: compose starting state from validated content."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai_adventure.engine.backgrounds import BackgroundDefinition, get_background
from ai_adventure.engine.constants import (
    EVENT_TYPE_CHARACTER_CREATED,
    MAX_CHARACTER_NAME_LENGTH,
    MIN_CHARACTER_NAME_LENGTH,
    STARTING_BODY,
    STARTING_CULTIVATION_PATH,
    STARTING_FOUNDATION_QUALITY,
    STARTING_QI,
    STARTING_REALM_ID,
    STARTING_SOUL,
    STARTING_STAGE_ID,
)
from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.identity import validate_identity_answers


@dataclass(frozen=True, slots=True)
class StartingPossession:
    """An inventory stack to persist at creation."""

    item_code: str
    display_name: str
    quantity: int


@dataclass(frozen=True, slots=True)
class CreatedCharacterState:
    """Authoritative starting character state produced by the engine."""

    character_name: str
    background_id: str
    background_display_name: str
    intro_flavor: str
    current_location_id: str
    current_location_name: str
    money_copper: int
    cultivation_path: str
    realm_id: str
    stage_id: str
    body: int
    qi: int
    soul: int
    foundation_quality: int
    identity_answers: dict[str, str]
    background_history: dict[str, Any]
    possessions: tuple[StartingPossession, ...]
    event_type: str = EVENT_TYPE_CHARACTER_CREATED
    event_payload: dict[str, Any] = field(default_factory=dict)


def normalize_character_name(name: str) -> str:
    """Trim and validate a display name."""

    cleaned = " ".join(name.split())
    if len(cleaned) < MIN_CHARACTER_NAME_LENGTH:
        raise EngineValidationError("Character name is required")
    if len(cleaned) > MAX_CHARACTER_NAME_LENGTH:
        raise EngineValidationError(
            f"Character name must be at most {MAX_CHARACTER_NAME_LENGTH} characters"
        )
    return cleaned


def create_character(
    *,
    character_name: str,
    background_id: str,
    identity_answers: dict[str, str],
    backgrounds_dir: str | None = None,
    personality_questions_path: str | None = None,
) -> CreatedCharacterState:
    """Validate inputs and compose starting state (no Boundless choice)."""

    name = normalize_character_name(character_name)
    background = get_background(background_id, backgrounds_dir=backgrounds_dir)
    _assert_background_not_corrupted(background)
    answers = validate_identity_answers(
        identity_answers,
        path=personality_questions_path,
    )

    possessions = tuple(
        StartingPossession(
            item_code=item.item_code,
            display_name=item.display_name,
            quantity=item.quantity,
        )
        for item in background.starting_possessions
    )

    history = background.history_payload()
    event_payload = {
        "character_name": name,
        "background_id": background.id,
        "background_display_name": background.display_name,
        "location_id": background.starting_location_id,
        "cultivation_path": STARTING_CULTIVATION_PATH,
    }

    return CreatedCharacterState(
        character_name=name,
        background_id=background.id,
        background_display_name=background.display_name,
        intro_flavor=background.intro_flavor,
        current_location_id=background.starting_location_id,
        current_location_name=background.starting_location_name,
        money_copper=background.starting_money_copper,
        cultivation_path=STARTING_CULTIVATION_PATH,
        realm_id=STARTING_REALM_ID,
        stage_id=STARTING_STAGE_ID,
        body=STARTING_BODY,
        qi=STARTING_QI,
        soul=STARTING_SOUL,
        foundation_quality=STARTING_FOUNDATION_QUALITY,
        identity_answers=answers,
        background_history=history,
        possessions=possessions,
        event_payload=event_payload,
    )


def _assert_background_not_corrupted(background: BackgroundDefinition) -> None:
    """Reject packages that would create illegal starting state."""

    if background.starting_money_copper < 0:
        raise EngineValidationError("Background starting money cannot be negative")
    if not background.starting_possessions:
        raise EngineValidationError("Background must include starting possessions")
    for item in background.starting_possessions:
        if item.quantity <= 0:
            raise EngineValidationError(
                f"Possession {item.item_code!r} has invalid quantity"
            )
