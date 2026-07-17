"""NPC application service (Phase 9b vertical slice)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from ai_adventure.engine.constants import EVENT_TYPE_NPC_INTERACTION
from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.npcs import (
    assert_npc_catalog_valid,
    get_npc,
    plan_greet,
    resolve_npc_sect_id,
)
from ai_adventure.repositories.npc_world_state import NpcWorldStateRepository
from ai_adventure.repositories.saves import SaveRepository


class NpcService:
    """Orchestrates NPC catalog cards, spawn ensure, and greet interaction."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_present_cards(
        self,
        session: Session,
        *,
        save_id: str,
        location_id: str,
    ) -> list[dict[str, Any]]:
        """NPCs at ``location_id`` with catalog identity + mutable state."""

        assert_npc_catalog_valid()
        rows = NpcWorldStateRepository(session).list_at_location(save_id, location_id)
        cards: list[dict[str, Any]] = []
        for row in rows:
            definition = get_npc(row.npc_id)
            record = NpcWorldStateRepository.to_engine_record(row)
            cards.append(
                {
                    "npc_id": definition.npc_id,
                    "actor_id": record.actor_id,
                    "display_name": definition.display_name,
                    "role_tags": list(definition.role_tags),
                    "description": definition.description,
                    "cultivation_summary": definition.cultivation_summary.model_dump(),
                    "sect_id": resolve_npc_sect_id(
                        definition, sect_id_override=record.sect_id_override
                    ),
                    "current_location_id": record.current_location_id,
                    "status": record.status,
                    "discovered": record.discovered,
                    "met": record.met,
                    "relationship_score": record.relationship_score,
                    "can_greet": True,
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
        """Run the greet vertical-slice interaction and persist relationship."""

        assert_npc_catalog_valid()
        with self._session_factory() as session:
            save_repo = SaveRepository(session)
            state_repo = NpcWorldStateRepository(session)
            save = save_repo.get_with_player(save_id)
            if save is None or save.player is None:
                raise EngineValidationError("Save not found")

            definition = get_npc(npc_id)
            row = state_repo.get_by_npc_id(save_id, npc_id)
            if row is None:
                raise EngineValidationError(f"Unknown NPC in this save: {npc_id!r}")

            resolution = plan_greet(
                definition=definition,
                state=state_repo.to_engine_record(row),
                player_location_id=str(save.player.current_location_id),
            )
            state_repo.apply_interaction(
                row,
                relationship_score=resolution.relationship_after,
                met=resolution.met,
                world_day=int(save.world_day),
            )
            save_repo.append_event(
                save_id,
                event_type=EVENT_TYPE_NPC_INTERACTION,
                payload={
                    "npc_id": resolution.npc_id,
                    "action_id": resolution.action_id,
                    "relationship_before": resolution.relationship_before,
                    "relationship_after": resolution.relationship_after,
                    "world_day": int(save.world_day),
                    "actor_id": str(row.id),
                },
            )
            session.commit()
            return {
                "npc_id": resolution.npc_id,
                "display_name": definition.display_name,
                "action_id": resolution.action_id,
                "relationship_before": resolution.relationship_before,
                "relationship_after": resolution.relationship_after,
                "summary": resolution.summary,
                "presentation_text": resolution.presentation_text,
            }
