"""Story progress persistence."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_adventure.db.models import StoryProgress


def _utcnow() -> datetime:
    return datetime.now(UTC)


class StoryRepository:
    """Load and save authoritative story position."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_for_save(self, save_id: str) -> StoryProgress | None:
        statement = select(StoryProgress).where(StoryProgress.save_id == save_id)
        return self._session.scalar(statement)

    def create(
        self,
        *,
        save_id: str,
        current_node_id: str,
        flags_json: str = "{}",
    ) -> StoryProgress:
        row = StoryProgress(
            save_id=save_id,
            current_node_id=current_node_id,
            flags_json=flags_json,
            updated_at=_utcnow(),
        )
        self._session.add(row)
        self._session.flush()
        return row

    def update(self, progress: StoryProgress, *, current_node_id: str, flags_json: str) -> StoryProgress:
        progress.current_node_id = current_node_id
        progress.flags_json = flags_json
        progress.updated_at = _utcnow()
        self._session.add(progress)
        return progress
