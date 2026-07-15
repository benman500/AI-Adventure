"""ORM models (persistent state only)."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ai_adventure.db import Base, EntityMixin


class MetaRecord(EntityMixin, Base):
    """Key/value metadata row for smoke persistence and migrations."""

    __tablename__ = "meta_records"

    key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(String(512), nullable=False)


class GameSave(EntityMixin, Base):
    """One player world save (eventually the entire persistent world for a run)."""

    __tablename__ = "game_saves"

    character_name: Mapped[str] = mapped_column(String(128), nullable=False)
    background_id: Mapped[str] = mapped_column(String(64), nullable=False)
    background_display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_location_id: Mapped[str] = mapped_column(String(128), nullable=False)
    current_location_name: Mapped[str] = mapped_column(String(256), nullable=False)
    playtime_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    player: Mapped["Player"] = relationship(back_populates="save", uselist=False)
    inventory_items: Mapped[list["InventoryItem"]] = relationship(back_populates="save")
    events: Mapped[list["EventLogEntry"]] = relationship(back_populates="save")


class Player(EntityMixin, Base):
    """Player character record belonging to exactly one save."""

    __tablename__ = "players"
    __table_args__ = (UniqueConstraint("save_id", name="uq_players_save_id"),)

    save_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("game_saves.id"),
        nullable=False,
    )
    character_name: Mapped[str] = mapped_column(String(128), nullable=False)
    background_id: Mapped[str] = mapped_column(String(64), nullable=False)
    money_copper: Mapped[int] = mapped_column(Integer, nullable=False)
    current_location_id: Mapped[str] = mapped_column(String(128), nullable=False)
    current_location_name: Mapped[str] = mapped_column(String(256), nullable=False)
    intro_flavor: Mapped[str] = mapped_column(Text, nullable=False)
    cultivation_path: Mapped[str] = mapped_column(String(64), nullable=False)
    realm_id: Mapped[str] = mapped_column(String(64), nullable=False)
    stage_id: Mapped[str] = mapped_column(String(64), nullable=False)
    body: Mapped[int] = mapped_column(Integer, nullable=False)
    qi: Mapped[int] = mapped_column(Integer, nullable=False)
    soul: Mapped[int] = mapped_column(Integer, nullable=False)
    foundation_quality: Mapped[int] = mapped_column(Integer, nullable=False)
    identity_answers_json: Mapped[str] = mapped_column(Text, nullable=False)
    background_history_json: Mapped[str] = mapped_column(Text, nullable=False)

    save: Mapped[GameSave] = relationship(back_populates="player")
    inventory_items: Mapped[list["InventoryItem"]] = relationship(back_populates="player")


class InventoryItem(EntityMixin, Base):
    """An inventory stack belonging to a save/player."""

    __tablename__ = "inventory_items"

    save_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("game_saves.id"),
        nullable=False,
    )
    player_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("players.id"),
        nullable=False,
    )
    item_code: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    save: Mapped[GameSave] = relationship(back_populates="inventory_items")
    player: Mapped[Player] = relationship(back_populates="inventory_items")


class EventLogEntry(EntityMixin, Base):
    """Append-only durable event for a save."""

    __tablename__ = "event_log"

    save_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("game_saves.id"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    save: Mapped[GameSave] = relationship(back_populates="events")
