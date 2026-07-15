"""Opening story, cultivation state, NPCs, and sect membership."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_opening_story_cultivation"
down_revision: Union[str, None] = "0002_character_saves"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names() -> set[str]:
    """Return existing table names (SQLite-safe)."""

    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table'")
    ).fetchall()
    return {str(row[0]) for row in rows}


def _column_names(table: str) -> set[str]:
    """Return existing column names for a table."""

    bind = op.get_bind()
    rows = bind.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
    # PRAGMA table_info: cid, name, type, notnull, dflt_value, pk
    return {str(row[1]) for row in rows}


def _index_names() -> set[str]:
    """Return existing index names."""

    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='index' AND name IS NOT NULL")
    ).fetchall()
    return {str(row[0]) for row in rows}


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    """Add a column only when it is not already present."""

    if column.name in _column_names(table):
        return
    op.add_column(table, column)


def upgrade() -> None:
    """Add Milestone 3 story, cultivation, NPC, and sect tables.

    Idempotent: safe to re-run when a prior attempt applied DDL under SQLite
    non-transactional mode but failed to update ``alembic_version``.
    """

    _add_column_if_missing(
        "game_saves",
        sa.Column("world_day", sa.Integer(), nullable=False, server_default="1"),
    )
    _add_column_if_missing(
        "game_saves",
        sa.Column("story_started_at", sa.DateTime(timezone=True), nullable=True),
    )

    _add_column_if_missing(
        "players",
        sa.Column("dao", sa.Integer(), nullable=False, server_default="1"),
    )
    _add_column_if_missing(
        "players",
        sa.Column("path_status", sa.String(length=32), nullable=False, server_default="provisional"),
    )
    _add_column_if_missing(
        "players",
        sa.Column("qi_reserve_current", sa.Integer(), nullable=False, server_default="0"),
    )
    _add_column_if_missing(
        "players",
        sa.Column("qi_reserve_max", sa.Integer(), nullable=False, server_default="10"),
    )
    _add_column_if_missing(
        "players",
        sa.Column("cultivation_progress", sa.Integer(), nullable=False, server_default="0"),
    )
    _add_column_if_missing(
        "players",
        sa.Column("practice_sessions", sa.Integer(), nullable=False, server_default="0"),
    )
    _add_column_if_missing(
        "players",
        sa.Column("anomaly_state", sa.String(length=32), nullable=False, server_default="none"),
    )
    _add_column_if_missing(
        "players",
        sa.Column("path_confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )
    _add_column_if_missing(
        "players",
        sa.Column(
            "breakthrough_readiness",
            sa.String(length=32),
            nullable=False,
            server_default="not_ready",
        ),
    )

    existing_tables = _table_names()
    if "story_progress" not in existing_tables:
        op.create_table(
            "story_progress",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("save_id", sa.String(length=36), sa.ForeignKey("game_saves.id"), nullable=False),
            sa.Column("current_node_id", sa.String(length=128), nullable=False),
            sa.Column("flags_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("save_id", name="uq_story_progress_save_id"),
        )

    if "sect_membership" not in existing_tables:
        op.create_table(
            "sect_membership",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("save_id", sa.String(length=36), sa.ForeignKey("game_saves.id"), nullable=False),
            sa.Column("sect_id", sa.String(length=64), nullable=False),
            sa.Column("rank_id", sa.String(length=64), nullable=False),
            sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("save_id", name="uq_sect_membership_save_id"),
        )

    if "npc_records" not in existing_tables:
        op.create_table(
            "npc_records",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("save_id", sa.String(length=36), sa.ForeignKey("game_saves.id"), nullable=False),
            sa.Column("template_id", sa.String(length=64), nullable=False),
            sa.Column("display_name", sa.String(length=128), nullable=False),
            sa.Column("role", sa.String(length=64), nullable=False),
            sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
        )

    if "ix_npc_records_save_id" not in _index_names():
        op.create_index("ix_npc_records_save_id", "npc_records", ["save_id"])


def downgrade() -> None:
    """Remove Milestone 3 schema (idempotent drops)."""

    if "ix_npc_records_save_id" in _index_names():
        op.drop_index("ix_npc_records_save_id", table_name="npc_records")

    existing_tables = _table_names()
    if "npc_records" in existing_tables:
        op.drop_table("npc_records")
    if "sect_membership" in existing_tables:
        op.drop_table("sect_membership")
    if "story_progress" in existing_tables:
        op.drop_table("story_progress")

    player_cols = _column_names("players") if "players" in existing_tables else set()
    for column in (
        "breakthrough_readiness",
        "path_confirmed_at",
        "anomaly_state",
        "practice_sessions",
        "cultivation_progress",
        "qi_reserve_max",
        "qi_reserve_current",
        "path_status",
        "dao",
    ):
        if column in player_cols:
            op.drop_column("players", column)

    save_cols = _column_names("game_saves") if "game_saves" in existing_tables else set()
    for column in ("story_started_at", "world_day"):
        if column in save_cols:
            op.drop_column("game_saves", column)
