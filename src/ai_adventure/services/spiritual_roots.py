"""Spiritual root awakening / ownership orchestration (Phase 7)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from ai_adventure.engine.constants import EVENT_TYPE_SPIRITUAL_ROOT_AWAKENED
from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.spiritual_roots import (
    STARTER_ROOT_ID,
    get_spiritual_root,
    list_spiritual_roots,
    validate_spiritual_root_catalog_against_bundles,
)
from ai_adventure.repositories import SaveRepository
from ai_adventure.repositories.spiritual_roots import SpiritualRootOwnershipRepository


class SpiritualRootService:
    """Application service for spiritual root catalog + ownership.

    Roots contribute to ``ModifierSnapshot`` only through the shared snapshot
    builder (with techniques). Consumers never call this for private math.
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_root_cards(self, session: Session, save_id: str, actor_id: str) -> list[dict[str, Any]]:
        """Return catalog roots with awakened flags for UI / tests."""

        validate_spiritual_root_catalog_against_bundles()
        owned = {
            row.root_id: row
            for row in SpiritualRootOwnershipRepository(session).list_for_actor(save_id, actor_id)
        }
        cards: list[dict[str, Any]] = []
        for root in list_spiritual_roots():
            row = owned.get(root.id)
            cards.append(
                {
                    "id": root.id,
                    "display_name": root.display_name,
                    "element": root.element,
                    "grade_rank": root.grade_rank,
                    "description": root.description,
                    "awakened": row is not None and bool(row.awakened),
                    "owned_grade_rank": int(row.grade_rank) if row is not None else None,
                }
            )
        return cards

    def awaken_root(self, save_id: str, root_id: str) -> dict[str, Any]:
        """Awaken a spiritual root for the save's player actor."""

        validate_spiritual_root_catalog_against_bundles()
        root = get_spiritual_root(root_id)
        with self._session_factory() as session:
            save_repo = SaveRepository(session)
            save = save_repo.get_with_player(save_id)
            if save is None or save.player is None:
                raise EngineValidationError("Save not found")
            actor_id = str(getattr(save.player, "actor_id"))
            row = SpiritualRootOwnershipRepository(session).upsert_awakened(
                save_id=save_id,
                actor_id=actor_id,
                root_id=root.id,
                world_day=int(save.world_day),
                grade_rank=root.grade_rank,
            )
            save_repo.append_event(
                save_id,
                event_type=EVENT_TYPE_SPIRITUAL_ROOT_AWAKENED,
                payload={
                    "root_id": root.id,
                    "actor_id": actor_id,
                    "grade_rank": int(row.grade_rank),
                    "world_day": int(save.world_day),
                },
            )
            session.commit()
            return {
                "root_id": root.id,
                "display_name": root.display_name,
                "awakened": True,
                "grade_rank": int(row.grade_rank),
            }

    def grant_starter_root(
        self,
        session: Session,
        *,
        save_id: str,
        actor_id: str,
        world_day: int,
        root_id: str = STARTER_ROOT_ID,
    ) -> None:
        """Awaken the starter root inside an open create transaction."""

        validate_spiritual_root_catalog_against_bundles()
        root = get_spiritual_root(root_id)
        SpiritualRootOwnershipRepository(session).upsert_awakened(
            save_id=save_id,
            actor_id=actor_id,
            root_id=root.id,
            world_day=world_day,
            grade_rank=root.grade_rank,
        )
        SaveRepository(session).append_event(
            save_id,
            event_type=EVENT_TYPE_SPIRITUAL_ROOT_AWAKENED,
            payload={
                "root_id": root.id,
                "actor_id": actor_id,
                "grade_rank": root.grade_rank,
                "world_day": world_day,
                "starter": True,
            },
        )
