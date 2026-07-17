"""Alchemy recipe ownership persistence (mutable state only)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_adventure.db.models import AlchemyRecipeOwnership
from ai_adventure.engine.alchemy import AlchemyRecipeOwnershipRecord


class AlchemyRecipeOwnershipRepository:
    """Load/save alchemy recipe ownership rows (no game rules)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_actor(self, save_id: str, actor_id: str) -> list[AlchemyRecipeOwnership]:
        """Return all ownership rows for one actor in a save."""

        statement = select(AlchemyRecipeOwnership).where(
            AlchemyRecipeOwnership.save_id == save_id,
            AlchemyRecipeOwnership.actor_id == actor_id,
        )
        return list(self._session.scalars(statement).all())

    def get(
        self,
        save_id: str,
        actor_id: str,
        recipe_id: str,
    ) -> AlchemyRecipeOwnership | None:
        """Return one ownership row if present."""

        statement = select(AlchemyRecipeOwnership).where(
            AlchemyRecipeOwnership.save_id == save_id,
            AlchemyRecipeOwnership.actor_id == actor_id,
            AlchemyRecipeOwnership.recipe_id == recipe_id,
        )
        return self._session.scalar(statement)

    def upsert_awakened(
        self,
        *,
        save_id: str,
        actor_id: str,
        recipe_id: str,
        world_day: int,
        grade_rank: int = 1,
    ) -> AlchemyRecipeOwnership:
        """Create or refresh an awakened ownership row (caller commits)."""

        existing = self.get(save_id, actor_id, recipe_id)
        if existing is not None:
            existing.awakened = 1
            if existing.grade_rank < grade_rank:
                existing.grade_rank = grade_rank
            existing.awakened_world_day = world_day
            return existing

        row = AlchemyRecipeOwnership(
            save_id=save_id,
            actor_id=actor_id,
            recipe_id=recipe_id,
            awakened=1,
            grade_rank=grade_rank,
            awakened_world_day=world_day,
        )
        self._session.add(row)
        return row

    @staticmethod
    def to_engine_records(
        rows: list[AlchemyRecipeOwnership],
    ) -> list[AlchemyRecipeOwnershipRecord]:
        """Map ORM rows to engine ownership DTOs."""

        return [
            AlchemyRecipeOwnershipRecord(
                actor_id=row.actor_id,
                recipe_id=row.recipe_id,
                awakened=bool(row.awakened),
                grade_rank=int(row.grade_rank),
            )
            for row in rows
        ]

