"""Phase 10: authored NPC interaction framework (Request Instruction slice)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_adventure.engine.constants import FLAG_TAUGHT_FOUNDATION_GUARD
from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.locations import clear_location_catalog_cache
from ai_adventure.engine.npcs import (
    IMPLEMENTED_NPC_REWARD_TYPES,
    RESERVED_NPC_REWARD_TYPES,
    clear_npc_catalog_cache,
    get_npc,
    get_npc_action,
    list_offered_actions_for_npc,
    load_npc_action_catalog,
    validate_npc_action_catalog,
)
from ai_adventure.engine.sects import clear_sect_catalog_cache
from ai_adventure.engine.story import parse_flags
from ai_adventure.repositories.saves import SaveRepository
from ai_adventure.repositories.techniques import TechniqueMasteryRepository
from tests.conftest_helpers import VALID_IDENTITY_ANSWERS, advance_to_cultivation_hall, make_service


@pytest.fixture(autouse=True)
def _clear_caches() -> None:
    clear_location_catalog_cache()
    clear_sect_catalog_cache()
    clear_npc_catalog_cache()
    yield
    clear_location_catalog_cache()
    clear_sect_catalog_cache()
    clear_npc_catalog_cache()


def _prepare_pei_instruction_ready(service, save_id: str) -> None:
    """Build relationship 8+ and standing 7+ with Pei (greet + ask_guidance)."""

    service.interact_with_npc(save_id, "npc_instructor_001", "greet")
    # rel 5, standing 6
    service.interact_with_npc(save_id, "npc_instructor_001", "ask_guidance")
    # rel 8, standing 8


def test_catalog_validates_and_reserves_future_rewards() -> None:
    load_npc_action_catalog()
    assert not validate_npc_action_catalog()
    assert "learn_technique" in IMPLEMENTED_NPC_REWARD_TYPES
    assert "begin_mission" in RESERVED_NPC_REWARD_TYPES
    assert RESERVED_NPC_REWARD_TYPES.isdisjoint(IMPLEMENTED_NPC_REWARD_TYPES)
    action = get_npc_action("request_instruction")
    assert action.requirements.min_relationship == 8
    assert action.requirements.min_sect_standing == 7
    assert action.requirements.allowed_npc_ids == ["npc_instructor_001"]
    assert any(r.type == "learn_technique" for r in action.rewards)


def test_request_instruction_only_offered_by_pei() -> None:
    pei = get_npc("npc_instructor_001")
    elder = get_npc("npc_foundation_elder_001")
    pei_ids = {a.id for a in list_offered_actions_for_npc(pei)}
    elder_ids = {a.id for a in list_offered_actions_for_npc(elder)}
    assert "request_instruction" in pei_ids
    assert "request_instruction" not in elder_ids


def test_unmet_relationship_blocks_instruction(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    advance_to_cultivation_hall(service, loaded.save_id)
    # standing can be raised without enough relationship
    service.interact_with_npc(loaded.save_id, "npc_instructor_001", "ask_guidance")
    # rel 3, standing 7 — relationship gate fails
    with pytest.raises(EngineValidationError, match="Relationship"):
        service.interact_with_npc(
            loaded.save_id, "npc_instructor_001", "request_instruction"
        )


def test_unmet_standing_blocks_instruction(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    advance_to_cultivation_hall(service, loaded.save_id)
    # Raise relationship without reaching standing 7 (inspect only).
    for _ in range(8):
        service.interact_with_npc(loaded.save_id, "npc_instructor_001", "inspect")
    # rel 8, standing still 5
    with pytest.raises(EngineValidationError, match="Sect standing"):
        service.interact_with_npc(
            loaded.save_id, "npc_instructor_001", "request_instruction"
        )


def test_wrong_npc_cannot_request_instruction(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    advance_to_cultivation_hall(service, loaded.save_id)
    with service._session_factory() as session:  # noqa: SLF001
        from ai_adventure.services.npcs import NpcService

        NpcService(service._session_factory).ensure_spawned(  # noqa: SLF001
            session,
            save_id=loaded.save_id,
            npc_id="npc_foundation_elder_001",
        )
        save = SaveRepository(session).get_with_player(loaded.save_id)
        assert save is not None and save.player is not None
        save.player.current_location_id = "verdant_gate_foundation_hall"
        save.current_location_id = "verdant_gate_foundation_hall"
        session.commit()

    with pytest.raises(EngineValidationError, match="does not offer"):
        service.interact_with_npc(
            loaded.save_id, "npc_foundation_elder_001", "request_instruction"
        )


def test_request_instruction_teaches_technique(tmp_path: Path) -> None:
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

    _prepare_pei_instruction_ready(service, loaded.save_id)
    scene = service.interact_with_npc(
        loaded.save_id, "npc_instructor_001", "request_instruction"
    )
    assert scene.world_day == day_before + 1 + 1  # ask_guidance + request_instruction
    assert scene.message and "Foundation Guard" in (scene.message or "")
    assert scene.sect_membership is not None
    # standing: 5 +1 greet +2 guidance +1 instruction = 9
    assert scene.sect_membership["standing_score"] == 9

    tech = next(t for t in scene.techniques if t["id"] == "tech_foundation_guard")
    assert tech["known"] is True

    with service._session_factory() as session:  # noqa: SLF001
        save = SaveRepository(session).get_with_player(loaded.save_id)
        assert save is not None and save.player is not None and save.story_progress
        flags = parse_flags(save.story_progress.flags_json)
        assert flags.has(FLAG_TAUGHT_FOUNDATION_GUARD)
        row = TechniqueMasteryRepository(session).get(
            loaded.save_id, save.player.actor_id, "tech_foundation_guard"
        )
        assert row is not None and bool(row.known)


def test_duplicate_instruction_blocked(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    advance_to_cultivation_hall(service, loaded.save_id)
    _prepare_pei_instruction_ready(service, loaded.save_id)
    service.interact_with_npc(
        loaded.save_id, "npc_instructor_001", "request_instruction"
    )
    with pytest.raises(EngineValidationError, match="already done"):
        service.interact_with_npc(
            loaded.save_id, "npc_instructor_001", "request_instruction"
        )


def test_instruction_persists_across_reload(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    advance_to_cultivation_hall(service, loaded.save_id)
    _prepare_pei_instruction_ready(service, loaded.save_id)
    service.interact_with_npc(
        loaded.save_id, "npc_instructor_001", "request_instruction"
    )
    reloaded = service.get_play_scene(loaded.save_id)
    tech = next(t for t in reloaded.techniques if t["id"] == "tech_foundation_guard")
    assert tech["known"] is True


def test_missing_sect_membership_blocks_instruction(tmp_path: Path) -> None:
    """Direct engine-style failure: without membership, required_sect_id fails."""

    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    # Do not advance through recruitment — no sect membership
    with service._session_factory() as session:  # noqa: SLF001
        from ai_adventure.services.npcs import NpcService
        from ai_adventure.repositories.saves import SaveRepository

        NpcService(service._session_factory).ensure_spawned(  # noqa: SLF001
            session,
            save_id=loaded.save_id,
            npc_id="npc_instructor_001",
        )
        save = SaveRepository(session).get_with_player(loaded.save_id)
        assert save is not None and save.player is not None
        save.player.current_location_id = "verdant_gate_cultivation_hall"
        save.current_location_id = "verdant_gate_cultivation_hall"
        session.commit()

    with pytest.raises(EngineValidationError, match="member of"):
        service.interact_with_npc(
            loaded.save_id, "npc_instructor_001", "request_instruction"
        )
