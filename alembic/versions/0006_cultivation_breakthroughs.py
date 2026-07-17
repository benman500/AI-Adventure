"""Phase 3: breakthrough attempt tracking and last result persistence."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_cultivation_breakthroughs"
down_revision: Union[str, None] = "0005_cultivation_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table: str) -> set[str]:
    bind = op.get_bind()
    rows = bind.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
    return {str(row[1]) for row in rows}


def upgrade() -> None:
    """Add breakthrough attempt counter and last result JSON."""

    cols = _column_names("players")
    if "breakthrough_attempts_current_stage" not in cols:
        op.add_column(
            "players",
            sa.Column(
                "breakthrough_attempts_current_stage",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )
    if "last_breakthrough_result_json" not in cols:
        op.add_column(
            "players",
            sa.Column("last_breakthrough_result_json", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    """Remove Phase 3 breakthrough columns."""

    cols = _column_names("players")
    if "last_breakthrough_result_json" in cols:
        op.drop_column("players", "last_breakthrough_result_json")
    if "breakthrough_attempts_current_stage" in cols:
        op.drop_column("players", "breakthrough_attempts_current_stage")
