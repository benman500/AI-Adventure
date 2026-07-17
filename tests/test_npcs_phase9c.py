"""Phase 9c: NPC interaction pipeline (inspect / greet / ask_guidance)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.events import ALLOWED_TRIGGER_KINDS, clear_event_catalog_cache, load_event_catalog
from ai_adventure.engine.locations import clear_location_catalog_cache
from ai_adventure.engine.npcs import (
    clear_npc_catalog_cache,
    get_npc,
    get_npc_action,
    load_npc_action_catalog,
    plan_npc_interaction,
)
from ai_adventure.engine.npcs import NpcWorldStateRecord
from ai_adventure.engine.sects import clear_sect_catalog_cache
from ai_adventure.repositories.npc_world_state import NpcWorldStateRepository
from ai_adventure.repositories.saves import SaveRepository
from ai_adventure.services.npcs import NpcService
from tests.conftest_helpers import VALID_IDENTITY_ANSWERS, advance_to_cultivation_hall, make_service


@pytest.fixture(autouse=True)
def _clear_caches() -> None:
    clear_location_catalog_cache()
    clear_sect_catalog_cache()
    clear_npc_catalog_cache()
    clear_event_catalog_cache()
    yield
    clear_location_catalog_cache()
    clear_sect_catalog_cache()
    clear_npc_catalog_cache()
    clear_event_catalog_cache()


def test_npc_action_catalog_loads_core_actions() -> None:
    catalog = load_npc_action_catalog()
    assert {"inspect", "greet", "ask_guidance", "request_instruction", "acknowledge_path", "request_recommendation"} <= set(catalog.by_id)
    assert get_npc_action("ask_guidance").duration_days == 1
    assert get_npc_action("inspect").duration_days == 0
    assert "after_npc_interact" in ALLOWED_TRIGGER_KINDS


def test_event_catalog_includes_after_npc_interact() -> None:
    catalog = load_event_catalog()
    matching = [e for e in catalog.events if "after_npc_interact" in e.trigger.kinds]
    assert matching
    assert any(e.id == "evt_npc_quiet_counsel" for e in matching)


def test_inspect_and_ask_guidance_pipeline(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    advance_to_cultivation_hall(service, loaded.save_id)

    with service._session_factory() as session:  # noqa: SLF001
        save = SaveRepository(session).get_with_player(loaded.save_id)
        assert save is not None
        day_before = int(save.world_day)

    scene = service.interact_with_npc(loaded.save_id, "npc_instructor_001", "inspect")
    pei = next(n for n in scene.present_npcs if n["npc_id"] == "npc_instructor_001")
    assert pei["relationship_score"] == 1
    assert pei["met"] is True
    assert scene.message and "Instructor Pei" in scene.message
    assert "qi_gathering" in (scene.message or "")

    after_guidance = service.interact_with_npc(
        loaded.save_id, "npc_instructor_001", "ask_guidance"
    )
    pei2 = next(n for n in after_guidance.present_npcs if n["npc_id"] == "npc_instructor_001")
    assert pei2["relationship_score"] == 1 + 3
    assert after_guidance.world_day == day_before + 1

    with service._session_factory() as session:  # noqa: SLF001
        row = NpcWorldStateRepository(session).get_by_npc_id(
            loaded.save_id, "npc_instructor_001"
        )
        assert row is not None
        assert int(row.relationship_score) == 4
        assert int(row.last_interaction_world_day or 0) == after_guidance.world_day


def test_available_actions_exposed_on_present_cards(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    advance_to_cultivation_hall(service, loaded.save_id)
    scene = service.get_play_scene(loaded.save_id)
    pei = next(n for n in scene.present_npcs if n["npc_id"] == "npc_instructor_001")
    action_ids = {a["id"] for a in pei["available_actions"]}
    # Gated actions (e.g. request_instruction) appear only when requirements are met.
    assert {"inspect", "greet", "ask_guidance"} <= action_ids
    assert "request_instruction" not in action_ids


def test_unknown_action_rejected(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    advance_to_cultivation_hall(service, loaded.save_id)
    with pytest.raises(EngineValidationError, match="Unknown NPC action"):
        service.interact_with_npc(loaded.save_id, "npc_instructor_001", "trade")


def test_plan_npc_interaction_deterministic() -> None:
    from ai_adventure.engine.npcs import NpcInteractionPlayerContext

    definition = get_npc("npc_instructor_001")
    state = NpcWorldStateRecord(
        actor_id="a1",
        npc_id=definition.npc_id,
        current_location_id=definition.default_location_id,
        status="active",
        discovered=True,
        met=False,
        relationship_score=10,
        sect_id_override=None,
        state_flags={},
        last_interaction_world_day=None,
    )
    player = NpcInteractionPlayerContext(
        location_id=definition.default_location_id,
        realm_id="qi_gathering",
        stage_id="early",
        sect_id="sect_verdant_gate",
        sect_rank_id="outer_disciple",
        sect_standing=5,
        story_flags={},
    )
    first = plan_npc_interaction(
        definition=definition,
        state=state,
        player=player,
        action_id="inspect",
    )
    second = plan_npc_interaction(
        definition=definition,
        state=state,
        player=player,
        action_id="inspect",
    )
    assert first == second
    assert first.relationship_after == 11
    assert first.duration_days == 0
    assert first.trigger_kind == "after_npc_interact"
