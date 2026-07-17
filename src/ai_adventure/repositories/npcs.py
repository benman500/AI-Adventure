"""NPC persistence (legacy npc_records).

Sect membership / standing live in ``repositories.sects``.
"""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_adventure.db.models import NpcRecord


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
