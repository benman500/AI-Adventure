"""Character creation and multi-save schema."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_character_saves"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create game_saves, players, inventory_items, and event_log."""

    op.create_table(
        "game_saves",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("character_name", sa.String(length=128), nullable=False),
        sa.Column("background_id", sa.String(length=64), nullable=False),
        sa.Column("background_display_name", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_played_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_location_id", sa.String(length=128), nullable=False),
        sa.Column("current_location_name", sa.String(length=256), nullable=False),
        sa.Column("playtime_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "players",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("save_id", sa.String(length=36), sa.ForeignKey("game_saves.id"), nullable=False),
        sa.Column("character_name", sa.String(length=128), nullable=False),
        sa.Column("background_id", sa.String(length=64), nullable=False),
        sa.Column("money_copper", sa.Integer(), nullable=False),
        sa.Column("current_location_id", sa.String(length=128), nullable=False),
        sa.Column("current_location_name", sa.String(length=256), nullable=False),
        sa.Column("intro_flavor", sa.Text(), nullable=False),
        sa.Column("cultivation_path", sa.String(length=64), nullable=False),
        sa.Column("realm_id", sa.String(length=64), nullable=False),
        sa.Column("stage_id", sa.String(length=64), nullable=False),
        sa.Column("body", sa.Integer(), nullable=False),
        sa.Column("qi", sa.Integer(), nullable=False),
        sa.Column("soul", sa.Integer(), nullable=False),
        sa.Column("foundation_quality", sa.Integer(), nullable=False),
        sa.Column("identity_answers_json", sa.Text(), nullable=False),
        sa.Column("background_history_json", sa.Text(), nullable=False),
        sa.UniqueConstraint("save_id", name="uq_players_save_id"),
    )

    op.create_table(
        "inventory_items",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("save_id", sa.String(length=36), sa.ForeignKey("game_saves.id"), nullable=False),
        sa.Column("player_id", sa.String(length=36), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("item_code", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=256), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
    )

    op.create_table(
        "event_log",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("save_id", sa.String(length=36), sa.ForeignKey("game_saves.id"), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_event_log_save_id", "event_log", ["save_id"])


def downgrade() -> None:
    """Drop Milestone 2 tables."""

    op.drop_index("ix_event_log_save_id", table_name="event_log")
    op.drop_table("event_log")
    op.drop_table("inventory_items")
    op.drop_table("players")
    op.drop_table("game_saves")
