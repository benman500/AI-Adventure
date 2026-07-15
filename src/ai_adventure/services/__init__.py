"""Application services: use-case orchestration."""

from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from ai_adventure.config import Settings
from ai_adventure.engine import EngineOutcome, GameEngine
from ai_adventure.narration import Narration, Narrator, create_narrator
from ai_adventure.repositories import MetaRepository


@dataclass(frozen=True, slots=True)
class HomePageModel:
    """View model for the home page (facts from engine; text from narrator)."""

    app_name: str
    outcome: EngineOutcome
    narration: Narration
    schema_marker: str | None


class GameAppService:
    """Coordinates engine → persist → narrate. Never invents mechanical outcomes."""

    def __init__(
        self,
        settings: Settings,
        session_factory: sessionmaker[Session],
        engine: GameEngine | None = None,
        narrator: Narrator | None = None,
    ) -> None:
        """Inject settings, session factory, engine, and narrator."""

        self._settings = settings
        self._session_factory = session_factory
        self._engine = engine or GameEngine()
        self._narrator = narrator or create_narrator(settings.narrator_backend)

    def build_home_page(self) -> HomePageModel:
        """Run engine ping, persist a schema marker, then narrate the outcome."""

        outcome = self._engine.ping()
        narration = self._narrator.narrate(outcome)

        with self._session_factory() as session:
            repo = MetaRepository(session)
            record = repo.upsert("architecture_scaffold", "ok")
            session.commit()
            marker = record.value

        return HomePageModel(
            app_name=self._settings.app_name,
            outcome=outcome,
            narration=narration,
            schema_marker=marker,
        )
