"""Shared test helpers for Milestone 2."""

from pathlib import Path

from ai_adventure.config import Settings
from ai_adventure.db import Base, create_db_engine, create_session_factory
from ai_adventure.db import models as _models  # noqa: F401
from ai_adventure.services import GameAppService

VALID_IDENTITY_ANSWERS = {
    "q_duty_ambition": "stay_for_duty",
    "q_mercy_necessity": "show_mercy",
    "q_tradition_innovation": "keep_custom",
    "q_coin_honor": "recover_coin",
    "q_solitude_fellowship": "walk_alone",
}


def make_service(tmp_path: Path) -> GameAppService:
    """Build a GameAppService against an isolated SQLite file."""

    db_path = tmp_path / "m2.db"
    settings = Settings(
        app_name="Test Adventure",
        database_url=f"sqlite:///{db_path.as_posix()}",
        narrator_backend="stub",
    )
    engine = create_db_engine(settings)
    Base.metadata.create_all(bind=engine)
    factory = create_session_factory(settings, engine=engine)
    return GameAppService(settings=settings, session_factory=factory)
