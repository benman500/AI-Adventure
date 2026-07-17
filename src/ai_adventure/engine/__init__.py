"""Game engine: authoritative rules and structured outcomes (no HTTP, no AI)."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from ai_adventure.engine.backgrounds import (
    BackgroundDefinition,
    clear_background_registry_cache,
    get_background,
    list_backgrounds,
    load_background_registry,
)
from ai_adventure.engine.character_creation import (
    CreatedCharacterState,
    create_character,
)
from ai_adventure.engine.cultivation import (
    CultivationResult,
    CultivationState,
    apply_cultivation_method,
    attempt_breakthrough,
    attempt_realm_breakthrough,
    commit_path_choice,
    cultivation_view,
)
from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.identity import (
    PersonalityQuestion,
    clear_personality_questions_cache,
    list_personality_questions,
    validate_identity_answers,
)
from ai_adventure.engine.realms import (
    RealmDefinition,
    StageDefinition,
    clear_realm_catalog_cache,
    get_realm,
    get_stage,
    list_realms,
    list_stages,
    load_realm_catalog,
)
from ai_adventure.engine.story import (
    SceneView,
    StoryContext,
    StoryFlags,
    StoryTransitionResult,
    apply_on_enter,
    apply_story_action,
    build_scene_view,
    clear_story_cache,
    entry_node_for_background,
    flags_to_json,
    get_story_node,
    load_story_registry,
    parse_flags,
)


class OutcomeKind(StrEnum):
    """Kinds of completed engine outcomes (narrator input only)."""

    SYSTEM = "system"
    STATUS = "status"
    CHARACTER_CREATED = "character_created"


@dataclass(frozen=True, slots=True)
class EngineOutcome:
    """A completed mechanical result. Narrators may describe this; they must not invent one."""

    kind: OutcomeKind
    summary: str
    facts: dict[str, Any] = field(default_factory=dict)


class GameEngine:
    """Authoritative game rules host.

    Cultivation, combat, economy, and time systems plug in here later.
    Milestone 2 adds character creation composition and validation only.
    """

    def ping(self) -> EngineOutcome:
        """Return a deterministic status outcome proving the engine layer is active."""

        return EngineOutcome(
            kind=OutcomeKind.STATUS,
            summary="Engine ready.",
            facts={"authoritative": True, "ai_decides_mechanics": False},
        )

    def list_selectable_backgrounds(
        self,
        backgrounds_dir: str | None = None,
    ) -> list[BackgroundDefinition]:
        """Return data-driven backgrounds available for new games."""

        return list_backgrounds(backgrounds_dir)

    def list_personality_questions(
        self,
        path: str | None = None,
    ) -> list[PersonalityQuestion]:
        """Return universal personality questions (answers stored raw later)."""

        return list_personality_questions(path)

    def create_character(
        self,
        *,
        character_name: str,
        background_id: str,
        identity_answers: dict[str, str],
        backgrounds_dir: str | None = None,
        personality_questions_path: str | None = None,
    ) -> tuple[CreatedCharacterState, EngineOutcome]:
        """Validate and compose a new character; Boundless path is never offered."""

        state = create_character(
            character_name=character_name,
            background_id=background_id,
            identity_answers=identity_answers,
            backgrounds_dir=backgrounds_dir,
            personality_questions_path=personality_questions_path,
        )
        if state.cultivation_path != "ordinary":
            raise EngineValidationError("New characters must start on the ordinary path")
        outcome = EngineOutcome(
            kind=OutcomeKind.CHARACTER_CREATED,
            summary=f"{state.character_name} begins their journey.",
            facts={
                "character_name": state.character_name,
                "background_id": state.background_id,
                "cultivation_path": state.cultivation_path,
                "boundless_offered": False,
            },
        )
        return state, outcome


__all__ = [
    "BackgroundDefinition",
    "CreatedCharacterState",
    "CultivationResult",
    "CultivationState",
    "EngineOutcome",
    "EngineValidationError",
    "GameEngine",
    "OutcomeKind",
    "PersonalityQuestion",
    "RealmDefinition",
    "SceneView",
    "StageDefinition",
    "StoryContext",
    "StoryFlags",
    "StoryTransitionResult",
    "apply_cultivation_method",
    "apply_on_enter",
    "apply_story_action",
    "attempt_breakthrough",
    "attempt_realm_breakthrough",
    "build_scene_view",
    "clear_background_registry_cache",
    "clear_personality_questions_cache",
    "clear_realm_catalog_cache",
    "clear_story_cache",
    "commit_path_choice",
    "create_character",
    "cultivation_view",
    "entry_node_for_background",
    "flags_to_json",
    "get_background",
    "get_realm",
    "get_stage",
    "get_story_node",
    "list_backgrounds",
    "list_personality_questions",
    "list_realms",
    "list_stages",
    "load_background_registry",
    "load_realm_catalog",
    "load_story_registry",
    "parse_flags",
    "validate_identity_answers",
]
