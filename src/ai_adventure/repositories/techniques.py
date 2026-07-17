"""Technique mastery persistence (mutable state only)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_adventure.db.models import TechniqueMastery
from ai_adventure.engine.techniques import TechniqueMasteryRecord


class TechniqueMasteryRepository:
    """Load/save technique mastery rows (no game rules)."""

    def __init__(self, session: Session) -> None:
        """Bind to an open SQLAlchemy session."""

        self._session = session

    def list_for_actor(self, save_id: str, actor_id: str) -> list[TechniqueMastery]:
        """Return all mastery rows for one actor in a save."""

        statement = select(TechniqueMastery).where(
            TechniqueMastery.save_id == save_id,
            TechniqueMastery.actor_id == actor_id,
        )
        return list(self._session.scalars(statement).all())

    def get(
        self,
        save_id: str,
        actor_id: str,
        technique_id: str,
    ) -> TechniqueMastery | None:
        """Return one mastery row if present."""

        statement = select(TechniqueMastery).where(
            TechniqueMastery.save_id == save_id,
            TechniqueMastery.actor_id == actor_id,
            TechniqueMastery.technique_id == technique_id,
        )
        return self._session.scalar(statement)

    def upsert_learned(
        self,
        *,
        save_id: str,
        actor_id: str,
        technique_id: str,
        world_day: int,
        equipped: bool = True,
        mastery_rank: int = 1,
    ) -> TechniqueMastery:
        """Create or refresh a known mastery row (caller commits)."""

        existing = self.get(save_id, actor_id, technique_id)
        if existing is not None:
            existing.known = 1
            existing.equipped = 1 if equipped else 0
            if existing.mastery_rank < mastery_rank:
                existing.mastery_rank = mastery_rank
            return existing
        row = TechniqueMastery(
            save_id=save_id,
            actor_id=actor_id,
            technique_id=technique_id,
            known=1,
            equipped=1 if equipped else 0,
            mastery_rank=mastery_rank,
            mastery_progress=0,
            learned_world_day=world_day,
        )
        self._session.add(row)
        return row

    def set_equipped(
        self,
        save_id: str,
        actor_id: str,
        technique_id: str,
        *,
        equipped: bool,
    ) -> TechniqueMastery | None:
        """Toggle equipped flag; return None if not known."""

        row = self.get(save_id, actor_id, technique_id)
        if row is None or not row.known:
            return None
        row.equipped = 1 if equipped else 0
        return row

    @staticmethod
    def to_engine_records(rows: list[TechniqueMastery]) -> list[TechniqueMasteryRecord]:
        """Map ORM rows to engine DTOs."""

        return [
            TechniqueMasteryRecord(
                actor_id=row.actor_id,
                technique_id=row.technique_id,
                known=bool(row.known),
                equipped=bool(row.equipped),
                mastery_rank=row.mastery_rank,
                mastery_progress=row.mastery_progress,
            )
            for row in rows
        ]
