"""Phase 9a–9b: NPC catalogs, world state, story spawn by npc_id, greet slice."""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from ai_adventure.config import get_settings
from ai_adventure.engine.constants import EVENT_TYPE_NPC_INTERACTION
from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.npcs import (
    GREET_RELATIONSHIP_DELTA as NPC_GREET_DELTA,
    assert_npc_catalog_valid,
    clear_npc_catalog_cache,
    get_npc,
    load_npc_catalog,
    plan_greet,
    validate_npc_catalog,
)
from ai_adventure.engine.sects import assert_sect_catalog_valid, clear_sect_catalog_cache, load_sect_catalog
from ai_adventure.engine.locations import clear_location_catalog_cache
from ai_adventure.repositories.npc_world_state import NpcWorldStateRepository
from ai_adventure.services.npcs import NpcService
from tests.conftest_helpers import VALID_IDENTITY_ANSWERS, advance_to_cultivation_hall, make_service

# Prefer engine constant; constants module may re-export later.
assert NPC_GREET_DELTA == 5


@pytest.fixture(autouse=True)
def _clear_caches() -> None:
    clear_location_catalog_cache()
    clear_sect_catalog_cache()
    clear_npc_catalog_cache()
    yield
    clear_location_catalog_cache()
    clear_sect_catalog_cache()
    clear_npc_catalog_cache()


def test_npc_and_sect_catalogs_validate() -> None:
    assert_sect_catalog_valid()
    assert_npc_catalog_valid()
    sects = load_sect_catalog()
    npcs = load_npc_catalog()
    assert "sect_verdant_gate" in sects.by_id
    assert "npc_instructor_001" in npcs.by_id
    pei = get_npc("npc_instructor_001")
    assert pei.display_name == "Instructor Pei"
    assert pei.default_location_id == "verdant_gate_cultivation_hall"


def test_duplicate_npc_id_fails_validation(tmp_path: Path) -> None:
    world = tmp_path / "world"
    packs = world / "packs" / "p1"
    packs.mkdir(parents=True)
    (world / "world_manifest.json").write_text(
        '{"schema_version":1,"packs":["p1"]}', encoding="utf-8"
    )
    (packs / "manifest.json").write_text(
        '{"pack_id":"p1","display_name":"P1","depends_on":[],'
        '"content_files":{"locations":"locations.json","npcs":"npcs.json","sects":"sects.json"}}',
        encoding="utf-8",
    )
    (packs / "locations.json").write_text(
        '{"schema_version":1,"locations":[{"id":"loc_a","kind":"site","display_name":"A"}]}',
        encoding="utf-8",
    )
    (packs / "sects.json").write_text(
        '{"schema_version":1,"sects":[{"sect_id":"sect_a","display_name":"A",'
        '"home_location_id":"loc_a","description":"d","initial_standing":0,'
        '"ranks":[{"rank_id":"r1","display_name":"R","order":0}]}]}',
        encoding="utf-8",
    )
    npc = {
        "npc_id": "npc_dup",
        "display_name": "Dup",
        "role_tags": ["disciple"],
        "home_location_id": "loc_a",
        "default_location_id": "loc_a",
        "sect_id": "sect_a",
        "cultivation_summary": {"realm_id": "body_tempering", "stage_id": "early", "path_tags": []},
        "description": "x",
    }
    import json

    (packs / "npcs.json").write_text(
        json.dumps({"schema_version": 1, "npcs": [npc, npc]}),
        encoding="utf-8",
    )
    errors = validate_npc_catalog(world)
    assert any("duplicate npc_id" in e for e in errors)


