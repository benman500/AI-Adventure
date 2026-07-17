"""Phase 11b: duties, profession job, unlock location, aspiration fact feeds."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.events import clear_event_catalog_cache, load_event_catalog
from ai_adventure.engine.location_actions import (
    clear_location_action_catalog_cache,
    get_location_action,
    load_location_action_catalog,
)
from ai_adventure.engine.locations import clear_location_catalog_cache
from ai_adventure.engine.npcs import clear_npc_catalog_cache
from ai_adventure.engine.sects import clear_sect_catalog_cache
from ai_adventure.repositories.locations import LocationPresenceRepository
from ai_adventure.repositories.saves import SaveRepository
from ai_adventure.repositories.story import StoryRepository
from ai_adventure.engine.story import parse_flags
from tests.conftest_helpers import (
    VALID_IDENTITY_ANSWERS,
    build_breakthrough_readiness,
    make_service,
)


@pytest.fixture(autouse=True)
def _clear_caches() -> None:
    clear_location_catalog_cache()
    clear_location_action_catalog_cache()
    clear_sect_catalog_cache()
    clear_npc_catalog_cache()
    clear_event_catalog_cache()
    yield
    clear_location_catalog_cache()
    clear_location_action_catalog_cache()
    clear_sect_catalog_cache()
    clear_npc_catalog_cache()
    clear_event_catalog_cache()


def _reach_post_ordinary(service, save_id: str) -> None:
    build_breakthrough_readiness(service, save_id)
    service.submit_story_action(save_id, "attempt_breakthrough")
    service.submit_story_action(save_id, "report")
    service.submit_story_action(save_id, "continue")
    service.submit_story_action(save_id, "continue")
    service.submit_story_action(save_id, "continue")
    service.submit_story_action(save_id, "go")
    service.submit_story_action(save_id, "continue")
    service.submit_story_action(save_id, "choose_ordinary")
    service.submit_story_action(save_id, "continue")


def test_duty_and_job_catalog_entries_load() -> None:
    catalog = load_location_action_catalog()
    for action_id in (
        "duty_herb_path",
        "duty_lecture",
        "duty_outer_chore",
        "job_sort_herbs",
    ):
        action = get_location_action(action_id, catalog=catalog)
        assert action.implemented is True
        assert action.duration_days == 1
        assert action.rewards
    assert "after_duty" in {
        kind
        for event in load_event_catalog().events
        for kind in event.trigger.kinds
    }


def test_three_duties_and_job_advance_clock_and_standing(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    _reach_post_ordinary(service, loaded.save_id)

    before = service.get_play_scene(loaded.save_id)
    standing_before = before.sect_membership["standing_score"]
    day_before = before.world_day

    service.travel_to(loaded.save_id, "verdant_gate_outer_quarters")
    chore = service.perform_location_action(loaded.save_id, "duty_outer_chore")
    assert chore.world_day == day_before + 1
    assert chore.sect_membership["standing_score"] >= standing_before + 1

    service.travel_to(loaded.save_id, "verdant_gate_cultivation_hall")
    lecture = service.perform_location_action(loaded.save_id, "duty_lecture")
    assert lecture.world_day == chore.world_day + 1

    service.travel_to(loaded.save_id, "verdant_gate_herb_garden")
    herb = service.perform_location_action(loaded.save_id, "duty_herb_path")
    assert herb.world_day == lecture.world_day + 1
    assert any(n["npc_id"] == "npc_herb_steward_001" for n in herb.present_npcs)

    money_before = None
    with service._session_factory() as session:  # noqa: SLF001
        save = SaveRepository(session).get_with_player(loaded.save_id)
        assert save is not None and save.player is not None
        money_before = int(save.player.money_copper)

    job = service.perform_location_action(loaded.save_id, "job_sort_herbs")
    with service._session_factory() as session:  # noqa: SLF001
        save = SaveRepository(session).get_with_player(loaded.save_id)
        assert save is not None and save.player is not None
        assert int(save.player.money_copper) >= money_before + 12

    # Aspiration recommendation standing gap can close via duties.
    panel = job.aspiration_panel
    assert panel is not None
    assert panel["working_toward"]["id"] in {
        "asp_stabilize_outer_probation",
        "asp_earn_elder_recommendation",
    }


def test_alchemist_background_bonus_on_herb_job(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Herb Wei",
        background_id="alchemists_apprentice",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    _reach_post_ordinary(service, loaded.save_id)
    service.travel_to(loaded.save_id, "verdant_gate_herb_garden")
    with service._session_factory() as session:  # noqa: SLF001
        save = SaveRepository(session).get_with_player(loaded.save_id)
        assert save is not None and save.player is not None
        money_before = int(save.player.money_copper)
    service.perform_location_action(loaded.save_id, "job_sort_herbs")
    with service._session_factory() as session:  # noqa: SLF001
        save = SaveRepository(session).get_with_player(loaded.save_id)
        assert save is not None and save.player is not None
        # Base 12 + alchemist bonus 8
        assert int(save.player.money_copper) >= money_before + 20


def test_misty_grove_unlock_persists_and_enables_travel(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    _reach_post_ordinary(service, loaded.save_id)
    service.travel_to(loaded.save_id, "verdant_gate_herb_garden")

    scene = service.get_play_scene(loaded.save_id)
    assert all(d["location_id"] != "verdant_gate_misty_grove" for d in scene.travel_destinations)

    # Build steward relationship, then unlock.
    service.interact_with_npc(loaded.save_id, "npc_herb_steward_001", "greet")
    unlocked = service.interact_with_npc(
        loaded.save_id, "npc_herb_steward_001", "ask_misty_path"
    )
    assert "Misty" in (unlocked.message or "") or "mist" in (unlocked.message or "").lower()
    assert any(
        d["location_id"] == "verdant_gate_misty_grove" for d in unlocked.travel_destinations
    )

    with service._session_factory() as session:  # noqa: SLF001
        progress = StoryRepository(session).get_for_save(loaded.save_id)
        assert progress is not None
        flags = parse_flags(progress.flags_json).values
        assert flags.get("unlocked_verdant_gate_misty_grove") is True
        presence = LocationPresenceRepository(session).get(
            loaded.save_id, "verdant_gate_misty_grove"
        )
        assert presence is not None

    grove = service.travel_to(loaded.save_id, "verdant_gate_misty_grove")
    assert "Misty Herb Grove" in grove.current_location_name
    inspect_scene = service.perform_location_action(loaded.save_id, "inspect")
    assert inspect_scene.location_actions

    # Repeated unlock claim fails.
    with pytest.raises(EngineValidationError):
        service.interact_with_npc(loaded.save_id, "npc_herb_steward_001", "ask_misty_path")


def test_duty_requires_path_confirmed(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    # Still provisional — travel to quarters via story path mid-opening is awkward;
    # use cultivation hall after lesson only.
    from tests.conftest_helpers import advance_to_cultivation_hall

    advance_to_cultivation_hall(service, loaded.save_id)
    with pytest.raises(EngineValidationError):
        service.perform_location_action(loaded.save_id, "duty_lecture")


def test_save_reload_preserves_unlock_flag(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    _reach_post_ordinary(service, loaded.save_id)
    service.travel_to(loaded.save_id, "verdant_gate_herb_garden")
    service.interact_with_npc(loaded.save_id, "npc_herb_steward_001", "greet")
    service.interact_with_npc(loaded.save_id, "npc_herb_steward_001", "ask_misty_path")

    reloaded = service.get_play_scene(loaded.save_id)
    assert any(
        d["location_id"] == "verdant_gate_misty_grove" for d in reloaded.travel_destinations
    )
