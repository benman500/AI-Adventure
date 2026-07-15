"""SQLAlchemy declarative base and engine helpers."""

from collections.abc import Generator
from uuid import uuid4

from sqlalchemy import Engine, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from ai_adventure.config import Settings, get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class EntityMixin:
    """Mixin requiring a permanent unique string ID (never reuse deleted IDs)."""

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )


def create_db_engine(settings: Settings | None = None) -> Engine:
    """Create a SQLAlchemy engine for SQLite (sync; MVP default)."""

    cfg = settings or get_settings()
    connect_args = {"check_same_thread": False} if cfg.database_url.startswith("sqlite") else {}
    return create_engine(cfg.database_url, future=True, connect_args=connect_args)


def create_session_factory(
    settings: Settings | None = None,
    engine: Engine | None = None,
) -> sessionmaker[Session]:
    """Return a session factory bound to the configured engine."""

    db_engine = engine or create_db_engine(settings)
    return sessionmaker(bind=db_engine, autoflush=False, autocommit=False, future=True)


def get_session(
    session_factory: sessionmaker[Session] | None = None,
) -> Generator[Session, None, None]:
    """Yield a database session and close it afterward."""

    factory = session_factory or create_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()
