"""FastAPI application factory."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from ai_adventure.api.routes import router
from ai_adventure.config import Settings, get_settings
from ai_adventure.db import create_db_engine, create_session_factory
from ai_adventure.db import models as _models  # noqa: F401 — register models
from ai_adventure.engine.event_devtools import assert_event_catalog_valid
from ai_adventure.engine.locations import assert_location_catalog_valid
from ai_adventure.engine.npcs import assert_npc_catalog_valid
from ai_adventure.engine.sects import assert_sect_catalog_valid
from ai_adventure.services import GameAppService


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI app with wired layers (routes → services → engine → repos).

    Schema must already exist via Alembic migrations (`alembic upgrade head`).
    This factory does **not** call ``Base.metadata.create_all`` so production
    startup cannot silently bypass migration history.
    """

    cfg = settings or get_settings()

    if cfg.validate_event_catalog_on_startup:
        assert_event_catalog_valid()
    if cfg.validate_location_catalog_on_startup:
        assert_location_catalog_valid()
        assert_sect_catalog_valid()
        assert_npc_catalog_valid()
        from ai_adventure.engine.aspirations import assert_aspiration_catalog_valid

        assert_aspiration_catalog_valid()

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

    if cfg.debug:
        from ai_adventure.api.debug_events import debug_router

        app.include_router(debug_router)

        from ai_adventure.api.debug_modifiers import debug_router as debug_modifiers_router

        app.include_router(debug_modifiers_router)

    return app
