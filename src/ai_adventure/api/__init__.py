"""FastAPI application factory."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from ai_adventure.api.routes import router
from ai_adventure.config import Settings, get_settings
from ai_adventure.db import create_db_engine, create_session_factory
from ai_adventure.db import models as _models  # noqa: F401 — register models
from ai_adventure.services import GameAppService


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI app with wired layers (routes → services → engine → repos).

    Schema must already exist via Alembic migrations (`alembic upgrade head`).
    This factory does **not** call ``Base.metadata.create_all`` so production
    startup cannot silently bypass migration history.
    """

    cfg = settings or get_settings()
    db_engine = create_db_engine(cfg)
    session_factory = create_session_factory(cfg, engine=db_engine)
    game_service = GameAppService(settings=cfg, session_factory=session_factory)

    app = FastAPI(title=cfg.app_name, debug=cfg.debug)
    app.state.settings = cfg
    app.state.session_factory = session_factory
    app.state.game_app_service = game_service

    static_dir = Path(__file__).resolve().parent.parent / "presentation" / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    app.include_router(router)
    return app
