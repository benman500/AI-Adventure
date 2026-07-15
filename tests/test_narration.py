"""Narrator unit tests."""

from ai_adventure.engine import EngineOutcome, OutcomeKind
from ai_adventure.narration import StubNarrator, create_narrator


def test_stub_narrator_describes_outcome_only() -> None:
    """Narrator returns text from a completed outcome and does not invent mechanics."""

    outcome = EngineOutcome(
        kind=OutcomeKind.SYSTEM,
        summary="A door opens.",
        facts={"room": "gate"},
    )
    narration = StubNarrator().narrate(outcome)
    assert "A door opens." in narration.text
    assert "gate" in narration.text


def test_create_narrator_defaults_to_stub() -> None:
    """Unknown backends fall back to stub so mechanics work offline."""

    narrator = create_narrator("unknown-provider")
    assert isinstance(narrator, StubNarrator)
