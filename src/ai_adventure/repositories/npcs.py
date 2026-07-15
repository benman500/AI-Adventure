"""NPC and sect membership persistence."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_adventure.db.models import NpcRecord, SectMembership


def _utcnow() -> datetime:
    return datetime.now(UTC)


class NpcRepository:
    """Spawn and query authored NPC records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_save(self, save_id: str) -> list[NpcRecord]:
        statement = select(NpcRecord).where(NpcRecord.save_id == save_id)
        return list(self._session.scalars(statement).all())

    def get_by_template(self, save_id: str, template_id: str) -> NpcRecord | None:
        statement = select(NpcRecord).where(
            NpcRecord.save_id == save_id,
            NpcRecord.template_id == template_id,
        )
        return self._session.scalar(statement)

    def spawn_if_absent(
        self,
        *,
        save_id: str,
        template_id: str,
        display_name: str,
        role: str,
        metadata: dict[str, object] | None = None,
    ) -> NpcRecord:
        existing = self.get_by_template(save_id, template_id)
        if existing is not None:
            return existing
        row = NpcRecord(
            save_id=save_id,
            template_id=template_id,
            display_name=display_name,
            role=role,
            metadata_json=json.dumps(metadata or {}, sort_keys=True),
        )
        self._session.add(row)
        self._session.flush()
        return row


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
