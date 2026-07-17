"""NPC world state persistence (Phase 9b).

Revision ID: 0012_npc_world_state
Revises: 0011_alchemy_recipe_ownership
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012_npc_world_state"
down_revision: Union[str, None] = "0011_alchemy_recipe_ownership"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names() -> set[str]:
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
    return {str(row[0]) for row in rows}


def upgrade() -> None:
    """Add npc_world_state for catalog-backed mutable NPC instances."""

    tables = _table_names()
    if "npc_world_state" not in tables:
        op.create_table(
            "npc_world_state",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("save_id", sa.String(length=36), nullable=False),
            sa.Column("npc_id", sa.String(length=128), nullable=False),
            sa.Column("current_location_id", sa.String(length=128), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
            sa.Column("discovered", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("met", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("relationship_score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("sect_id_override", sa.String(length=64), nullable=True),
            sa.Column("state_flags_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("last_interaction_world_day", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["save_id"], ["game_saves.id"]),
            sa.UniqueConstraint("save_id", "npc_id", name="uq_npc_world_state_save_npc"),
        )
        op.create_index("ix_npc_world_state_save_id", "npc_world_state", ["save_id"])


def downgrade() -> None:
    """Drop npc_world_state."""

    tables = _table_names()
    if "npc_world_state" in tables:
        op.drop_index("ix_npc_world_state_save_id", table_name="npc_world_state")
        op.drop_table("npc_world_state")
