"""Application services: use-case orchestration."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
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
from ai_adventure.engine.constants import (
    DELETE_CONFIRMATION_VALUE,
    PATH_STATUS_CONFIRMED_BOUNDLESS,
    PATH_STATUS_CONFIRMED_ORDINARY,
)
from ai_adventure.engine.cultivation import cultivation_state_from_player, cultivation_view
from ai_adventure.engine.identity import PersonalityQuestion
from ai_adventure.engine.story import (
    StoryContext,
    apply_on_enter,
    apply_story_action,
    build_scene_view,
    entry_node_for_background,
    flags_to_json,
    parse_flags,
)
from ai_adventure.narration import Narration, Narrator, create_narrator
from ai_adventure.repositories import (
    EventLogRepository,
    MetaRepository,
    NpcRepository,
    SaveRepository,
    StoryRepository,
)
from ai_adventure.services.locations import LocationService


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
class PlaySceneModel:
    """Story scene view for the play UI."""

    app_name: str
    save_id: str
    character_name: str
    background_display_name: str
    current_location_name: str
    world_day: int
    node_id: str
    title: str
    narrative: str
    actions: list[dict[str, str]]
    cultivation_methods: list[dict[str, Any]]
    cultivation: dict[str, Any]
    location_actions: list[dict[str, Any]]
    techniques: list[dict[str, Any]]
    spiritual_roots: list[dict[str, Any]] = field(default_factory=list)
    present_npcs: list[dict[str, Any]] = field(default_factory=list)
    sect_membership: dict[str, Any] | None = None
    aspiration_panel: dict[str, Any] | None = None
    travel_destinations: list[dict[str, Any]] = field(default_factory=list)
    inventory: list[dict[str, Any]] = field(default_factory=list)
    money_copper: int = 0
    identity_answers: dict[str, str] = field(default_factory=dict)
    message: str | None = None
    opening_complete: bool = False
    cultivation_available: bool = True
    cultivation_blocked_reason: str | None = None
    last_cultivation_result: dict[str, Any] | None = None
    breakthrough_readiness: dict[str, Any] | None = None
    last_breakthrough_result: dict[str, Any] | None = None
    breakthrough_can_attempt: bool = False


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
            session.flush()
            loaded = repo.get_with_player(save.id)
            if loaded is None or loaded.player is None:
                raise EngineValidationError("Failed to create save player")
            LocationService(session).establish_starting_presence(
                loaded,
                loaded.player,
                state.current_location_id,
            )
            from ai_adventure.services.spiritual_roots import SpiritualRootService

            SpiritualRootService(self._session_factory).grant_starter_root(
                session,
                save_id=loaded.id,
                actor_id=str(getattr(loaded.player, "actor_id")),
                world_day=int(loaded.world_day),
            )
            session.commit()
            return self._loaded_model_from_state(
                save_id=loaded.id,
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

    def get_play_scene(self, save_id: str, *, message: str | None = None) -> PlaySceneModel:
        """Load authoritative story scene for a save (bootstrap if needed)."""

        with self._session_factory() as session:
            save_repo = SaveRepository(session)
            save = save_repo.get_with_player(save_id)
            if save is None or save.player is None:
                raise EngineValidationError("Save not found")

            story_repo = StoryRepository(session)
            progress = save.story_progress
            if progress is None:
                entry = entry_node_for_background(save.background_id)
                progress = story_repo.create(save_id=save.id, current_node_id=entry)
                save_repo.mark_story_started(save)

            player = save.player
            # Persist realm catalog qi floor + normalized realm/stage ids on load.
            synced = cultivation_state_from_player(player)
            if (
                synced.qi_reserve_max != player.qi_reserve_max
                or synced.realm_id != player.realm_id
                or synced.stage_id != getattr(player, "stage_id", synced.stage_id)
            ):
                save_repo.apply_player_cultivation(player, synced)
            context = self._story_context(session, save, player, progress)
            scene = build_scene_view(context)
            techniques = self._technique_cards(session, save, player)
            save_repo.touch_last_played(save)
            session.commit()
            return self._play_scene_model(
                save=save,
                player=player,
                scene=scene,
                message=message,
                techniques=techniques,
                breakthrough_modifiers=context.breakthrough_modifiers,
            )

    def submit_story_action(
        self,
        save_id: str,
        action_id: str,
    ) -> PlaySceneModel:
        """Apply a story or cultivation action through the engine."""

        with self._session_factory() as session:
            save_repo = SaveRepository(session)
            story_repo = StoryRepository(session)
            npc_repo = NpcRepository(session)

            save = save_repo.get_with_player(save_id)
            if save is None or save.player is None:
                raise EngineValidationError("Save not found")
            progress = save.story_progress
            if progress is None:
                raise EngineValidationError("Story progress not initialized")

            player = save.player
            context = self._story_context(session, save, player, progress)
            result = apply_story_action(context, action_id)

            travel_event_message = self._persist_story_result(
                session=session,
                save_repo=save_repo,
                story_repo=story_repo,
                npc_repo=npc_repo,
                save=save,
                player=player,
                progress=progress,
                result=result,
            )

            event_message: str | None = None
            if getattr(result, "last_cultivation_result", None) is not None:
                from ai_adventure.services.events import EventService

                event_outcome = EventService(session).run_after_cultivation_session(
                    save=save,
                    player=player,
                    progress=progress,
                    cultivation=result.cultivation,
                )
                event_message = event_outcome.presentation_message

            save_repo.touch_last_played(save)
            session.commit()

            progress.current_node_id = result.next_node_id
            context = self._story_context(session, save, player, progress)
            scene = build_scene_view(context)
            techniques = self._technique_cards(session, save, player)
            message = result.summary
            if travel_event_message:
                message = f"{message} {travel_event_message}".strip()
            if event_message:
                message = f"{message} {event_message}".strip()
            return self._play_scene_model(
                save=save,
                player=player,
                scene=scene,
                message=message,
                techniques=techniques,
                breakthrough_modifiers=context.breakthrough_modifiers,
            )

    def perform_location_action(self, save_id: str, action_id: str) -> PlaySceneModel:
        """Execute a location action through LocationService (Phase 5c)."""

        with self._session_factory() as session:
            save_repo = SaveRepository(session)
            save = save_repo.get_with_player(save_id)
            if save is None or save.player is None:
                raise EngineValidationError("Save not found")
            progress = save.story_progress
            if progress is None:
                raise EngineValidationError("Story progress not initialized")

            result = LocationService(session).perform_action(
                save=save,
                player=save.player,
                progress=progress,
                action_id=action_id,
            )
            save_repo.touch_last_played(save)
            session.commit()

            context = self._story_context(session, save, save.player, progress)
            scene = build_scene_view(context)
            techniques = self._technique_cards(session, save, save.player)
            message = result.presentation_message or result.resolution.summary
            if result.event_message:
                message = f"{message} {result.event_message}".strip()
            return self._play_scene_model(
                save=save,
                player=save.player,
                scene=scene,
                message=message,
                techniques=techniques,
                breakthrough_modifiers=context.breakthrough_modifiers,
            )

    def _story_context(
        self,
        session: Session,
        save: object,
        player: object,
        progress: object,
    ) -> StoryContext:
        from ai_adventure.services.techniques import (
            build_breakthrough_snapshot,
            build_cultivate_session_snapshot,
        )

        save_id = str(getattr(save, "id"))
        actor_id = str(getattr(player, "actor_id"))
        world_day = int(getattr(save, "world_day"))
        session_modifiers = build_cultivate_session_snapshot(
            session,
            save_id=save_id,
            actor_id=actor_id,
            world_day=world_day,
        )
        breakthrough_modifiers = build_breakthrough_snapshot(
            session,
            save_id=save_id,
            actor_id=actor_id,
            world_day=world_day,
        )
        return StoryContext(
            background_id=getattr(save, "background_id"),
            current_node_id=getattr(progress, "current_node_id"),
            flags=parse_flags(getattr(progress, "flags_json")),
            cultivation=cultivation_state_from_player(player),
            world_day=getattr(save, "world_day"),
            session_modifiers=session_modifiers,
            breakthrough_modifiers=breakthrough_modifiers,
        )

    def _technique_cards(
        self,
        session: Session,
        save: object,
        player: object,
    ) -> list[dict[str, Any]]:
        from ai_adventure.engine.techniques import can_learn_technique, list_techniques
        from ai_adventure.repositories import TechniqueMasteryRepository

        rows = TechniqueMasteryRepository(session).list_for_actor(
            str(getattr(save, "id")),
            str(getattr(player, "actor_id")),
        )
        by_id = {row.technique_id: row for row in rows}
        cards: list[dict[str, Any]] = []
        for tech in list_techniques():
            row = by_id.get(tech.id)
            cards.append(
                {
                    "id": tech.id,
                    "display_name": tech.display_name,
                    "description": tech.description,
                    "known": bool(row.known) if row else False,
                    "equipped": bool(row.equipped) if row else False,
                    "mastery_rank": row.mastery_rank if row else 0,
                    "learnable": can_learn_technique(
                        tech,
                        realm_id=str(getattr(player, "realm_id")),
                    )[0],
                }
            )
        return cards

    def travel_to(self, save_id: str, to_location_id: str) -> PlaySceneModel:
        """Travel along a catalog edge via LocationService (existing travel graph)."""

        with self._session_factory() as session:
            save_repo = SaveRepository(session)
            save = save_repo.get_with_player(save_id)
            if save is None or save.player is None:
                raise EngineValidationError("Save not found")
            progress = save.story_progress
            if progress is None:
                raise EngineValidationError("Story progress not initialized")

            result = LocationService(session).travel(
                save=save,
                player=save.player,
                progress=progress,
                to_location_id=to_location_id,
            )
            save_repo.touch_last_played(save)
            session.commit()

            context = self._story_context(session, save, save.player, progress)
            scene = build_scene_view(context)
            techniques = self._technique_cards(session, save, save.player)
            message = result.presentation_message or result.resolution.summary
            if result.event_message:
                message = f"{message} {result.event_message}".strip()
            return self._play_scene_model(
                save=save,
                player=save.player,
                scene=scene,
                message=message,
                techniques=techniques,
                breakthrough_modifiers=context.breakthrough_modifiers,
            )

    def learn_technique(self, save_id: str, technique_id: str) -> PlaySceneModel:
        """Learn a starter technique and return the refreshed play scene."""

        from ai_adventure.services.techniques import TechniqueService

        learned = TechniqueService(self._session_factory).learn(save_id, technique_id)
        return self.get_play_scene(
            save_id,
            message=f"You learn {learned['display_name']}.",
        )

    def greet_npc(self, save_id: str, npc_id: str) -> PlaySceneModel:
        """Greet an NPC (compat wrapper around ``interact_with_npc``)."""

        return self.interact_with_npc(save_id, npc_id, "greet")

    def interact_with_npc(self, save_id: str, npc_id: str, action_id: str) -> PlaySceneModel:
        """Canonical NPC interaction via NpcService (Phase 9c)."""

        from ai_adventure.services.npcs import NpcService

        outcome = NpcService(self._session_factory).interact(save_id, npc_id, action_id)
        message = str(outcome["presentation_text"])
        event_message = outcome.get("event_message")
        if event_message:
            message = f"{message} {event_message}".strip()
        return self.get_play_scene(save_id, message=message)

    def _persist_story_result(
        self,
        *,
        session: Session,
        save_repo: SaveRepository,
        story_repo: StoryRepository,
        npc_repo: NpcRepository,
        save: object,
        player: object,
        progress: object,
        result: object,
    ) -> str | None:
        """Persist story engine outcome. Location/day changes go through LocationService."""

        story_repo.update(
            progress,
            current_node_id=result.next_node_id,
            flags_json=flags_to_json(result.flags),
        )
        save_repo.apply_player_cultivation(player, result.cultivation)

        if getattr(result.cultivation, "path_status", None) in (
            PATH_STATUS_CONFIRMED_ORDINARY,
            PATH_STATUS_CONFIRMED_BOUNDLESS,
        ):
            save_repo.mark_path_confirmed(player)

        location_result = LocationService(session).apply_story_transition(
            save=save,  # type: ignore[arg-type]
            player=player,  # type: ignore[arg-type]
            progress=progress,  # type: ignore[arg-type]
            result_location_id=result.location_id,
            result_world_day=int(result.world_day),
        )
        travel_event_message = (
            None if location_result is None else location_result.event_message
        )

        playtime_delta = int(getattr(result, "playtime_seconds", 0) or 0)
        if playtime_delta:
            save_repo.add_playtime(save, playtime_delta)
        last_result = getattr(result, "last_cultivation_result", None)
        if last_result is not None:
            player.last_cultivation_result_json = json.dumps(last_result, sort_keys=True)
            player.cultivation_rng_counter = (
                int(getattr(player, "cultivation_rng_counter", 0) or 0) + 1
            )
        last_bt = getattr(result, "last_breakthrough_result", None)
        if last_bt is not None:
            player.last_breakthrough_result_json = json.dumps(last_bt, sort_keys=True)
        for npc in result.spawned_npcs:
            from ai_adventure.services.npcs import NpcService

            NpcService(self._session_factory).ensure_spawned(
                session,
                save_id=getattr(save, "id"),
                npc_id=str(npc["npc_id"]),
            )
        if result.sect_id and result.sect_rank:
            from ai_adventure.services.sects import SectService

            SectService(self._session_factory).join(
                session,
                save_id=getattr(save, "id"),
                sect_id=str(result.sect_id),
                rank_id=str(result.sect_rank),
                world_day=int(getattr(save, "world_day")),
                waive_standing_gate=True,
            )
        for event in result.events:
            save_repo.append_event(
                getattr(save, "id"),
                event_type=str(event["event_type"]),
                payload=dict(event.get("payload", {})),
            )
        return travel_event_message

    def _play_scene_model(
        self,
        *,
        save: object,
        player: object,
        scene: object,
        message: str | None,
        techniques: list[dict[str, Any]] | None = None,
        breakthrough_modifiers: object | None = None,
    ) -> PlaySceneModel:
        cultivation = cultivation_view(cultivation_state_from_player(player))
        opening_complete = cultivation["path_status"] in (
            PATH_STATUS_CONFIRMED_ORDINARY,
            PATH_STATUS_CONFIRMED_BOUNDLESS,
        ) and scene.node_id in {"shared_post_ordinary_02", "shared_post_boundless_02"}

        last_result: dict[str, Any] | None = None
        raw_last = getattr(player, "last_cultivation_result_json", None)
        if raw_last:
            try:
                parsed = json.loads(raw_last)
                if isinstance(parsed, dict):
                    last_result = parsed
            except json.JSONDecodeError:
                last_result = None

        last_bt: dict[str, Any] | None = None
        raw_bt = getattr(player, "last_breakthrough_result_json", None)
        if raw_bt:
            try:
                parsed_bt = json.loads(raw_bt)
                if isinstance(parsed_bt, dict):
                    last_bt = parsed_bt
            except json.JSONDecodeError:
                last_bt = None

        from ai_adventure.engine.breakthroughs import (
            evaluate_breakthrough_readiness,
            readiness_to_dict,
        )
        from ai_adventure.engine.modifiers import ModifierSnapshot

        state = cultivation_state_from_player(player)
        bt_mods = breakthrough_modifiers if isinstance(breakthrough_modifiers, ModifierSnapshot) else None
        readiness = readiness_to_dict(
            evaluate_breakthrough_readiness(state, modifiers=bt_mods)
        )

        from ai_adventure.engine.location_actions import list_available_location_actions

        location_actions = [
            {
                "id": item.id,
                "label": item.label,
                "description": item.description,
                "duration_days": item.duration_days,
                "implemented": item.implemented,
                "available": item.available,
                "blocked_reason": item.blocked_reason,
            }
            for item in list_available_location_actions(str(getattr(player, "current_location_id")))
        ]

        from ai_adventure.engine.locations import get_location, list_travel_destinations
        from ai_adventure.services.aspirations import AspirationService
        from ai_adventure.services.spiritual_roots import SpiritualRootService
        from ai_adventure.services.npcs import NpcService
        from ai_adventure.services.sects import SectService

        inventory_items: list[dict[str, Any]] = []
        for item in getattr(player, "inventory_items", []) or []:
            inventory_items.append(
                {
                    "item_code": item.item_code,
                    "display_name": item.display_name,
                    "quantity": item.quantity,
                }
            )

        identity_raw = getattr(player, "identity_answers_json", "{}") or "{}"
        try:
            identity_answers = json.loads(identity_raw)
            if not isinstance(identity_answers, dict):
                identity_answers = {}
        except json.JSONDecodeError:
            identity_answers = {}

        with self._session_factory() as root_session:
            spiritual_roots = SpiritualRootService(self._session_factory).list_root_cards(
                root_session,
                str(getattr(save, "id")),
                str(getattr(player, "actor_id")),
            )
            present_npcs = NpcService(self._session_factory).list_present_cards(
                root_session,
                save_id=str(getattr(save, "id")),
                location_id=str(getattr(player, "current_location_id")),
            )
            sect_membership = SectService(self._session_factory).membership_card(
                root_session,
                str(getattr(save, "id")),
            )
            aspiration_panel = AspirationService(self._session_factory).build_play_panel(
                root_session,
                str(getattr(save, "id")),
            )

        travel_destinations: list[dict[str, Any]] = []
        story_flags = (
            parse_flags(save.story_progress.flags_json).values
            if getattr(save, "story_progress", None) is not None
            else {}
        )
        for edge in list_travel_destinations(
            str(getattr(player, "current_location_id")),
            story_flags=dict(story_flags),
        ):
            destination = get_location(edge.to)
            travel_destinations.append(
                {
                    "location_id": destination.id,
                    "display_name": destination.display_name,
                    "days": int(edge.days),
                    "tags": list(destination.tags),
                    "kind": destination.kind,
                    "environment_tags": list(destination.environment_tags),
                    "ambience": destination.presentation.ambience,
                }
            )

        return PlaySceneModel(
            app_name=self._settings.app_name,
            save_id=getattr(save, "id"),
            character_name=getattr(player, "character_name"),
            background_display_name=getattr(save, "background_display_name"),
            current_location_name=getattr(player, "current_location_name"),
            world_day=getattr(save, "world_day"),
            node_id=scene.node_id,
            title=scene.title,
            narrative=scene.narrative,
            actions=list(scene.actions),
            cultivation_methods=list(scene.cultivation_methods),
            cultivation=cultivation,
            location_actions=location_actions,
            techniques=list(techniques or []),
            spiritual_roots=spiritual_roots,
            present_npcs=present_npcs,
            sect_membership=sect_membership,
            aspiration_panel=aspiration_panel,
            travel_destinations=travel_destinations,
            inventory=inventory_items,
            money_copper=int(getattr(player, "money_copper", 0) or 0),
            identity_answers={str(k): str(v) for k, v in identity_answers.items()},
            message=message,
            opening_complete=opening_complete,
            cultivation_available=bool(getattr(scene, "cultivation_available", True)),
            cultivation_blocked_reason=getattr(scene, "cultivation_blocked_reason", None),
            last_cultivation_result=last_result,
            breakthrough_readiness=readiness,
            last_breakthrough_result=last_bt,
            breakthrough_can_attempt=bool(getattr(scene, "breakthrough_can_attempt", False)),
        )

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
