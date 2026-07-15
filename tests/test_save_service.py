"""Save service and repository persistence tests."""

from pathlib import Path

import pytest

from ai_adventure.db import create_db_engine, create_session_factory
from ai_adventure.engine import EngineValidationError
from ai_adventure.engine.constants import DELETE_CONFIRMATION_VALUE, EVENT_TYPE_CHARACTER_CREATED
from ai_adventure.repositories import EventLogRepository, SaveRepository
from tests.conftest_helpers import VALID_IDENTITY_ANSWERS, make_service


def test_new_game_persists_save_player_inventory_and_event(tmp_path: Path) -> None:
    """Creating a game writes save metadata, player, inventory, and event log."""

    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Shen Yue",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    assert loaded.character_name == "Shen Yue"
    assert loaded.background_id == "merchant_family"
    assert loaded.cultivation_path == "ordinary"
    assert loaded.money_copper == 120
    assert loaded.inventory
    assert loaded.identity_answers == VALID_IDENTITY_ANSWERS

    events = service.list_events_for_save(loaded.save_id)
    assert len(events) == 1
    assert events[0]["event_type"] == EVENT_TYPE_CHARACTER_CREATED

    listed = service.list_saves()
    assert len(listed) == 1
    assert listed[0].character_name == "Shen Yue"
    assert listed[0].background_display_name == "Merchant Family"


def test_load_save_updates_last_played(tmp_path: Path) -> None:
    """Load returns persisted state and refreshes last_played_at."""

    service = make_service(tmp_path)
    created = service.create_new_game(
        character_name="Bai",
        background_id="alchemists_apprentice",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    first = service.list_saves()[0].last_played_at
    loaded = service.load_save(created.save_id)
    assert loaded.background_id == "alchemists_apprentice"
    assert loaded.money_copper == 40
    second = service.list_saves()[0].last_played_at
    assert second >= first


def test_delete_requires_confirmation_and_soft_deletes(tmp_path: Path) -> None:
    """Delete without confirmation fails; confirmed delete hides the save."""

    service = make_service(tmp_path)
    created = service.create_new_game(
        character_name="Delete Me",
        background_id="hunter",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    with pytest.raises(EngineValidationError, match="DELETE"):
        service.delete_save(created.save_id, confirmation="nope")

    service.delete_save(created.save_id, confirmation=DELETE_CONFIRMATION_VALUE)
    assert service.list_saves() == []
    with pytest.raises(EngineValidationError, match="Save not found"):
        service.load_save(created.save_id)


def test_save_repository_retains_id_after_soft_delete(tmp_path: Path) -> None:
    """Soft-deleted rows remain queryable including deleted when asked."""

    service = make_service(tmp_path)
    created = service.create_new_game(
        character_name="Keep Id",
        background_id="hunter",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    service.delete_save(created.save_id, confirmation=DELETE_CONFIRMATION_VALUE)

    settings = service._settings  # noqa: SLF001 — test inspects persistence
    engine = create_db_engine(settings)
    factory = create_session_factory(settings, engine=engine)
    with factory() as session:
        repo = SaveRepository(session)
        gone = repo.get_by_id(created.save_id)
        assert gone is None
        kept = repo.get_by_id(created.save_id, include_deleted=True)
        assert kept is not None
        assert kept.deleted_at is not None
        events = EventLogRepository(session).list_for_save(created.save_id)
        assert events
