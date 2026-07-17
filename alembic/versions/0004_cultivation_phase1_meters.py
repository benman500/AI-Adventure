"""Opening cultivation Phase 1 meters: comprehension and foundation stability."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_cultivation_phase1_meters"
down_revision: Union[str, None] = "0003_opening_story_cultivation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table: str) -> set[str]:
    bind = op.get_bind()
    rows = bind.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
    return {str(row[1]) for row in rows}


def upgrade() -> None:
    """Add Phase 1 cultivation meters and normalize stage ids."""

    cols = _column_names("players")
    if "realm_comprehension" not in cols:
        op.add_column(
            "players",
            sa.Column(
                "realm_comprehension",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )
    if "foundation_stability" not in cols:
        op.add_column(
            "players",
            sa.Column(
                "foundation_stability",
                sa.Integer(),
                nullable=False,
                server_default="50",
            ),
        )

    # Legacy Milestone 3 used stage_id "mid"; Phase 1 canonical id is "middle".
    op.execute(sa.text("UPDATE players SET stage_id = 'middle' WHERE stage_id = 'mid'"))


def downgrade() -> None:
    """Remove Phase 1 meters and restore mid stage id."""

    op.execute(sa.text("UPDATE players SET stage_id = 'mid' WHERE stage_id = 'middle'"))
    cols = _column_names("players")
    if "foundation_stability" in cols:
        op.drop_column("players", "foundation_stability")
    if "realm_comprehension" in cols:
        op.drop_column("players", "realm_comprehension")
