"""Shared test helpers for Milestone 2+.

Isolated test databases deliberately use ``Base.metadata.create_all`` so each
test gets a full schema without running Alembic against temp files. Production
startup must use Alembic only (see ``create_app``).
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from ai_adventure.api import create_app
from ai_adventure.config import Settings
from ai_adventure.db import Base, create_db_engine, create_session_factory
from ai_adventure.db import models as _models  # noqa: F401
from ai_adventure.engine.constants import (
    BREAKTHROUGH_PROGRESS_THRESHOLD,
    BREAKTHROUGH_QI_THRESHOLD,
    CULTIVATION_METHOD_ABSORB_QI,
)
from ai_adventure.services import GameAppService

VALID_IDENTITY_ANSWERS = {
    "q_duty_ambition": "stay_for_duty",
    "q_mercy_necessity": "show_mercy",
    "q_tradition_innovation": "keep_custom",
    "q_coin_honor": "recover_coin",
    "q_solitude_fellowship": "walk_alone",
}


def prepare_test_database(database_url: str) -> None:
    """Create the full ORM schema on an isolated test SQLite URL.

    Deliberate test-only path. Do not use for the production ``saves/game.db``.
    """

    settings = Settings(database_url=database_url, narrator_backend="stub")
    engine = create_db_engine(settings)
    Base.metadata.create_all(bind=engine)
    engine.dispose()


def make_test_app(tmp_path: Path, *, filename: str = "http.db") -> FastAPI:
    """Create a FastAPI app backed by an isolated schema-created SQLite file."""

    db_path = tmp_path / filename
    database_url = f"sqlite:///{db_path.as_posix()}"
    prepare_test_database(database_url)
    settings = Settings(database_url=database_url, narrator_backend="stub")
    return create_app(settings)


def make_service(tmp_path: Path) -> GameAppService:
    """Build a GameAppService against an isolated SQLite file."""

    db_path = tmp_path / "test.db"
    settings = Settings(
        app_name="Test Adventure",
        database_url=f"sqlite:///{db_path.as_posix()}",
        narrator_backend="stub",
    )
    # Isolated tests: create_all is intentional (not Alembic).
    engine = create_db_engine(settings)
    Base.metadata.create_all(bind=engine)
    factory = create_session_factory(settings, engine=engine)
    return GameAppService(settings=settings, session_factory=factory)


def create_test_save(
    tmp_path: Path,
    *,
    background_id: str = "hunter",
    character_name: str = "Test Hero",
) -> GameAppService:
    """Create a service with one new save."""

    service = make_service(tmp_path)
    service.create_new_game(
        character_name=character_name,
        background_id=background_id,
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    return service


def advance_to_cultivation_hall(service: GameAppService, save_id: str) -> None:
    """Walk any background through shared pipeline to cultivation hall."""

    scene = service.get_play_scene(save_id)
    bg = scene.background_display_name
    if "Merchant" in bg:
        service.submit_story_action(save_id, "finish_tally")
        service.submit_story_action(save_id, "listen_quietly")
        service.submit_story_action(save_id, "leave_home")
    elif "Alchemist" in bg:
        service.submit_story_action(save_id, "continue_catalogue")
        service.submit_story_action(save_id, "complete_errand")
        service.submit_story_action(save_id, "leave_home")
    else:
        service.submit_story_action(save_id, "check_snares")
        service.submit_story_action(save_id, "report_only")
        service.submit_story_action(save_id, "leave_home")

    service.submit_story_action(save_id, "continue")  # leave home
    service.submit_story_action(save_id, "continue")  # travel 1
    service.submit_story_action(save_id, "travel_together")
    service.submit_story_action(save_id, "continue")  # travel 2
    service.submit_story_action(save_id, "enter")
    service.submit_story_action(save_id, "continue")  # registration
    service.submit_story_action(save_id, "continue")  # exam
    service.submit_story_action(save_id, "continue")  # quarters
    service.submit_story_action(save_id, "continue")  # lesson


def build_breakthrough_readiness(service: GameAppService, save_id: str) -> None:
    """Practice until breakthrough readiness via qi/progress thresholds."""

    advance_to_cultivation_hall(service, save_id)
    scene = service.get_play_scene(save_id)
    while not scene.cultivation["breakthrough_ready"]:
        scene = service.submit_story_action(save_id, CULTIVATION_METHOD_ABSORB_QI)
    assert scene.cultivation["qi_reserve_current"] >= BREAKTHROUGH_QI_THRESHOLD
    assert scene.cultivation["cultivation_progress"] >= BREAKTHROUGH_PROGRESS_THRESHOLD
