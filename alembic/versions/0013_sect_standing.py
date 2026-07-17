"""Sect institutional standing (Phase 9d).

Revision ID: 0013_sect_standing
Revises: 0012_npc_world_state
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013_sect_standing"
down_revision: Union[str, None] = "0012_npc_world_state"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names() -> set[str]:
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
    return {str(row[0]) for row in rows}


def upgrade() -> None:
    """Add sect_standing for per-save institutional favor with a sect."""

    tables = _table_names()
    if "sect_standing" not in tables:
        op.create_table(
            "sect_standing",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("save_id", sa.String(length=36), nullable=False),
            sa.Column("sect_id", sa.String(length=64), nullable=False),
            sa.Column("standing_score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("updated_world_day", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["save_id"], ["game_saves.id"]),
            sa.UniqueConstraint("save_id", "sect_id", name="uq_sect_standing_save_sect"),
        )
        op.create_index("ix_sect_standing_save_id", "sect_standing", ["save_id"])


def downgrade() -> None:
    """Drop sect_standing."""

    tables = _table_names()
    if "sect_standing" in tables:
        op.drop_index("ix_sect_standing_save_id", table_name="sect_standing")
        op.drop_table("sect_standing")
