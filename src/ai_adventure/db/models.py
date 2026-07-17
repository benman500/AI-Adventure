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
    world_day: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    world_rng_counter: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    story_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    player: Mapped["Player"] = relationship(back_populates="save", uselist=False)
    inventory_items: Mapped[list["InventoryItem"]] = relationship(back_populates="save")
    events: Mapped[list["EventLogEntry"]] = relationship(back_populates="save")
    event_cooldowns: Mapped[list["EventCooldown"]] = relationship(back_populates="save")
    location_presence: Mapped[list["LocationPresence"]] = relationship(back_populates="save")
    technique_mastery: Mapped[list["TechniqueMastery"]] = relationship(back_populates="save")
    spiritual_root_ownership: Mapped[list["SpiritualRootOwnership"]] = relationship(
        back_populates="save"
    )
    alchemy_recipe_ownership: Mapped[list["AlchemyRecipeOwnership"]] = relationship(
        back_populates="save"
    )
    story_progress: Mapped["StoryProgress | None"] = relationship(
        back_populates="save",
        uselist=False,
    )
    sect_membership: Mapped["SectMembership | None"] = relationship(
        back_populates="save",
        uselist=False,
    )
    sect_standing: Mapped[list["SectStanding"]] = relationship(back_populates="save")
    npc_records: Mapped[list["NpcRecord"]] = relationship(back_populates="save")
    npc_world_state: Mapped[list["NpcWorldState"]] = relationship(back_populates="save")


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
    actor_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
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
    dao: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    path_status: Mapped[str] = mapped_column(String(32), nullable=False, default="provisional")
    qi_reserve_current: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    qi_reserve_max: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    cultivation_progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    realm_comprehension: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    foundation_stability: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    practice_sessions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cultivation_rng_counter: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_cultivation_result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    breakthrough_attempts_current_stage: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    last_breakthrough_result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    anomaly_state: Mapped[str] = mapped_column(String(32), nullable=False, default="none")
    breakthrough_readiness: Mapped[str] = mapped_column(String(32), nullable=False, default="not_ready")
    path_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    identity_answers_json: Mapped[str] = mapped_column(Text, nullable=False)
    background_history_json: Mapped[str] = mapped_column(Text, nullable=False)

    save: Mapped[GameSave] = relationship(back_populates="player")
    inventory_items: Mapped[list["InventoryItem"]] = relationship(back_populates="player")


class EventCooldown(EntityMixin, Base):
    """Current cooldown / fire-count state for one event template per subject.

    Immutable history belongs in ``event_log``. This table is mutable current
    state only (last fire day + cumulative fire count for gates).
    """

    __tablename__ = "event_cooldowns"
    __table_args__ = (
        UniqueConstraint(
            "save_id",
            "event_template_id",
            "subject_actor_id",
            name="uq_event_cooldowns_save_template_actor",
        ),
    )

    save_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("game_saves.id"),
        nullable=False,
        index=True,
    )
    event_template_id: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_actor_id: Mapped[str] = mapped_column(String(36), nullable=False)
    last_fired_world_day: Mapped[int] = mapped_column(Integer, nullable=False)
    fire_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    save: Mapped[GameSave] = relationship(back_populates="event_cooldowns")


class LocationPresence(EntityMixin, Base):
    """Per-save mutable discovery / visit state for a catalog location.

    The location catalog remains authoritative for existence and display names.
    """

    __tablename__ = "location_presence"
    __table_args__ = (
        UniqueConstraint(
            "save_id",
            "location_id",
            name="uq_location_presence_save_location",
        ),
    )

    save_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("game_saves.id"),
        nullable=False,
        index=True,
    )
    location_id: Mapped[str] = mapped_column(String(128), nullable=False)
    discovered_world_day: Mapped[int] = mapped_column(Integer, nullable=False)
    first_visited_world_day: Mapped[int] = mapped_column(Integer, nullable=False)
    last_visited_world_day: Mapped[int] = mapped_column(Integer, nullable=False)
    visit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    save: Mapped[GameSave] = relationship(back_populates="location_presence")


class TechniqueMastery(EntityMixin, Base):
    """Per-actor mutable technique learning / equip / rank state.

    Technique catalog remains authoritative for definitions and effect bundles.
    """

    __tablename__ = "technique_mastery"
    __table_args__ = (
        UniqueConstraint(
            "save_id",
            "actor_id",
            "technique_id",
            name="uq_technique_mastery_save_actor_technique",
        ),
    )

    save_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("game_saves.id"),
        nullable=False,
        index=True,
    )
    actor_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    technique_id: Mapped[str] = mapped_column(String(128), nullable=False)
    known: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    equipped: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    mastery_rank: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    mastery_progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    learned_world_day: Mapped[int] = mapped_column(Integer, nullable=False)

    save: Mapped[GameSave] = relationship(back_populates="technique_mastery")


