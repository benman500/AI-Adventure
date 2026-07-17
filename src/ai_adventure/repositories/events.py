"""Persistence for event cooldown current state (not history)."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_adventure.db.models import EventCooldown
from ai_adventure.engine.events import CooldownState


class EventCooldownRepository:
    """Load and update mutable event cooldown rows."""

    def __init__(self, session: Session) -> None:
        """Bind to an open SQLAlchemy session."""

        self._session = session

    def list_for_save(self, save_id: str) -> list[EventCooldown]:
        """Return all cooldown rows for a save."""

        statement = select(EventCooldown).where(EventCooldown.save_id == save_id)
        return list(self._session.scalars(statement).all())

    def cooldown_states_for_save(self, save_id: str) -> tuple[CooldownState, ...]:
        """Engine-facing cooldown snapshots."""

        rows = self.list_for_save(save_id)
        return tuple(
            CooldownState(
                event_template_id=row.event_template_id,
                subject_actor_id=row.subject_actor_id,
                last_fired_world_day=row.last_fired_world_day,
                fire_count=row.fire_count,
            )
            for row in rows
        )

    def record_fire(
        self,
        *,
        save_id: str,
        event_template_id: str,
        subject_actor_id: str,
        world_day: int,
    ) -> EventCooldown:
        """Upsert cooldown state after a successful event resolution."""

        statement = select(EventCooldown).where(
            EventCooldown.save_id == save_id,
            EventCooldown.event_template_id == event_template_id,
            EventCooldown.subject_actor_id == subject_actor_id,
        )
        row = self._session.scalar(statement)
        if row is None:
            row = EventCooldown(
                id=str(uuid4()),
                save_id=save_id,
                event_template_id=event_template_id,
                subject_actor_id=subject_actor_id,
                last_fired_world_day=world_day,
                fire_count=1,
            )
            self._session.add(row)
        else:
            row.last_fired_world_day = world_day
            row.fire_count = int(row.fire_count) + 1
            self._session.add(row)
        self._session.flush()
        return row
