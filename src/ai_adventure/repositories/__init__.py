"""Repository layer: persistence only, no game rules."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_adventure.db.models import MetaRecord
from ai_adventure.repositories.events import EventCooldownRepository
from ai_adventure.repositories.locations import LocationPresenceRepository
from ai_adventure.repositories.npcs import NpcRepository, SectRepository
from ai_adventure.repositories.saves import EventLogRepository, SaveRepository
from ai_adventure.repositories.story import StoryRepository
from ai_adventure.repositories.spiritual_roots import SpiritualRootOwnershipRepository
from ai_adventure.repositories.alchemy import AlchemyRecipeOwnershipRepository
from ai_adventure.repositories.techniques import TechniqueMasteryRepository
from ai_adventure.repositories.npc_world_state import NpcWorldStateRepository

__all__ = [
    "EventCooldownRepository",
    "EventLogRepository",
    "LocationPresenceRepository",
    "MetaRepository",
    "NpcRepository",
    "NpcWorldStateRepository",
    "SaveRepository",
    "SectRepository",
    "SpiritualRootOwnershipRepository",
    "AlchemyRecipeOwnershipRepository",
    "StoryRepository",
    "TechniqueMasteryRepository",
]


class MetaRepository:
    """Load/save MetaRecord rows by permanent unique ID or key."""

    def __init__(self, session: Session) -> None:
        """Bind this repository to an open SQLAlchemy session."""

        self._session = session

    def get_by_key(self, key: str) -> MetaRecord | None:
        """Return a meta record by unique key, if present."""

        statement = select(MetaRecord).where(MetaRecord.key == key)
        return self._session.scalar(statement)

    def upsert(self, key: str, value: str) -> MetaRecord:
        """Create or update a meta record and return it (caller commits)."""

        existing = self.get_by_key(key)
        if existing is None:
            record = MetaRecord(key=key, value=value)
            self._session.add(record)
            return record
        existing.value = value
        return existing
