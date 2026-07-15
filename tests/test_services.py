"""Repository and service integration tests."""

from pathlib import Path

from ai_adventure.config import Settings
from ai_adventure.db import Base, create_db_engine, create_session_factory
from ai_adventure.db import models as _models  # noqa: F401
from ai_adventure.repositories import MetaRepository
from ai_adventure.services import GameAppService


def test_meta_repository_upsert(tmp_path: Path) -> None:
    """Repositories persist by unique key without encoding game rules."""

    db_path = tmp_path / "test.db"
    settings = Settings(database_url=f"sqlite:///{db_path.as_posix()}")
    engine = create_db_engine(settings)
    Base.metadata.create_all(bind=engine)
    factory = create_session_factory(settings, engine=engine)

    with factory() as session:
        repo = MetaRepository(session)
        repo.upsert("k", "v1")
        session.commit()

    with factory() as session:
        repo = MetaRepository(session)
        found = repo.get_by_key("k")
        assert found is not None
        assert found.value == "v1"
        assert found.id


def test_game_app_service_narrates_after_engine(tmp_path: Path) -> None:
    """Service runs engine first, then narrator; both are reflected in the view model."""

    db_path = tmp_path / "svc.db"
    settings = Settings(
        app_name="Test Adventure",
        database_url=f"sqlite:///{db_path.as_posix()}",
        narrator_backend="stub",
    )
    engine = create_db_engine(settings)
    Base.metadata.create_all(bind=engine)
    factory = create_session_factory(settings, engine=engine)
    service = GameAppService(settings=settings, session_factory=factory)

    model = service.build_home_page()
    assert model.app_name == "Test Adventure"
    assert model.outcome.facts["authoritative"] is True
    assert "Engine ready" in model.narration.text
    assert model.schema_marker == "ok"
