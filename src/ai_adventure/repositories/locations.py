"""Persistence for per-save location presence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_adventure.db.models import LocationPresence
from ai_adventure.engine.locations import compute_presence_upsert, require_known_location


class LocationPresenceRepository:
    """Load and upsert location presence rows for a save."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, save_id: str, location_id: str) -> LocationPresence | None:
        """Return presence for one location, if any."""

        stmt = select(LocationPresence).where(
            LocationPresence.save_id == save_id,
            LocationPresence.location_id == location_id,
        )
        return self._session.scalar(stmt)

    def list_for_save(self, save_id: str) -> list[LocationPresence]:
        """Return all presence rows for a save."""

        stmt = select(LocationPresence).where(LocationPresence.save_id == save_id)
        return list(self._session.scalars(stmt).all())

    def record_visit(self, save_id: str, location_id: str, world_day: int) -> LocationPresence:
        """Validate catalog id and upsert visit / discovery counters."""

        require_known_location(location_id)
        existing = self.get(save_id, location_id)
        upsert = compute_presence_upsert(
            location_id=location_id,
            world_day=world_day,
            existing_visit_count=None if existing is None else int(existing.visit_count),
            existing_discovered_world_day=(
                None if existing is None else int(existing.discovered_world_day)
            ),
            existing_first_visited_world_day=(
                None if existing is None else int(existing.first_visited_world_day)
            ),
        )

        if existing is None:
            row = LocationPresence(
                save_id=save_id,
                location_id=upsert.location_id,
                discovered_world_day=upsert.discovered_world_day,
                first_visited_world_day=upsert.first_visited_world_day,
                last_visited_world_day=upsert.last_visited_world_day,
                visit_count=upsert.visit_count,
            )
            self._session.add(row)
            return row

        existing.discovered_world_day = upsert.discovered_world_day
        existing.first_visited_world_day = upsert.first_visited_world_day
        existing.last_visited_world_day = upsert.last_visited_world_day
        existing.visit_count = upsert.visit_count
        self._session.add(existing)
        return existing
