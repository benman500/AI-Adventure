"""NPC application service — permanent authored interaction pipeline.

Canonical entry: ``interact(save_id, npc_id, action_id)``.
Pipeline: validate → WorldClock → allowlisted rewards → EventEngine → persist.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session, sessionmaker

from ai_adventure.db.models import InventoryItem
from ai_adventure.engine.constants import EVENT_TYPE_NPC_INTERACTION
from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.npcs import (
    NpcInteractionPlayerContext,
    assert_npc_catalog_valid,
    get_npc,
    list_offered_actions_for_npc,
    load_npc_action_catalog,
    npc_action_eligible,
    plan_npc_interaction,
    resolve_npc_sect_id,
)
from ai_adventure.engine.story import flags_to_json, parse_flags
from ai_adventure.repositories.npc_world_state import NpcWorldStateRepository
from ai_adventure.repositories.locations import LocationPresenceRepository
from ai_adventure.repositories.saves import SaveRepository
from ai_adventure.repositories.sects import SectRepository
from ai_adventure.repositories.story import StoryRepository
from ai_adventure.services.locations import LocationService
from ai_adventure.services.sects import SectService
from ai_adventure.services.techniques import TechniqueService


class NpcService:
    """Orchestrates NPC catalog cards, spawn ensure, and interactions."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ensure_defaults_at_location(
        self,
        session: Session,
        *,
        save_id: str,
        location_id: str,
    ) -> None:
        """Spawn catalog NPCs whose default location matches ``location_id``."""

        from ai_adventure.engine.npcs import list_npcs

        assert_npc_catalog_valid()
        for definition in list_npcs():
            if definition.default_location_id == location_id:
                self.ensure_spawned(session, save_id=save_id, npc_id=definition.npc_id)

    def list_present_cards(
        self,
        session: Session,
        *,
        save_id: str,
        location_id: str,
    ) -> list[dict[str, Any]]:
        """NPCs at ``location_id`` with catalog identity + offered actions."""

        assert_npc_catalog_valid()
        load_npc_action_catalog()
        self.ensure_defaults_at_location(
            session, save_id=save_id, location_id=location_id
        )
        sect_service = SectService(self._session_factory)
        rows = NpcWorldStateRepository(session).list_at_location(save_id, location_id)
        cards: list[dict[str, Any]] = []
        for row in rows:
            definition = get_npc(row.npc_id)
            record = NpcWorldStateRepository.to_engine_record(row)
            sect_id = resolve_npc_sect_id(
                definition, sect_id_override=record.sect_id_override
            )
            standing = (
                sect_service.get_standing_score(session, save_id, sect_id)
                if sect_id
                else None
            )
            offered = list_offered_actions_for_npc(definition)
            membership = SectRepository(session).get_for_save(save_id)
            progress = StoryRepository(session).get_for_save(save_id)
            story_flags = (
                parse_flags(progress.flags_json).values if progress is not None else {}
            )
            save = SaveRepository(session).get_with_player(save_id)
            player = None if save is None else save.player
            player_ctx = NpcInteractionPlayerContext(
                location_id=location_id,
                realm_id="" if player is None else str(player.realm_id),
                stage_id="" if player is None else str(player.stage_id),
                sect_id=None if membership is None else str(membership.sect_id),
                sect_rank_id=None if membership is None else str(membership.rank_id),
                sect_standing=standing,
                story_flags=dict(story_flags),
            )
            eligible_actions = [
                action
                for action in offered
                if npc_action_eligible(
                    action=action,
                    definition=definition,
                    state=record,
                    player=player_ctx,
                    npc_sect_id=sect_id,
                )
            ]
            cards.append(
                {
                    "npc_id": definition.npc_id,
                    "actor_id": record.actor_id,
                    "display_name": definition.display_name,
                    "role_tags": list(definition.role_tags),
                    "description": definition.description,
                    "cultivation_summary": definition.cultivation_summary.model_dump(),
                    "sect_id": sect_id,
                    "current_location_id": record.current_location_id,
                    "status": record.status,
                    "discovered": record.discovered,
                    "met": record.met,
                    "relationship_score": record.relationship_score,
                    "sect_standing_score": standing,
                    "available_actions": [
                        {
                            "id": action.id,
                            "label": action.label,
                            "description": action.description,
                            "duration_days": action.duration_days,
                        }
                        for action in eligible_actions
                    ],
                    "can_greet": any(action.id == "greet" for action in eligible_actions),
                }
            )
        return cards

    def ensure_spawned(
        self,
        session: Session,
        *,
        save_id: str,
        npc_id: str,
    ) -> dict[str, Any]:
        """Ensure mutable world state exists for catalog ``npc_id``."""

        assert_npc_catalog_valid()
        definition = get_npc(npc_id)
        row = NpcWorldStateRepository(session).ensure_spawned(
            save_id=save_id,
            npc_id=definition.npc_id,
            current_location_id=definition.default_location_id,
            discovered=True,
        )
        return {
            "npc_id": definition.npc_id,
            "actor_id": row.id,
            "display_name": definition.display_name,
            "current_location_id": row.current_location_id,
        }

    def greet(self, save_id: str, npc_id: str) -> dict[str, Any]:
        """Compatibility wrapper for ``interact(..., action_id='greet')``."""

        return self.interact(save_id, npc_id, "greet")

    def interact(self, save_id: str, npc_id: str, action_id: str) -> dict[str, Any]:
        """Canonical NPC interaction entry point.

        Intent → validate requirements → WorldClock → allowlisted rewards →
        optional EventEngine → persistence → presentation facts.
        """

        assert_npc_catalog_valid()
        load_npc_action_catalog()
        with self._session_factory() as session:
            save_repo = SaveRepository(session)
            state_repo = NpcWorldStateRepository(session)
            sect_service = SectService(self._session_factory)
            save = save_repo.get_with_player(save_id)
            if save is None or save.player is None:
                raise EngineValidationError("Save not found")

            definition = get_npc(npc_id)
            row = state_repo.get_by_npc_id(save_id, npc_id)
            if row is None:
                raise EngineValidationError(f"Unknown NPC in this save: {npc_id!r}")

            record = state_repo.to_engine_record(row)
            npc_sect_id = resolve_npc_sect_id(
                definition, sect_id_override=record.sect_id_override
            )
            membership = SectRepository(session).get_for_save(save_id)
            standing = (
                sect_service.get_standing_score(session, save_id, npc_sect_id)
                if npc_sect_id
                else None
            )
            progress = save.story_progress
            story_flags = (
                parse_flags(progress.flags_json).values
                if progress is not None
                else {}
            )

            player_ctx = NpcInteractionPlayerContext(
                location_id=str(save.player.current_location_id),
                realm_id=str(save.player.realm_id),
                stage_id=str(save.player.stage_id),
                sect_id=None if membership is None else str(membership.sect_id),
                sect_rank_id=None if membership is None else str(membership.rank_id),
                sect_standing=standing,
                story_flags=dict(story_flags),
            )

            resolution = plan_npc_interaction(
                definition=definition,
                state=record,
                player=player_ctx,
                action_id=action_id,
            )

            if resolution.duration_days:
                LocationService(session).advance_world_days(save, resolution.duration_days)

            state_repo.apply_interaction(
                row,
                relationship_score=resolution.relationship_after,
                met=resolution.met,
                world_day=int(save.world_day),
            )

            if (
                resolution.sect_id is not None
                and resolution.sect_standing_after is not None
            ):
                sect_service.apply_standing(
                    session,
                    save_id=save_id,
                    sect_id=resolution.sect_id,
                    standing_score=resolution.sect_standing_after,
                    world_day=int(save.world_day),
                )

            learned: list[dict[str, Any]] = []
            tech_service = TechniqueService(self._session_factory)
            for technique_id in resolution.technique_ids_to_learn:
                learned.append(
                    tech_service.learn_in_session(
                        session,
                        save=save,
                        player=save.player,
                        technique_id=technique_id,
                        equipped=True,
                    )
                )

            for item_code, quantity in resolution.items_to_grant:
                self._grant_item(
                    session,
                    save_id=save_id,
                    player=save.player,
                    item_code=item_code,
                    quantity=quantity,
                )

            flag_updates = list(resolution.flag_updates)
            for location_id in resolution.location_ids_to_unlock:
                flag_updates.append((f"unlocked_{location_id}", True))
                LocationPresenceRepository(session).record_visit(
                    save.id, location_id, int(save.world_day)
                )

            if flag_updates and progress is not None:
                flags = parse_flags(progress.flags_json)
                for flag_name, flag_value in flag_updates:
                    flags = flags.set(flag_name, flag_value)
                StoryRepository(session).update(
                    progress,
                    current_node_id=progress.current_node_id,
                    flags_json=flags_to_json(flags),
                )

            save_repo.append_event(
                save_id,
                event_type=EVENT_TYPE_NPC_INTERACTION,
                payload={
                    "npc_id": resolution.npc_id,
                    "action_id": resolution.action_id,
                    "relationship_before": resolution.relationship_before,
                    "relationship_after": resolution.relationship_after,
                    "sect_id": resolution.sect_id,
                    "sect_standing_before": resolution.sect_standing_before,
                    "sect_standing_after": resolution.sect_standing_after,
                    "sect_standing_delta": resolution.sect_standing_delta,
                    "technique_ids": list(resolution.technique_ids_to_learn),
                    "flag_updates": [
                        {"flag": name, "value": value}
                        for name, value in flag_updates
                    ],
                    "location_ids_unlocked": list(resolution.location_ids_to_unlock),
                    "duration_days": resolution.duration_days,
                    "world_day": int(save.world_day),
                    "actor_id": str(row.id),
                },
            )

            event_message: str | None = None
            if resolution.trigger_kind:
                from ai_adventure.services.events import EventService

                event_outcome = EventService(session).run_trigger(
                    save=save,
                    player=save.player,
                    progress=save.story_progress,
                    trigger_kind=resolution.trigger_kind,
                    action_id=resolution.action_id,
                )
                event_message = event_outcome.presentation_message

            session.commit()
            return {
                "npc_id": resolution.npc_id,
                "display_name": definition.display_name,
                "action_id": resolution.action_id,
                "relationship_before": resolution.relationship_before,
                "relationship_after": resolution.relationship_after,
                "sect_id": resolution.sect_id,
                "sect_standing_before": resolution.sect_standing_before,
                "sect_standing_after": resolution.sect_standing_after,
                "techniques_learned": learned,
                "duration_days": resolution.duration_days,
                "world_day": int(save.world_day),
                "summary": resolution.summary,
                "presentation_text": resolution.presentation_text,
                "event_message": event_message,
            }

    def _grant_item(
        self,
        session: Session,
        *,
        save_id: str,
        player: Any,
        item_code: str,
        quantity: int,
    ) -> None:
        """Stack or create an inventory item for the player."""

        for row in list(getattr(player, "inventory_items", []) or []):
            if row.item_code == item_code:
                row.quantity = int(row.quantity) + int(quantity)
                session.add(row)
                return
        session.add(
            InventoryItem(
                id=str(uuid4()),
                save_id=save_id,
                player_id=player.id,
                item_code=item_code,
                display_name=item_code,
                quantity=int(quantity),
            )
        )
