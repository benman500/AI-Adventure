"""Engine unit tests."""

from ai_adventure.engine import GameEngine, OutcomeKind


def test_engine_ping_is_authoritative() -> None:
    """Engine produces completed outcomes; does not delegate mechanics to AI."""

    outcome = GameEngine().ping()
    assert outcome.kind is OutcomeKind.STATUS
    assert outcome.facts["authoritative"] is True
    assert outcome.facts["ai_decides_mechanics"] is False
