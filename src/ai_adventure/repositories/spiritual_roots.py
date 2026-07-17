"""Spiritual root ownership persistence (mutable state only)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_adventure.db.models import SpiritualRootOwnership
from ai_adventure.engine.spiritual_roots import SpiritualRootOwnershipRecord


class SpiritualRootOwnershipRepository:
    """Load/save spiritual root ownership rows (no game rules)."""

    def __init__(self, session: Session) -> None:
        """Bind to an open SQLAlchemy session."""

        self._session = session

    def list_for_actor(self, save_id: str, actor_id: str) -> list[SpiritualRootOwnership]:
        """Return all ownership rows for one actor in a save."""

        statement = select(SpiritualRootOwnership).where(
            SpiritualRootOwnership.save_id == save_id,
            SpiritualRootOwnership.actor_id == actor_id,
        )
        return list(self._session.scalars(statement).all())

    def get(
        self,
        save_id: str,
        actor_id: str,
        root_id: str,
    ) -> SpiritualRootOwnership | None:
        """Return one ownership row if present."""

        statement = select(SpiritualRootOwnership).where(
            SpiritualRootOwnership.save_id == save_id,
            SpiritualRootOwnership.actor_id == actor_id,
            SpiritualRootOwnership.root_id == root_id,
        )
        return self._session.scalar(statement)

    def upsert_awakened(
        self,
        *,
        save_id: str,
        actor_id: str,
        root_id: str,
        world_day: int,
        grade_rank: int = 1,
    ) -> SpiritualRootOwnership:
        """Create or refresh an awakened ownership row (caller commits)."""

        existing = self.get(save_id, actor_id, root_id)
        if existing is not None:
            existing.awakened = 1
            if existing.grade_rank < grade_rank:
                existing.grade_rank = grade_rank
            return existing
        row = SpiritualRootOwnership(
            save_id=save_id,
            actor_id=actor_id,
            root_id=root_id,
            awakened=1,
            grade_rank=grade_rank,
            awakened_world_day=world_day,
        )
        self._session.add(row)
        return row

    @staticmethod
    def to_engine_records(
        rows: list[SpiritualRootOwnership],
    ) -> list[SpiritualRootOwnershipRecord]:
        """Map ORM rows to engine ownership DTOs."""

        return [
            SpiritualRootOwnershipRecord(
                actor_id=row.actor_id,
                root_id=row.root_id,
                awakened=bool(row.awakened),
                grade_rank=int(row.grade_rank),
            )
            for row in rows
        ]
