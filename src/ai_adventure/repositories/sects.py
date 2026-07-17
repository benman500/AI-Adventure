"""Sect membership and institutional standing persistence."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_adventure.db.models import SectMembership, SectStanding


def _utcnow() -> datetime:
    return datetime.now(UTC)


class SectRepository:
    """Sect membership persistence."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_for_save(self, save_id: str) -> SectMembership | None:
        statement = select(SectMembership).where(SectMembership.save_id == save_id)
        return self._session.scalar(statement)

    def upsert(
        self,
        *,
        save_id: str,
        sect_id: str,
        rank_id: str,
    ) -> SectMembership:
        existing = self.get_for_save(save_id)
        if existing is not None:
            existing.sect_id = sect_id
            existing.rank_id = rank_id
            self._session.add(existing)
            return existing
        row = SectMembership(
            save_id=save_id,
            sect_id=sect_id,
            rank_id=rank_id,
            joined_at=_utcnow(),
        )
        self._session.add(row)
        self._session.flush()
        return row


class SectStandingRepository:
    """Institutional standing persistence (per save + sect)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, save_id: str, sect_id: str) -> SectStanding | None:
        statement = select(SectStanding).where(
            SectStanding.save_id == save_id,
            SectStanding.sect_id == sect_id,
        )
        return self._session.scalar(statement)

    def list_for_save(self, save_id: str) -> list[SectStanding]:
        statement = select(SectStanding).where(SectStanding.save_id == save_id)
        return list(self._session.scalars(statement).all())

    def upsert_score(
        self,
        *,
        save_id: str,
        sect_id: str,
        standing_score: int,
        world_day: int | None,
    ) -> SectStanding:
        existing = self.get(save_id, sect_id)
        if existing is not None:
            existing.standing_score = int(standing_score)
            existing.updated_world_day = world_day
            self._session.add(existing)
            return existing
        row = SectStanding(
            save_id=save_id,
            sect_id=sect_id,
            standing_score=int(standing_score),
            updated_world_day=world_day,
        )
        self._session.add(row)
        self._session.flush()
        return row
