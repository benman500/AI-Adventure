"""Abstract Narrator and stub implementation (AI never writes state)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ai_adventure.engine import EngineOutcome


@dataclass(frozen=True, slots=True)
class Narration:
    """Display-only text produced from a completed engine outcome."""

    text: str


class Narrator(ABC):
    """Port for narration providers (stub, Ollama, OpenAI-compatible later)."""

    @abstractmethod
    def narrate(self, outcome: EngineOutcome) -> Narration:
        """Return flavor text for a completed engine outcome. Must not mutate game state."""


class StubNarrator(Narrator):
    """Template narration so the game works with no AI provider configured."""

    def narrate(self, outcome: EngineOutcome) -> Narration:
        """Build simple prose from the outcome summary and facts."""

        fact_bits = ", ".join(f"{key}={value!r}" for key, value in outcome.facts.items())
        if fact_bits:
            text = f"{outcome.summary} ({fact_bits})"
        else:
            text = outcome.summary
        return Narration(text=text)


def create_narrator(backend: str = "stub") -> Narrator:
    """Factory for narrator backends. Unknown values fall back to stub."""

    if backend == "stub":
        return StubNarrator()
    # Future: ollama, openai_compatible
    return StubNarrator()
