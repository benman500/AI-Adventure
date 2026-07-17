"""Phase 11a: Aspiration catalog, eligibility, and play panel."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_adventure.engine.aspirations import (
    AspirationFactSnapshot,
    clear_aspiration_catalog_cache,
    evaluate_aspiration,
    get_aspiration,
    load_aspiration_catalog,
    select_primary_aspiration,
    evaluate_all_aspirations,
)
from ai_adventure.engine.locations import clear_location_catalog_cache
from ai_adventure.engine.npcs import clear_npc_catalog_cache, get_npc_action, load_npc_action_catalog
from ai_adventure.engine.sects import clear_sect_catalog_cache
from ai_adventure.engine.techniques import clear_technique_catalog_cache
from tests.conftest_helpers import (
    VALID_IDENTITY_ANSWERS,
    build_breakthrough_readiness,
    make_service,
)


@pytest.fixture(autouse=True)
def _clear_caches() -> None:
    clear_aspiration_catalog_cache()
    clear_location_catalog_cache()
    clear_sect_catalog_cache()
    clear_npc_catalog_cache()
    clear_technique_catalog_cache()
    yield
    clear_aspiration_catalog_cache()
    clear_location_catalog_cache()
    clear_sect_catalog_cache()
    clear_npc_catalog_cache()
    clear_technique_catalog_cache()


def _reach_post_ordinary(service, save_id: str) -> None:
    build_breakthrough_readiness(service, save_id)
    service.submit_story_action(save_id, "attempt_breakthrough")
    service.submit_story_action(save_id, "report")
    service.submit_story_action(save_id, "continue")
    service.submit_story_action(save_id, "continue")
    service.submit_story_action(save_id, "continue")
    service.submit_story_action(save_id, "go")
    service.submit_story_action(save_id, "continue")  # revelation → choice
    service.submit_story_action(save_id, "choose_ordinary")
    service.submit_story_action(save_id, "continue")  # post_01 → post_02


def test_aspiration_catalog_loads_seed() -> None:
    catalog = load_aspiration_catalog()
    assert "asp_stabilize_outer_probation" in catalog.by_id
    assert "asp_earn_elder_recommendation" in catalog.by_id
    first = get_aspiration("asp_stabilize_outer_probation")
    assert first.kind == "primary"
    assert len(first.facets) == 3


def test_npc_catalog_includes_path_and_recommendation_actions() -> None:
    catalog = load_npc_action_catalog()
    assert "acknowledge_path" in catalog.by_id
    assert "request_recommendation" in catalog.by_id
    assert get_npc_action("acknowledge_path").duration_days == 0


def test_eligibility_reads_facts_only() -> None:
    aspiration = get_aspiration("asp_stabilize_outer_probation")
    empty = AspirationFactSnapshot(
        path_status="confirmed_ordinary",
        story_flags={"path_confirmed": True},
    )
    evaluation = evaluate_aspiration(aspiration, empty)
    assert evaluation.available is True
    assert evaluation.fulfilled is False
    assert len(evaluation.gaps) == 3

    ready = AspirationFactSnapshot(
        path_status="confirmed_ordinary",
        story_flags={
            "path_confirmed": True,
            "yun_mei_acknowledged_path": True,
        },
        npc_relationships={"npc_instructor_001": 5},
        known_technique_ids=frozenset({"tech_foundation_guard"}),
    )
    done = evaluate_aspiration(aspiration, ready)
    assert done.fulfilled is True
    assert done.gaps == ()


def test_primary_selection_orders_spine() -> None:
    facts = AspirationFactSnapshot(
        path_status="confirmed_ordinary",
        story_flags={"path_confirmed": True},
    )
    evaluations = evaluate_all_aspirations(facts)
    primary = select_primary_aspiration(evaluations)
    assert primary is not None
    assert primary.aspiration_id == "asp_stabilize_outer_probation"

    facts_done = AspirationFactSnapshot(
        path_status="confirmed_ordinary",
        story_flags={
            "path_confirmed": True,
            "yun_mei_acknowledged_path": True,
        },
        npc_relationships={"npc_instructor_001": 5},
        known_technique_ids=frozenset({"tech_foundation_guard"}),
    )
    next_primary = select_primary_aspiration(evaluate_all_aspirations(facts_done))
    assert next_primary is not None
    assert next_primary.aspiration_id == "asp_earn_elder_recommendation"


def test_play_scene_shows_working_toward_after_path(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    scene = service.get_play_scene(loaded.save_id)
    assert scene.aspiration_panel is None

    _reach_post_ordinary(service, loaded.save_id)
    scene = service.get_play_scene(loaded.save_id)
    assert scene.opening_complete is True
    assert scene.aspiration_panel is not None
    assert scene.aspiration_panel["visible"] is True
    toward = scene.aspiration_panel["working_toward"]
    assert toward["id"] == "asp_stabilize_outer_probation"
    assert toward["display_name"] == "Find Your Footing"
    assert len(scene.aspiration_panel["current_gaps"]) == 3
    assert scene.aspiration_panel["possible_paths"]
    assert scene.travel_destinations


def test_stabilize_aspiration_completable_via_existing_systems(tmp_path: Path) -> None:
    """Player fantasy: settle into outer life using travel + NPC interactions."""

    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    _reach_post_ordinary(service, loaded.save_id)

    # Elder acknowledgment at Foundation Hall.
    scene = service.interact_with_npc(
        loaded.save_id, "npc_foundation_elder_001", "acknowledge_path"
    )
    assert scene.message and "Yun Mei" in scene.message
    gaps = {g["id"] for g in scene.aspiration_panel["current_gaps"]}
    assert "elder_witness" not in gaps

    # Travel to Cultivation Hall and earn Pei's instruction.
    scene = service.travel_to(loaded.save_id, "verdant_gate_cultivation_hall")
    assert "Cultivation Hall" in scene.current_location_name
    service.interact_with_npc(loaded.save_id, "npc_instructor_001", "greet")
    service.interact_with_npc(loaded.save_id, "npc_instructor_001", "greet")
    scene = service.interact_with_npc(
        loaded.save_id, "npc_instructor_001", "request_instruction"
    )
    assert "Foundation Guard" in (scene.message or "")

    toward = scene.aspiration_panel["working_toward"]
    assert toward["id"] == "asp_earn_elder_recommendation"
    assert toward["display_name"] == "Earn an Elder's Recommendation"
    assert scene.aspiration_panel["fulfilled_previous"]["id"] == "asp_stabilize_outer_probation"
    assert scene.aspiration_panel["current_gaps"]
    assert scene.aspiration_panel["possible_paths"]
