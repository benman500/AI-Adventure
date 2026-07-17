"""Phase 6c: technique mastery mutable state (catalog remains authoritative)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_technique_mastery"
down_revision: Union[str, None] = "0008_locations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names() -> set[str]:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table'")
    ).fetchall()
    return {str(row[0]) for row in rows}


def upgrade() -> None:
    """Add technique_mastery for per-actor known / equipped / rank state."""

    tables = _table_names()
    if "technique_mastery" not in tables:
        op.create_table(
            "technique_mastery",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("save_id", sa.String(length=36), nullable=False),
            sa.Column("actor_id", sa.String(length=36), nullable=False),
            sa.Column("technique_id", sa.String(length=128), nullable=False),
            sa.Column("known", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("equipped", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("mastery_rank", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("mastery_progress", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("learned_world_day", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["save_id"], ["game_saves.id"]),
            sa.UniqueConstraint(
                "save_id",
                "actor_id",
                "technique_id",
                name="uq_technique_mastery_save_actor_technique",
            ),
        )
        op.create_index(
            "ix_technique_mastery_save_id",
            "technique_mastery",
            ["save_id"],
        )
        op.create_index(
            "ix_technique_mastery_actor_id",
            "technique_mastery",
            ["actor_id"],
        )


def downgrade() -> None:
    """Drop technique_mastery."""

    tables = _table_names()
    if "technique_mastery" in tables:
        op.drop_index("ix_technique_mastery_actor_id", table_name="technique_mastery")
        op.drop_index("ix_technique_mastery_save_id", table_name="technique_mastery")
        op.drop_table("technique_mastery")