class SpiritualRootOwnership(EntityMixin, Base):
    """Per-actor mutable spiritual root awakened / grade state.

    Spiritual root catalog remains authoritative for definitions and effect bundles.
    """

    __tablename__ = "spiritual_root_ownership"
    __table_args__ = (
        UniqueConstraint(
            "save_id",
            "actor_id",
            "root_id",
            name="uq_spiritual_root_ownership_save_actor_root",
        ),
    )

    save_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("game_saves.id"),
        nullable=False,
        index=True,
    )
    actor_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    root_id: Mapped[str] = mapped_column(String(128), nullable=False)
    awakened: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    grade_rank: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    awakened_world_day: Mapped[int] = mapped_column(Integer, nullable=False)

    save: Mapped[GameSave] = relationship(back_populates="spiritual_root_ownership")


class AlchemyRecipeOwnership(EntityMixin, Base):
    """Per-actor mutable awakened alchemy recipe / grade state.

    Alchemy recipe catalog remains authoritative for definitions and effect
    bundles.
    """

    __tablename__ = "alchemy_recipe_ownership"
    __table_args__ = (
        UniqueConstraint(
            "save_id",
            "actor_id",
            "recipe_id",
            name="uq_alchemy_recipe_ownership_save_actor_recipe",
        ),
    )

    save_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("game_saves.id"),
        nullable=False,
        index=True,
    )
    actor_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    recipe_id: Mapped[str] = mapped_column(String(128), nullable=False)
    awakened: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    grade_rank: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    awakened_world_day: Mapped[int] = mapped_column(Integer, nullable=False)

    save: Mapped[GameSave] = relationship(back_populates="alchemy_recipe_ownership")


class StoryProgress(EntityMixin, Base):
    """Authoritative story position for a save."""

    __tablename__ = "story_progress"
    __table_args__ = (UniqueConstraint("save_id", name="uq_story_progress_save_id"),)

    save_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("game_saves.id"),
        nullable=False,
    )
    current_node_id: Mapped[str] = mapped_column(String(128), nullable=False)
    flags_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    save: Mapped[GameSave] = relationship(back_populates="story_progress")


class SectMembership(EntityMixin, Base):
    """Player sect affiliation for a save."""

    __tablename__ = "sect_membership"
    __table_args__ = (UniqueConstraint("save_id", name="uq_sect_membership_save_id"),)

    save_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("game_saves.id"),
        nullable=False,
    )
    sect_id: Mapped[str] = mapped_column(String(64), nullable=False)
    rank_id: Mapped[str] = mapped_column(String(64), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    save: Mapped[GameSave] = relationship(back_populates="sect_membership")


class SectStanding(EntityMixin, Base):
    """Institutional standing between a save's player and one catalog sect."""

    __tablename__ = "sect_standing"
    __table_args__ = (
        UniqueConstraint("save_id", "sect_id", name="uq_sect_standing_save_sect"),
    )

    save_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("game_saves.id"),
        nullable=False,
        index=True,
    )
    sect_id: Mapped[str] = mapped_column(String(64), nullable=False)
    standing_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_world_day: Mapped[int | None] = mapped_column(Integer, nullable=True)

    save: Mapped[GameSave] = relationship(back_populates="sect_standing")


class NpcRecord(EntityMixin, Base):
    """Legacy spawned NPC row (superseded by ``NpcWorldState``).

    Kept for migration compatibility. New code must not write this table.
    """

    __tablename__ = "npc_records"

    save_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("game_saves.id"),
        nullable=False,
        index=True,
    )
    template_id: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    save: Mapped[GameSave] = relationship(back_populates="npc_records")


class NpcWorldState(EntityMixin, Base):
    """Per-save mutable NPC world state (catalog remains identity authority).

    Row ``id`` is the opaque ``actor_id`` for this NPC instance in the save.
    """

    __tablename__ = "npc_world_state"
    __table_args__ = (
        UniqueConstraint(
            "save_id",
            "npc_id",
            name="uq_npc_world_state_save_npc",
        ),
    )

    save_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("game_saves.id"),
        nullable=False,
        index=True,
    )
    npc_id: Mapped[str] = mapped_column(String(128), nullable=False)
    current_location_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    discovered: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    met: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    relationship_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sect_id_override: Mapped[str | None] = mapped_column(String(64), nullable=True)
    state_flags_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    last_interaction_world_day: Mapped[int | None] = mapped_column(Integer, nullable=True)

    save: Mapped[GameSave] = relationship(back_populates="npc_world_state")


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
