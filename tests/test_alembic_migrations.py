"""Regression tests for Alembic migration safety (no create_all bypass)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from ai_adventure.api import create_app
from ai_adventure.config import Settings
from ai_adventure.db import Base
from ai_adventure.db import models as _models  # noqa: F401


def _alembic_config(database_url: str) -> Config:
    """Build Alembic config pointing at an isolated SQLite URL."""

    root = Path(__file__).resolve().parents[1]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def test_create_app_does_not_create_tables(tmp_path: Path) -> None:
    """Production startup must not silently invent schema without Alembic."""

    db_path = tmp_path / "empty.db"
    settings = Settings(database_url=f"sqlite:///{db_path.as_posix()}")
    app = create_app(settings)
    # Force a connection so the SQLite file exists without creating game tables.
    with app.state.session_factory() as session:
        session.execute(text("SELECT 1"))

    assert db_path.exists()
    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    # SQLAlchemy may touch the file; it must not create game tables.
    assert "meta_records" not in tables
    assert "game_saves" not in tables
    assert "players" not in tables


def test_migration_0003_is_idempotent_when_schema_already_present(tmp_path: Path, monkeypatch) -> None:
    """Re-running 0003 after partial SQLite DDL must not fail on duplicate columns."""

    db_path = tmp_path / "partial.db"
    url = f"sqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("AI_ADVENTURE_DATABASE_URL", url)
    # Clear cached settings so Alembic env picks up the temp URL.
    from ai_adventure.config import get_settings

    get_settings.cache_clear()

    engine = create_engine(url, future=True)
    # Simulate: M2 tables created outside Alembic, then M3 DDL partially/fully applied.
    Base.metadata.create_all(bind=engine)
    engine.dispose()

    cfg = _alembic_config(url)
    # History claims we are only at M2 while schema already includes M3 objects.
    command.stamp(cfg, "0002_character_saves")
    command.upgrade(cfg, "head")

    with sqlite3.connect(db_path) as conn:
        version = conn.execute("SELECT version_num FROM alembic_version").fetchone()
        assert version == ("0013_sect_standing",)
        save_cols = {row[1] for row in conn.execute("PRAGMA table_info(game_saves)")}
        assert "world_day" in save_cols
        player_cols = {row[1] for row in conn.execute("PRAGMA table_info(players)")}
        assert "realm_comprehension" in player_cols
        assert "foundation_stability" in player_cols
        assert "last_cultivation_result_json" in player_cols
        assert "cultivation_rng_counter" in player_cols
        assert "breakthrough_attempts_current_stage" in player_cols
        assert "last_breakthrough_result_json" in player_cols
        assert "actor_id" in player_cols
        assert "world_rng_counter" in save_cols
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert "story_progress" in tables
        assert "event_cooldowns" in tables
        assert "location_presence" in tables
        assert "spiritual_root_ownership" in tables

    # Second upgrade must remain a no-op.
    command.upgrade(cfg, "head")
    get_settings.cache_clear()
