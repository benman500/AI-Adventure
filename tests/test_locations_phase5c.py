"""Phase 5c: location actions (explore / inspect) and event integration."""

from __future__ import annotations

from random import Random

import pytest

from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.events import clear_event_catalog_cache, load_event_catalog
from ai_adventure.engine.location_actions import (
    clear_location_action_catalog_cache,
    list_available_location_actions,
    plan_location_action,
)
from ai_adventure.engine.locations import clear_location_catalog_cache
from ai_adventure.repositories.saves import EventLogRepository, SaveRepository
from ai_adventure.services.locations import LocationService
from tests.conftest_helpers import VALID_IDENTITY_ANSWERS, advance_to_cultivation_hall, make_service


@pytest.fixture(autouse=True)
def _clear_caches() -> None:
    clear_location_catalog_cache()
    clear_location_action_catalog_cache()
    clear_event_catalog_cache()
    yield
    clear_location_catalog_cache()
    clear_location_action_catalog_cache()
    clear_event_catalog_cache()


def test_action_catalog_offers_explore_and_inspect_at_hall() -> None:
    offered = list_available_location_actions("verdant_gate_cultivation_hall")
    by_id = {item.id: item for item in offered}
    assert "explore" in by_id and by_id["explore"].available
    assert "inspect" in by_id and by_id["inspect"].available
    assert "cultivate" in by_id and not by_id["cultivate"].available
    assert by_id["cultivate"].blocked_reason == "not_implemented"


def test_plan_blocks_action_not_offered_here() -> None:
    result = plan_location_action(
        location_id="verdant_gate_registration",
        action_id="explore",
        world_day=2,
    )
    assert result.outcome_type == "blocked"
    assert result.blocked_reason == "not_offered"


def test_explore_advances_clock_and_can_fire_location_event(tmp_path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    advance_to_cultivation_hall(service, loaded.save_id)

    class Always(Random):
        def random(self) -> float:  # noqa: A003
            return 0.0

    with service._session_factory() as session:
        save = SaveRepository(session).get_with_player(loaded.save_id)
        assert save is not None and save.player is not None
        day_before = int(save.world_day)
        result = LocationService(session).perform_action(
            save=save,
            player=save.player,
            progress=save.story_progress,
            action_id="explore",
        )
        # LocationService already evaluates the explore trigger once.
        # If it happened to fire on that first attempt, the cooldown may
        # prevent the forced rerun from firing. Accept either outcome.
        from ai_adventure.services.events import EventService

        if result.event_message is None:
            event = EventService(session).run_after_explore(
                save=save,
                player=save.player,
                progress=save.story_progress,
                rng=Always(1),
            )
            session.commit()
            assert event.fired is True
        else:
            event = None
        session.commit()
        assert result.action_id == "explore"
        assert result.world_day == day_before + 1
        assert result.event_message is not None or event is not None


def test_inspect_is_instant_and_uses_real_location_ids(tmp_path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    advance_to_cultivation_hall(service, loaded.save_id)
    scene = service.perform_location_action(loaded.save_id, "inspect")
    assert scene.message
    assert any(a["id"] == "inspect" for a in scene.location_actions)

    catalog = load_event_catalog()
    inspect_events = [
        e for e in catalog.events if "after_inspect" in e.trigger.kinds
    ]
    assert inspect_events
    assert any(
        "verdant_gate_cultivation_hall" in e.requirements.location_ids
        for e in inspect_events
    )


def test_failed_location_action_does_not_mutate(tmp_path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    service.get_play_scene(loaded.save_id)
    with service._session_factory() as session:
        save = SaveRepository(session).get_with_player(loaded.save_id)
        assert save is not None and save.player is not None
        day_before = int(save.world_day)
        with pytest.raises(EngineValidationError):
            LocationService(session).perform_action(
                save=save,
                player=save.player,
                progress=save.story_progress,
                action_id="explore",  # hometown market has inspect only
            )
        session.rollback()
    with service._session_factory() as session:
        save = SaveRepository(session).get_with_player(loaded.save_id)
        assert save is not None
        assert int(save.world_day) == day_before


def test_play_scene_exposes_location_actions(tmp_path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    advance_to_cultivation_hall(service, loaded.save_id)
    scene = service.get_play_scene(loaded.save_id)
    ids = {a["id"] for a in scene.location_actions}
    assert "explore" in ids
    assert "inspect" in ids
    available = {a["id"] for a in scene.location_actions if a["available"]}
    assert "explore" in available
    assert "inspect" in available


def test_location_action_appends_audit_event(tmp_path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    advance_to_cultivation_hall(service, loaded.save_id)
    service.perform_location_action(loaded.save_id, "inspect")
    with service._session_factory() as session:
        logs = EventLogRepository(session).list_for_save(loaded.save_id)
        assert any(e.event_type == "location_action_resolved" for e in logs)
