"""Engine character creation and background content tests."""

import json
from pathlib import Path

import pytest

from ai_adventure.engine import (
    EngineValidationError,
    GameEngine,
    OutcomeKind,
    clear_background_registry_cache,
    create_character,
    list_backgrounds,
    load_background_registry,
    validate_identity_answers,
)
from tests.conftest_helpers import VALID_IDENTITY_ANSWERS


def test_backgrounds_are_data_driven() -> None:
    """Selectable backgrounds load from JSON without code hardcoding."""

    clear_background_registry_cache()
    backgrounds = list_backgrounds()
    ids = {item.id for item in backgrounds}
    assert ids == {"merchant_family", "alchemists_apprentice", "hunter"}
    assert any(item.display_name == "Merchant Family" for item in backgrounds)


def test_unknown_background_rejected() -> None:
    """Invalid backgrounds fail engine validation."""

    with pytest.raises(EngineValidationError, match="Unknown background"):
        create_character(
            character_name="Li Wei",
            background_id="secret_protagonist",
            identity_answers=VALID_IDENTITY_ANSWERS,
        )


def test_corrupted_background_data_rejected(tmp_path: Path) -> None:
    """Malformed background JSON fails validation."""

    bad = tmp_path / "broken.json"
    bad.write_text("{not json", encoding="utf-8")
    clear_background_registry_cache()
    with pytest.raises(EngineValidationError, match="Corrupted background"):
        load_background_registry(str(tmp_path))
    clear_background_registry_cache()


def test_invalid_background_schema_rejected(tmp_path: Path) -> None:
    """Background missing required seed fields is rejected."""

    path = tmp_path / "incomplete.json"
    path.write_text(json.dumps({"id": "incomplete", "display_name": "X"}), encoding="utf-8")
    clear_background_registry_cache()
    with pytest.raises(EngineValidationError, match="Invalid background"):
        load_background_registry(str(tmp_path))
    clear_background_registry_cache()


def test_identity_answers_validation() -> None:
    """Missing or illegal personality answers are rejected; valid answers pass through."""

    with pytest.raises(EngineValidationError, match="missing"):
        validate_identity_answers({})

    bad = dict(VALID_IDENTITY_ANSWERS)
    bad["q_duty_ambition"] = "not_a_real_answer"
    with pytest.raises(EngineValidationError, match="Invalid answer"):
        validate_identity_answers(bad)

    assert validate_identity_answers(VALID_IDENTITY_ANSWERS) == VALID_IDENTITY_ANSWERS


def test_create_character_ordinary_path_no_boundless() -> None:
    """Creation starts ordinary and never offers Boundless Foundation."""

    engine = GameEngine()
    state, outcome = engine.create_character(
        character_name="  Lan Mei  ",
        background_id="hunter",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    assert state.character_name == "Lan Mei"
    assert state.cultivation_path == "ordinary"
    assert state.background_id == "hunter"
    assert state.identity_answers == VALID_IDENTITY_ANSWERS
    assert "known_contacts" in state.background_history
    assert outcome.kind is OutcomeKind.CHARACTER_CREATED
    assert outcome.facts["boundless_offered"] is False
    assert outcome.facts["cultivation_path"] == "ordinary"


def test_blank_name_rejected() -> None:
    """Empty names are rejected."""

    with pytest.raises(EngineValidationError, match="name"):
        create_character(
            character_name="   ",
            background_id="merchant_family",
            identity_answers=VALID_IDENTITY_ANSWERS,
        )