def test_story_spawn_by_npc_id_persists_world_state(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    advance_to_cultivation_hall(service, loaded.save_id)

    with service._session_factory() as session:  # noqa: SLF001
        rows = NpcWorldStateRepository(session).list_for_save(loaded.save_id)
        by_id = {row.npc_id: row for row in rows}
        assert "npc_instructor_001" in by_id
        pei = by_id["npc_instructor_001"]
        assert pei.current_location_id == "verdant_gate_cultivation_hall"
        assert pei.discovered == 1
        assert pei.met == 0
        assert pei.relationship_score == 0
        # Catalog authority: no display_name column on world state.


def test_greet_changes_relationship_and_survives_reload(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    advance_to_cultivation_hall(service, loaded.save_id)

    scene = service.get_play_scene(loaded.save_id)
    present_ids = {n["npc_id"] for n in scene.present_npcs}
    assert "npc_instructor_001" in present_ids
    pei_card = next(n for n in scene.present_npcs if n["npc_id"] == "npc_instructor_001")
    assert pei_card["display_name"] == "Instructor Pei"
    assert pei_card["relationship_score"] == 0

    after = service.greet_npc(loaded.save_id, "npc_instructor_001")
    pei_after = next(n for n in after.present_npcs if n["npc_id"] == "npc_instructor_001")
    assert pei_after["relationship_score"] == NPC_GREET_DELTA
    assert pei_after["met"] is True
    assert after.message and "Instructor Pei" in after.message

    reloaded = service.get_play_scene(loaded.save_id)
    pei_reload = next(n for n in reloaded.present_npcs if n["npc_id"] == "npc_instructor_001")
    assert pei_reload["relationship_score"] == NPC_GREET_DELTA
    assert pei_reload["met"] is True

    with service._session_factory() as session:  # noqa: SLF001
        from ai_adventure.repositories.saves import EventLogRepository

        events = EventLogRepository(session).list_for_save(loaded.save_id)
        assert any(e.event_type == EVENT_TYPE_NPC_INTERACTION for e in events)


def test_greet_blocked_when_not_colocated(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    service.get_play_scene(loaded.save_id)
    # Lu Han spawns on the road node before the player reaches jade ridge.
    service.submit_story_action(loaded.save_id, "finish_tally")
    service.submit_story_action(loaded.save_id, "listen_quietly")
    service.submit_story_action(loaded.save_id, "leave_home")
    service.submit_story_action(loaded.save_id, "continue")
    service.submit_story_action(loaded.save_id, "continue")  # to cultivator node → spawn Lu Han

    with pytest.raises(EngineValidationError, match="not at your current location"):
        NpcService(service._session_factory).greet(  # noqa: SLF001
            loaded.save_id, "npc_passing_cultivator_001"
        )


def test_unknown_npc_greet_fails(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    with pytest.raises(EngineValidationError, match="Unknown NPC"):
        service.greet_npc(loaded.save_id, "npc_does_not_exist")


def test_plan_greet_is_deterministic() -> None:
    from ai_adventure.engine.npcs import NpcWorldStateRecord

    definition = get_npc("npc_instructor_001")
    state = NpcWorldStateRecord(
        actor_id="a1",
        npc_id=definition.npc_id,
        current_location_id=definition.default_location_id,
        status="active",
        discovered=True,
        met=False,
        relationship_score=0,
        sect_id_override=None,
        state_flags={},
        last_interaction_world_day=None,
    )
    first = plan_greet(
        definition=definition,
        state=state,
        player_location_id=definition.default_location_id,
    )
    second = plan_greet(
        definition=definition,
        state=state,
        player_location_id=definition.default_location_id,
    )
    assert first.relationship_after == second.relationship_after == NPC_GREET_DELTA


def test_migration_0012_creates_npc_world_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "npc.db"
    url = f"sqlite:///{db_path.as_posix()}"
    monkeypatch.setenv("AI_ADVENTURE_DATABASE_URL", url)
    get_settings.cache_clear()

    root = Path(__file__).resolve().parents[1]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")

    with create_engine(url, future=True).connect() as conn:
        version = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
        assert version == ("0013_sect_standing",)
        tables = {
            row[0]
            for row in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            ).fetchall()
        }
        assert "npc_world_state" in tables

    get_settings.cache_clear()
