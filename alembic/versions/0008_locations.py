"""Phase 5a: per-save location presence (mutable discovery / visit state)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_locations"
down_revision: Union[str, None] = "0007_event_engine"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names() -> set[str]:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table'")
    ).fetchall()
    return {str(row[0]) for row in rows}


def upgrade() -> None:
    """Add location_presence for catalog-backed visit / discovery tracking."""

    tables = _table_names()
    if "location_presence" not in tables:
        op.create_table(
            "location_presence",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("save_id", sa.String(length=36), nullable=False),
            sa.Column("location_id", sa.String(length=128), nullable=False),
            sa.Column("discovered_world_day", sa.Integer(), nullable=False),
            sa.Column("first_visited_world_day", sa.Integer(), nullable=False),
            sa.Column("last_visited_world_day", sa.Integer(), nullable=False),
            sa.Column("visit_count", sa.Integer(), nullable=False, server_default="0"),
            sa.ForeignKeyConstraint(["save_id"], ["game_saves.id"]),
            sa.UniqueConstraint(
                "save_id",
                "location_id",
                name="uq_location_presence_save_location",
            ),
        )
        op.create_index(
            "ix_location_presence_save_id",
            "location_presence",
            ["save_id"],
        )


def downgrade() -> None:
    """Drop location_presence."""

    tables = _table_names()
    if "location_presence" in tables:
        op.drop_index("ix_location_presence_save_id", table_name="location_presence")
        op.drop_table("location_presence")
