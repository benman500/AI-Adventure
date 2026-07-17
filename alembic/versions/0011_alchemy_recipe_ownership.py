"""Alchemy recipe ownership persistence (mutable state only).

Phase 8: alchemy as a Modifier Framework source via EffectBundles.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011_alchemy_recipe_ownership"
down_revision: Union[str, None] = "0010_spiritual_roots"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names() -> set[str]:
    """Return current SQLite table names."""

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
    return {str(row[0]) for row in rows}


def upgrade() -> None:
    """Add alchemy_recipe_ownership for per-actor awakened recipe state."""

    tables = _table_names()
    if "alchemy_recipe_ownership" not in tables:
        op.create_table(
            "alchemy_recipe_ownership",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("save_id", sa.String(length=36), nullable=False),
            sa.Column("actor_id", sa.String(length=36), nullable=False),
            sa.Column("recipe_id", sa.String(length=128), nullable=False),
            sa.Column("awakened", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("grade_rank", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("awakened_world_day", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["save_id"], ["game_saves.id"]),
            sa.UniqueConstraint(
                "save_id",
                "actor_id",
                "recipe_id",
                name="uq_alchemy_recipe_ownership_save_actor_recipe",
            ),
        )
        op.create_index(
            "ix_alchemy_recipe_ownership_save_id",
            "alchemy_recipe_ownership",
            ["save_id"],
        )
        op.create_index(
            "ix_alchemy_recipe_ownership_actor_id",
            "alchemy_recipe_ownership",
            ["actor_id"],
        )


def downgrade() -> None:
    """Drop alchemy_recipe_ownership."""

    tables = _table_names()
    if "alchemy_recipe_ownership" in tables:
        op.drop_index(
            "ix_alchemy_recipe_ownership_actor_id",
            table_name="alchemy_recipe_ownership",
        )
        op.drop_index(
            "ix_alchemy_recipe_ownership_save_id",
            table_name="alchemy_recipe_ownership",
        )
        op.drop_table("alchemy_recipe_ownership")

