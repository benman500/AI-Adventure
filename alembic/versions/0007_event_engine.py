"""Phase 4a: actor_id, world RNG counter, and event cooldowns."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_event_engine"
down_revision: Union[str, None] = "0006_cultivation_breakthroughs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table: str) -> set[str]:
    bind = op.get_bind()
    rows = bind.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
    return {str(row[1]) for row in rows}


def _table_names() -> set[str]:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table'")
    ).fetchall()
    return {str(row[0]) for row in rows}


def _index_names(table: str) -> set[str]:
    bind = op.get_bind()
    rows = bind.execute(sa.text(f"PRAGMA index_list({table})")).fetchall()
    return {str(row[1]) for row in rows}


def upgrade() -> None:
    """Add event-engine persistence primitives and backfill actor_id."""

    save_cols = _column_names("game_saves")
    if "world_rng_counter" not in save_cols:
        op.add_column(
            "game_saves",
            sa.Column(
                "world_rng_counter",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )

    player_cols = _column_names("players")
    if "actor_id" not in player_cols:
        op.add_column(
            "players",
            sa.Column("actor_id", sa.String(length=36), nullable=True),
        )
        op.execute(sa.text("UPDATE players SET actor_id = id WHERE actor_id IS NULL"))
        with op.batch_alter_table("players") as batch_op:
            batch_op.alter_column("actor_id", existing_type=sa.String(length=36), nullable=False)

    indexes = _index_names("players")
    if "uq_players_actor_id" not in indexes and "ix_players_actor_id" not in indexes:
        op.create_index("ix_players_actor_id", "players", ["actor_id"], unique=True)

    tables = _table_names()
    if "event_cooldowns" not in tables:
        op.create_table(
            "event_cooldowns",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("save_id", sa.String(length=36), nullable=False),
            sa.Column("event_template_id", sa.String(length=128), nullable=False),
            sa.Column("subject_actor_id", sa.String(length=36), nullable=False),
            sa.Column("last_fired_world_day", sa.Integer(), nullable=False),
            sa.Column("fire_count", sa.Integer(), nullable=False, server_default="0"),
            sa.ForeignKeyConstraint(["save_id"], ["game_saves.id"]),
            sa.UniqueConstraint(
                "save_id",
                "event_template_id",
                "subject_actor_id",
                name="uq_event_cooldowns_save_template_actor",
            ),
        )
        op.create_index("ix_event_cooldowns_save_id", "event_cooldowns", ["save_id"])


def downgrade() -> None:
    """Remove Phase 4a event-engine columns and table."""

    tables = _table_names()
    if "event_cooldowns" in tables:
        op.drop_table("event_cooldowns")

    player_cols = _column_names("players")
    indexes = _index_names("players")
    if "ix_players_actor_id" in indexes or "uq_players_actor_id" in indexes:
        # Index name from create_index above.
        try:
            op.drop_index("ix_players_actor_id", table_name="players")
        except Exception:  # noqa: BLE001
            pass
    if "actor_id" in player_cols:
        op.drop_column("players", "actor_id")

    save_cols = _column_names("game_saves")
    if "world_rng_counter" in save_cols:
        op.drop_column("game_saves", "world_rng_counter")
