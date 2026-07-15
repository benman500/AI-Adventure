"""Application services: use-case orchestration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from ai_adventure.config import Settings
from ai_adventure.engine import (
    BackgroundDefinition,
    CreatedCharacterState,
    EngineOutcome,
    EngineValidationError,
    GameEngine,
)
from ai_adventure.engine.constants import DELETE_CONFIRMATION_VALUE
from ai_adventure.engine.identity import PersonalityQuestion
from ai_adventure.narration import Narration, Narrator, create_narrator
from ai_adventure.repositories import EventLogRepository, MetaRepository, SaveRepository


@dataclass(frozen=True, slots=True)
class HomePageModel:
    """View model for the home page (facts from engine; text from narrator)."""

    app_name: str
    outcome: EngineOutcome
    narration: Narration
    schema_marker: str | None


@dataclass(frozen=True, slots=True)
class SaveListItem:
    """One row on the save-list screen."""

    save_id: str
    character_name: str
    background_display_name: str
    created_at: datetime
    last_played_at: datetime
    current_location_name: str
    playtime_seconds: int


@dataclass(frozen=True, slots=True)
class NewGameFormModel:
    """Data needed to render the new-game form."""

    app_name: str
    backgrounds: list[BackgroundDefinition]
    questions: list[PersonalityQuestion]
    error: str | None = None


@dataclass(frozen=True, slots=True)
class InventoryViewItem:
    """Inventory line for display."""

    item_code: str
    display_name: str
    quantity: int


@dataclass(frozen=True, slots=True)
class LoadedSaveModel:
    """Loaded save summary for the play-status screen."""

    app_name: str
    save_id: str
    character_name: str
    background_id: str
    background_display_name: str
    intro_flavor: str
    current_location_name: str
    money_copper: int
    cultivation_path: str
    realm_id: str
    stage_id: str
    identity_answers: dict[str, str]
    background_history: dict[str, Any]
    inventory: list[InventoryViewItem]
    narration: str | None = None
    created: bool = False


@dataclass(frozen=True, slots=True)
class DeleteConfirmModel:
    """Confirm-delete page view model."""

    app_name: str
    save_id: str
    character_name: str
    error: str | None = None


class GameAppService:
    """Coordinates engine → persist → narrate. Never invents mechanical outcomes."""

    def __init__(
        self,
        settings: Settings,
        session_factory: sessionmaker[Session],
        engine: GameEngine | None = None,
        narrator: Narrator | None = None,
    ) -> None:
        """Inject settings, session factory, engine, and narrator."""

        self._settings = settings
        self._session_factory = session_factory
        self._engine = engine or GameEngine()
        self._narrator = narrator or create_narrator(settings.narrator_backend)

    def build_home_page(self) -> HomePageModel:
        """Run engine ping, persist a schema marker, then narrate the outcome."""

        outcome = self._engine.ping()
        narration = self._narrator.narrate(outcome)

        with self._session_factory() as session:
            repo = MetaRepository(session)
            record = repo.upsert("architecture_scaffold", "ok")
            session.commit()
            marker = record.value

        return HomePageModel(
            app_name=self._settings.app_name,
            outcome=outcome,
            narration=narration,
            schema_marker=marker,
        )

    def build_new_game_form(self, error: str | None = None) -> NewGameFormModel:
        """Assemble selectable backgrounds and personality questions."""

        return NewGameFormModel(
            app_name=self._settings.app_name,
            backgrounds=self._engine.list_selectable_backgrounds(),
            questions=self._engine.list_personality_questions(),
            error=error,
        )

    def list_saves(self) -> list[SaveListItem]:
        """List non-deleted save slots."""

        with self._session_factory() as session:
            saves = SaveRepository(session).list_active()
            return [
                SaveListItem(
                    save_id=save.id,
                    character_name=save.character_name,
                    background_display_name=save.background_display_name,
                    created_at=save.created_at,
                    last_played_at=save.last_played_at,
                    current_location_name=save.current_location_name,
                    playtime_seconds=save.playtime_seconds,
                )
                for save in saves
            ]

    def create_new_game(
        self,
        *,
        character_name: str,
        background_id: str,
        identity_answers: dict[str, str],
    ) -> LoadedSaveModel:
        """Create a new save from engine-validated starting state."""

        state, outcome = self._engine.create_character(
            character_name=character_name,
            background_id=background_id,
            identity_answers=identity_answers,
        )
        narration = self._narrator.narrate(outcome)

        with self._session_factory() as session:
            repo = SaveRepository(session)
            save = repo.create_from_character_state(state)
            session.commit()
            return self._loaded_model_from_state(
                save_id=save.id,
                state=state,
                background_display_name=state.background_display_name,
                narration=narration.text,
                created=True,
            )

    def load_save(self, save_id: str) -> LoadedSaveModel:
        """Load an existing save and update last played."""

        with self._session_factory() as session:
            repo = SaveRepository(session)
            save = repo.get_with_player(save_id)
            if save is None or save.player is None:
                raise EngineValidationError("Save not found")
            repo.touch_last_played(save)
            session.commit()
            player = save.player
            inventory = [
                InventoryViewItem(
                    item_code=item.item_code,
                    display_name=item.display_name,
                    quantity=item.quantity,
                )
                for item in player.inventory_items
            ]
            return LoadedSaveModel(
                app_name=self._settings.app_name,
                save_id=save.id,
                character_name=player.character_name,
                background_id=player.background_id,
                background_display_name=save.background_display_name,
                intro_flavor=player.intro_flavor,
                current_location_name=player.current_location_name,
                money_copper=player.money_copper,
                cultivation_path=player.cultivation_path,
                realm_id=player.realm_id,
                stage_id=player.stage_id,
                identity_answers=json.loads(player.identity_answers_json),
                background_history=json.loads(player.background_history_json),
                inventory=inventory,
                narration=None,
                created=False,
            )

    def get_delete_confirm(self, save_id: str, error: str | None = None) -> DeleteConfirmModel:
        """Load metadata for the delete confirmation screen."""

        with self._session_factory() as session:
            save = SaveRepository(session).get_by_id(save_id)
            if save is None:
                raise EngineValidationError("Save not found")
            return DeleteConfirmModel(
                app_name=self._settings.app_name,
                save_id=save.id,
                character_name=save.character_name,
                error=error,
            )

    def delete_save(self, save_id: str, *, confirmation: str) -> None:
        """Soft-delete a save after explicit confirmation."""

        if confirmation.strip() != DELETE_CONFIRMATION_VALUE:
            raise EngineValidationError(
                f'Type {DELETE_CONFIRMATION_VALUE} to confirm deletion'
            )

        with self._session_factory() as session:
            repo = SaveRepository(session)
            save = repo.get_by_id(save_id)
            if save is None:
                raise EngineValidationError("Save not found")
            repo.soft_delete(save)
            session.commit()

    def list_events_for_save(self, save_id: str) -> list[dict[str, Any]]:
        """Return event log payloads for tests and future UI."""

        with self._session_factory() as session:
            if SaveRepository(session).get_by_id(save_id) is None:
                raise EngineValidationError("Save not found")
            entries = EventLogRepository(session).list_for_save(save_id)
            return [
                {
                    "id": entry.id,
                    "event_type": entry.event_type,
                    "payload": json.loads(entry.payload_json),
                    "created_at": entry.created_at,
                }
                for entry in entries
            ]

    def _loaded_model_from_state(
        self,
        *,
        save_id: str,
        state: CreatedCharacterState,
        background_display_name: str,
        narration: str | None,
        created: bool,
    ) -> LoadedSaveModel:
        return LoadedSaveModel(
            app_name=self._settings.app_name,
            save_id=save_id,
            character_name=state.character_name,
            background_id=state.background_id,
            background_display_name=background_display_name,
            intro_flavor=state.intro_flavor,
            current_location_name=state.current_location_name,
            money_copper=state.money_copper,
            cultivation_path=state.cultivation_path,
            realm_id=state.realm_id,
            stage_id=state.stage_id,
            identity_answers=dict(state.identity_answers),
            background_history=dict(state.background_history),
            inventory=[
                InventoryViewItem(
                    item_code=item.item_code,
                    display_name=item.display_name,
                    quantity=item.quantity,
                )
                for item in state.possessions
            ],
            narration=narration,
            created=created,
        )
