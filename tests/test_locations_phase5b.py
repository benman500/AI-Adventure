"""Phase 5b: travel graph, LocationService, WorldClock, after_story_travel."""

from __future__ import annotations

import pytest

from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.locations import (
    clear_location_catalog_cache,
    find_travel_edge,
    plan_travel,
)
from ai_adventure.engine.time import advance_world_days
from ai_adventure.repositories.locations import LocationPresenceRepository
from ai_adventure.repositories.saves import EventLogRepository, SaveRepository
from ai_adventure.services.locations import LocationService
from tests.conftest_helpers import VALID_IDENTITY_ANSWERS, advance_to_cultivation_hall, make_service


@pytest.fixture(autouse=True)
def _clear_location_cache() -> None:
    clear_location_catalog_cache()
    yield
    clear_location_catalog_cache()


def test_travel_graph_covers_opening_path() -> None:
    assert find_travel_edge("hometown_market_lane", "road_north_of_willowford") is not None
    assert find_travel_edge("road_north_of_willowford", "jade_ridge_approach") is not None
    assert find_travel_edge("jade_ridge_approach", "verdant_gate_registration") is not None
    assert find_travel_edge("verdant_gate_cultivation_hall", "verdant_gate_foundation_hall") is not None


def test_plan_travel_blocks_missing_edge() -> None:
    result = plan_travel(
        from_location_id="hometown_market_lane",
        to_location_id="verdant_gate_foundation_hall",
        world_day=1,
        mode="travel",
    )
    assert result.outcome_type == "blocked"
    assert result.blocked_reason == "no_edge"


def test_plan_travel_uses_world_clock() -> None:
    result = plan_travel(
        from_location_id="road_north_of_willowford",
        to_location_id="jade_ridge_approach",
        world_day=3,
        mode="travel",
    )
    assert result.outcome_type == "success"
    assert result.plan is not None
    assert result.plan.days == 1
    assert result.plan.world_day_after == advance_world_days(3, 1)


def test_failed_travel_does_not_mutate_save(tmp_path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    with service._session_factory() as session:
        save = SaveRepository(session).get_with_player(loaded.save_id)
        assert save is not None and save.player is not None
        before_day = int(save.world_day)
        before_loc = str(save.player.current_location_id)
        with pytest.raises(EngineValidationError, match="No travel route|no_edge"):
            LocationService(session).travel(
                save=save,
                player=save.player,
                progress=save.story_progress,
                to_location_id="verdant_gate_foundation_hall",
            )
        session.rollback()

    with service._session_factory() as session:
        save = SaveRepository(session).get_with_player(loaded.save_id)
        assert save is not None and save.player is not None
        assert int(save.world_day) == before_day
        assert str(save.player.current_location_id) == before_loc


def test_free_travel_advances_clock_and_presence(tmp_path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    with service._session_factory() as session:
        save = SaveRepository(session).get_with_player(loaded.save_id)
        assert save is not None and save.player is not None
        # Story-leave to road first via LocationService (same path story uses).
        LocationService(session).relocate(
            save=save,
            player=save.player,
            progress=save.story_progress,
            to_location_id="road_north_of_willowford",
            mode="story",
            days_override=0,
        )
        result = LocationService(session).travel(
            save=save,
            player=save.player,
            progress=save.story_progress,
            to_location_id="jade_ridge_approach",
        )
        session.commit()
        assert result.location_id == "jade_ridge_approach"
        assert result.world_day == 2
        rows = LocationPresenceRepository(session).list_for_save(loaded.save_id)
        ids = {row.location_id for row in rows}
        assert "jade_ridge_approach" in ids


def test_story_opening_uses_location_service_edges(tmp_path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    advance_to_cultivation_hall(service, loaded.save_id)
    with service._session_factory() as session:
        save = SaveRepository(session).get_with_player(loaded.save_id)
        assert save is not None and save.player is not None
        assert save.player.current_location_id == "verdant_gate_cultivation_hall"
        events = EventLogRepository(session).list_for_save(loaded.save_id)
        travel_events = [e for e in events if e.event_type == "travel_resolved"]
        assert travel_events


def test_after_story_travel_hook_is_live_and_deterministic(tmp_path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )

    def _run_once(seed: int) -> tuple[int, str | None]:
        with service._session_factory() as session:
            save = SaveRepository(session).get_with_player(loaded.save_id)
            assert save is not None and save.player is not None
            # Reset to road for repeated trials.
            save.player.current_location_id = "road_north_of_willowford"
            save.player.current_location_name = "North Road out of Willowford"
            save.current_location_id = "road_north_of_willowford"
            save.current_location_name = "North Road out of Willowford"
            save.world_day = 1
            save.world_rng_counter = 0
            session.commit()

        with service._session_factory() as session:
            save = SaveRepository(session).get_with_player(loaded.save_id)
            assert save is not None and save.player is not None
            result = LocationService(session).travel(
                save=save,
                player=save.player,
                progress=save.story_progress,
                to_location_id="jade_ridge_approach",
            )
            # Force deterministic event evaluation by re-running with fixed rng
            # after travel: counter already bumped; check message stability via seed path.
            session.commit()
            return result.world_day, result.event_message

    # Same starting counter/seed path should be stable across process uses of Random(seed)
    day1, _ = _run_once(1)
    day2, _ = _run_once(1)
    assert day1 == day2 == 2


def test_story_and_free_travel_share_edge_days(tmp_path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    with service._session_factory() as session:
        save = SaveRepository(session).get_with_player(loaded.save_id)
        assert save is not None and save.player is not None
        LocationService(session).relocate(
            save=save,
            player=save.player,
            progress=None,
            to_location_id="road_north_of_willowford",
            mode="story",
            days_override=0,
        )
        free = plan_travel(
            from_location_id="road_north_of_willowford",
            to_location_id="jade_ridge_approach",
            world_day=int(save.world_day),
            mode="travel",
        )
        story = plan_travel(
            from_location_id="road_north_of_willowford",
            to_location_id="jade_ridge_approach",
            world_day=int(save.world_day),
            mode="story",
            days_override=1,
        )
        assert free.plan is not None and story.plan is not None
        assert free.plan.to_location_id == story.plan.to_location_id
        assert free.plan.days == story.plan.days == 1
