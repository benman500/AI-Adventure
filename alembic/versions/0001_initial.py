"""Initial schema: meta_records."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create meta_records table."""

    op.create_table(
        "meta_records",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("value", sa.String(length=512), nullable=False),
        sa.UniqueConstraint("key"),
    )


def downgrade() -> None:
    """Drop meta_records table."""

    op.drop_table("meta_records")
