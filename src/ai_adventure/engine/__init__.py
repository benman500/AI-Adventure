"""Game engine: authoritative rules and structured outcomes (no HTTP, no AI)."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class OutcomeKind(StrEnum):
    """Kinds of completed engine outcomes (narrator input only)."""

    SYSTEM = "system"
    STATUS = "status"


@dataclass(frozen=True, slots=True)
class EngineOutcome:
    """A completed mechanical result. Narrators may describe this; they must not invent one."""

    kind: OutcomeKind
    summary: str
    facts: dict[str, Any] = field(default_factory=dict)


class GameEngine:
    """Authoritative game rules host.

    Cultivation, combat, economy, and time systems plug in here later.
    This scaffold only exposes health-check style outcomes for wiring tests.
    """

    def ping(self) -> EngineOutcome:
        """Return a deterministic status outcome proving the engine layer is active."""

        return EngineOutcome(
            kind=OutcomeKind.STATUS,
            summary="Engine ready.",
            facts={"authoritative": True, "ai_decides_mechanics": False},
        )
