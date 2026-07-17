"""Phase 7: spiritual root ownership (catalog remains authoritative)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010_spiritual_roots"
down_revision: Union[str, None] = "0009_technique_mastery"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names() -> set[str]:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table'")
    ).fetchall()
    return {str(row[0]) for row in rows}


def upgrade() -> None:
    """Add spiritual_root_ownership for per-actor awakened root state."""

    tables = _table_names()
    if "spiritual_root_ownership" not in tables:
        op.create_table(
            "spiritual_root_ownership",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("save_id", sa.String(length=36), nullable=False),
            sa.Column("actor_id", sa.String(length=36), nullable=False),
            sa.Column("root_id", sa.String(length=128), nullable=False),
            sa.Column("awakened", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("grade_rank", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("awakened_world_day", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["save_id"], ["game_saves.id"]),
            sa.UniqueConstraint(
                "save_id",
                "actor_id",
                "root_id",
                name="uq_spiritual_root_ownership_save_actor_root",
            ),
        )
        op.create_index(
            "ix_spiritual_root_ownership_save_id",
            "spiritual_root_ownership",
            ["save_id"],
        )
        op.create_index(
            "ix_spiritual_root_ownership_actor_id",
            "spiritual_root_ownership",
            ["actor_id"],
        )


def downgrade() -> None:
    """Drop spiritual_root_ownership."""

    tables = _table_names()
    if "spiritual_root_ownership" in tables:
        op.drop_index(
            "ix_spiritual_root_ownership_actor_id",
            table_name="spiritual_root_ownership",
        )
        op.drop_index(
            "ix_spiritual_root_ownership_save_id",
            table_name="spiritual_root_ownership",
        )
        op.drop_table("spiritual_root_ownership")
