"""Save / player / inventory / event persistence."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ai_adventure.db.models import EventLogEntry, GameSave, InventoryItem, Player
from ai_adventure.engine.character_creation import CreatedCharacterState


def _utcnow() -> datetime:
    return datetime.now(UTC)


class SaveRepository:
    """Persist and query game saves (no game rules)."""

    def __init__(self, session: Session) -> None:
        """Bind to an open SQLAlchemy session."""

        self._session = session

    def list_active(self) -> list[GameSave]:
        """Return non-deleted saves ordered by last played (newest first)."""

        statement = (
            select(GameSave)
            .where(GameSave.deleted_at.is_(None))
            .order_by(GameSave.last_played_at.desc())
        )
        return list(self._session.scalars(statement).all())

    def get_by_id(self, save_id: str, *, include_deleted: bool = False) -> GameSave | None:
        """Load a save by id."""

        statement = select(GameSave).where(GameSave.id == save_id)
        save = self._session.scalar(statement)
        if save is None:
            return None
        if save.deleted_at is not None and not include_deleted:
            return None
        return save

    def get_with_player(self, save_id: str) -> GameSave | None:
        """Load an active save with player and inventory eagerly loaded."""

        statement = (
            select(GameSave)
            .where(GameSave.id == save_id, GameSave.deleted_at.is_(None))
            .options(
                selectinload(GameSave.player).selectinload(Player.inventory_items),
                selectinload(GameSave.inventory_items),
                selectinload(GameSave.story_progress),
                selectinload(GameSave.sect_membership),
                selectinload(GameSave.npc_records),
            )
        )
        return self._session.scalar(statement)

    def create_from_character_state(self, state: CreatedCharacterState) -> GameSave:
        """Insert save, player, inventory, and character_created event."""

        now = _utcnow()
        save = GameSave(
            character_name=state.character_name,
            background_id=state.background_id,
            background_display_name=state.background_display_name,
            created_at=now,
            last_played_at=now,
            current_location_id=state.current_location_id,
            current_location_name=state.current_location_name,
            playtime_seconds=0,
            deleted_at=None,
        )
        self._session.add(save)
        self._session.flush()

        player = Player(
            save_id=save.id,
            character_name=state.character_name,
            background_id=state.background_id,
            money_copper=state.money_copper,
            current_location_id=state.current_location_id,
            current_location_name=state.current_location_name,
            intro_flavor=state.intro_flavor,
            cultivation_path=state.cultivation_path,
            realm_id=state.realm_id,
            stage_id=state.stage_id,
            body=state.body,
            qi=state.qi,
            soul=state.soul,
            foundation_quality=state.foundation_quality,
            dao=state.dao,
            identity_answers_json=json.dumps(state.identity_answers, sort_keys=True),
            background_history_json=json.dumps(state.background_history, sort_keys=True),
        )
        self._session.add(player)
        self._session.flush()

        for possession in state.possessions:
            self._session.add(
                InventoryItem(
                    save_id=save.id,
                    player_id=player.id,
                    item_code=possession.item_code,
                    display_name=possession.display_name,
                    quantity=possession.quantity,
                )
            )

        self._session.add(
            EventLogEntry(
                save_id=save.id,
                event_type=state.event_type,
                payload_json=json.dumps(state.event_payload, sort_keys=True),
                created_at=now,
            )
        )
        self._session.flush()
        return save

    def append_event(
        self,
        save_id: str,
        *,
        event_type: str,
        payload: dict[str, object],
    ) -> EventLogEntry:
        """Append one event log row."""

        entry = EventLogEntry(
            save_id=save_id,
            event_type=event_type,
            payload_json=json.dumps(payload, sort_keys=True),
            created_at=_utcnow(),
        )
        self._session.add(entry)
        self._session.flush()
        return entry

    def apply_player_cultivation(self, player: Player, cultivation: object) -> Player:
        """Persist cultivation state from engine CultivationState."""

        player.cultivation_path = cultivation.cultivation_path
        player.path_status = cultivation.path_status
        player.realm_id = cultivation.realm_id
        player.stage_id = cultivation.stage_id
        player.body = cultivation.body
        player.qi = cultivation.qi
        player.soul = cultivation.soul
        player.dao = cultivation.dao
        player.foundation_quality = cultivation.foundation_quality
        player.qi_reserve_current = cultivation.qi_reserve_current
        player.qi_reserve_max = cultivation.qi_reserve_max
        player.cultivation_progress = cultivation.cultivation_progress
        player.practice_sessions = cultivation.practice_sessions
        player.anomaly_state = cultivation.anomaly_state
        player.breakthrough_readiness = cultivation.breakthrough_readiness
        self._session.add(player)
        return player

    def mark_path_confirmed(self, player: Player) -> None:
        """Record permanent path confirmation timestamp."""

        if player.path_confirmed_at is None:
            player.path_confirmed_at = _utcnow()
            self._session.add(player)

    def update_locations(
        self,
        save: GameSave,
        player: Player,
        *,
        location_id: str,
        location_name: str,
    ) -> None:
        """Update current location on save and player."""

        save.current_location_id = location_id
        save.current_location_name = location_name
        player.current_location_id = location_id
        player.current_location_name = location_name
        self._session.add(save)
        self._session.add(player)

    def set_world_day(self, save: GameSave, world_day: int) -> None:
        """Update world day counter."""

        save.world_day = world_day
        self._session.add(save)

    def mark_story_started(self, save: GameSave) -> None:
        """Record when the opening story began."""

        if save.story_started_at is None:
            save.story_started_at = _utcnow()
            self._session.add(save)

    def touch_last_played(self, save: GameSave) -> GameSave:
        """Update last_played_at for a load."""

        save.last_played_at = _utcnow()
        self._session.add(save)
        return save

    def soft_delete(self, save: GameSave) -> GameSave:
        """Mark a save deleted without reusing its id."""

        save.deleted_at = _utcnow()
        self._session.add(save)
        return save


class EventLogRepository:
    """Append-only event log queries."""

    def __init__(self, session: Session) -> None:
        """Bind to an open SQLAlchemy session."""

        self._session = session

    def list_for_save(self, save_id: str) -> list[EventLogEntry]:
        """Return events for a save in chronological order."""

        statement = (
            select(EventLogEntry)
            .where(EventLogEntry.save_id == save_id)
            .order_by(EventLogEntry.created_at.asc())
        )
        return list(self._session.scalars(statement).all())
