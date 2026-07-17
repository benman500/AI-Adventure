"""Phase 2: last cultivation result persistence and RNG counter."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_cultivation_sessions"
down_revision: Union[str, None] = "0004_cultivation_phase1_meters"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table: str) -> set[str]:
    bind = op.get_bind()
    rows = bind.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
    return {str(row[1]) for row in rows}


def upgrade() -> None:
    """Add cultivation session result + deterministic RNG counter."""

    cols = _column_names("players")
    if "last_cultivation_result_json" not in cols:
        op.add_column(
            "players",
            sa.Column("last_cultivation_result_json", sa.Text(), nullable=True),
        )
    if "cultivation_rng_counter" not in cols:
        op.add_column(
            "players",
            sa.Column(
                "cultivation_rng_counter",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )
    # Normalize legacy realm id if any saves used qi_condensation.
    op.execute(
        sa.text(
            "UPDATE players SET realm_id = 'qi_gathering' WHERE realm_id = 'qi_condensation'"
        )
    )


def downgrade() -> None:
    """Remove Phase 2 session columns."""

    cols = _column_names("players")
    if "cultivation_rng_counter" in cols:
        op.drop_column("players", "cultivation_rng_counter")
    if "last_cultivation_result_json" in cols:
        op.drop_column("players", "last_cultivation_result_json")
