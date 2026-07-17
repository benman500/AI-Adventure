"""NPC world-state persistence (mutable state only)."""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_adventure.db.models import NpcWorldState
from ai_adventure.engine.npcs import NpcWorldStateRecord


class NpcWorldStateRepository:
    """Load/save ``npc_world_state`` rows (no game rules)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_for_save(self, save_id: str) -> list[NpcWorldState]:
        """Return all NPC world-state rows for a save."""

        statement = select(NpcWorldState).where(NpcWorldState.save_id == save_id)
        return list(self._session.scalars(statement).all())

    def list_at_location(self, save_id: str, location_id: str) -> list[NpcWorldState]:
        """Return active discovered NPCs at a location."""

        statement = select(NpcWorldState).where(
            NpcWorldState.save_id == save_id,
            NpcWorldState.current_location_id == location_id,
            NpcWorldState.status == "active",
            NpcWorldState.discovered == 1,
        )
        return list(self._session.scalars(statement).all())

    def get_by_npc_id(self, save_id: str, npc_id: str) -> NpcWorldState | None:
        """Return one row by catalog npc_id."""

        statement = select(NpcWorldState).where(
            NpcWorldState.save_id == save_id,
            NpcWorldState.npc_id == npc_id,
        )
        return self._session.scalar(statement)

    def ensure_spawned(
        self,
        *,
        save_id: str,
        npc_id: str,
        current_location_id: str,
        discovered: bool = True,
    ) -> NpcWorldState:
        """Create world state if absent; leave existing rows unchanged."""

        existing = self.get_by_npc_id(save_id, npc_id)
        if existing is not None:
            if discovered and not existing.discovered:
                existing.discovered = 1
                self._session.add(existing)
            return existing
        row = NpcWorldState(
            save_id=save_id,
            npc_id=npc_id,
            current_location_id=current_location_id,
            status="active",
            discovered=1 if discovered else 0,
            met=0,
            relationship_score=0,
            sect_id_override=None,
            state_flags_json="{}",
            last_interaction_world_day=None,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def apply_interaction(
        self,
        row: NpcWorldState,
        *,
        relationship_score: int,
        met: bool,
        world_day: int,
    ) -> NpcWorldState:
        """Persist interaction outcomes onto an existing row."""

        row.relationship_score = int(relationship_score)
        row.met = 1 if met else int(row.met)
        row.last_interaction_world_day = int(world_day)
        self._session.add(row)
        self._session.flush()
        return row

    @staticmethod
    def to_engine_record(row: NpcWorldState) -> NpcWorldStateRecord:
        """Map ORM row to engine DTO."""

        try:
            flags_raw = json.loads(row.state_flags_json or "{}")
        except json.JSONDecodeError:
            flags_raw = {}
        flags = {
            str(key): bool(value)
            for key, value in flags_raw.items()
            if isinstance(value, (bool, int))
        }
        return NpcWorldStateRecord(
            actor_id=str(row.id),
            npc_id=str(row.npc_id),
            current_location_id=str(row.current_location_id),
            status=row.status,  # type: ignore[arg-type]
            discovered=bool(row.discovered),
            met=bool(row.met),
            relationship_score=int(row.relationship_score),
            sect_id_override=row.sect_id_override,
            state_flags=flags,
            last_interaction_world_day=(
                int(row.last_interaction_world_day)
                if row.last_interaction_world_day is not None
                else None
            ),
        )
