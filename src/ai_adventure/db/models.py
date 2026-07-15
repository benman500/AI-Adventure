"""ORM models (persistent state only)."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from ai_adventure.db import Base, EntityMixin


class MetaRecord(EntityMixin, Base):
    """Key/value metadata row for smoke persistence and migrations."""

    __tablename__ = "meta_records"

    key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(String(512), nullable=False)
