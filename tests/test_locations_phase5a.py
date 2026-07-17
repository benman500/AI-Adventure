"""Phase 5a: location catalog packs, presence, and story location migration."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from ai_adventure.config import get_settings
from ai_adventure.db import models as _models  # noqa: F401
from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.locations import (
    clear_location_catalog_cache,
    compute_presence_upsert,
    get_location,
    load_location_catalog,
    require_known_location,
    resolve_location_display_name,
    validate_location_catalog,
)
from ai_adventure.engine.cultivation_state import cultivation_state_from_player
from ai_adventure.engine.story import StoryContext, apply_story_action, parse_flags
from ai_adventure.repositories.locations import LocationPresenceRepository
from ai_adventure.repositories.saves import SaveRepository
from tests.conftest_helpers import VALID_IDENTITY_ANSWERS, make_service


REQUIRED_OPENING_LOCATION_IDS = frozenset(
    {
        "hometown_market_lane",
        "hometown_herb_workshop",
        "hometown_wild_edge",
        "road_north_of_willowford",
        "road_out_of_ashridge",
        "road_from_pinehollow",
        "jade_ridge_approach",
        "jade_ridge_verdant_gate",
        "verdant_gate_registration",
        "verdant_gate_outer_quarters",
        "verdant_gate_cultivation_hall",
        "verdant_gate_foundation_hall",
    }
)


@pytest.fixture(autouse=True)
def _clear_location_cache() -> None:
    clear_location_catalog_cache()
    yield
    clear_location_catalog_cache()


def test_location_catalog_loads_and_validates() -> None:
    report = validate_location_catalog()
    assert report.ok, [issue.message for issue in report.errors]
    catalog = load_location_catalog()
    assert "opening_homelands" in catalog.pack_ids
    assert "jade_ridge" in catalog.pack_ids
    assert "verdant_gate" in catalog.pack_ids
    for location_id in REQUIRED_OPENING_LOCATION_IDS:
        assert location_id in catalog.by_id


def test_verdant_gate_depends_on_jade_ridge_parent() -> None:
    hall = get_location("verdant_gate_cultivation_hall")
    assert hall.parent_id == "jade_ridge_verdant_gate"
    assert hall.sect_id == "sect_verdant_gate"
    assert "basic_cultivation" in hall.technique_tags
    assert hall.presentation.music is None


def test_unknown_location_rejected() -> None:
    with pytest.raises(EngineValidationError, match="Unknown location_id"):
        require_known_location("no_such_place")


def test_duplicate_location_id_across_packs_fails(tmp_path: Path) -> None:
    root = tmp_path / "world"
    packs = root / "packs"
    (packs / "a").mkdir(parents=True)
    (packs / "b").mkdir(parents=True)
    (root / "world_manifest.json").write_text(
        json.dumps({"schema_version": 1, "packs": ["a", "b"]}),
        encoding="utf-8",
    )
    for pack_id in ("a", "b"):
        (packs / pack_id / "manifest.json").write_text(
            json.dumps(
                {
                    "pack_id": pack_id,
                    "display_name": pack_id,
                    "depends_on": [],
                    "content_files": {"locations": "locations.json"},
                }
            ),
            encoding="utf-8",
        )
        (packs / pack_id / "locations.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "locations": [
                        {
                            "id": "shared_id",
                            "kind": "site",
                            "display_name": "Dup",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
    report = validate_location_catalog(root)
    assert not report.ok
    assert any(issue.code == "duplicate_location_id" for issue in report.errors)


def test_presence_upsert_increments() -> None:
    first = compute_presence_upsert(
        location_id="hometown_market_lane",
        world_day=1,
        existing_visit_count=None,
        existing_discovered_world_day=None,
        existing_first_visited_world_day=None,
    )
    assert first.is_new
    assert first.visit_count == 1
    second = compute_presence_upsert(
        location_id="hometown_market_lane",
        world_day=3,
        existing_visit_count=first.visit_count,
        existing_discovered_world_day=first.discovered_world_day,
        existing_first_visited_world_day=first.first_visited_world_day,
    )
    assert not second.is_new
    assert second.visit_count == 2
    assert second.last_visited_world_day == 3
    assert second.discovered_world_day == 1


def test_create_new_game_records_starting_presence(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    assert loaded.current_location_name == resolve_location_display_name(
        "hometown_market_lane"
    )
    with service._session_factory() as session:
        rows = LocationPresenceRepository(session).list_for_save(loaded.save_id)
        assert len(rows) == 1
        assert rows[0].location_id == "hometown_market_lane"
        assert rows[0].visit_count == 1


def test_story_set_location_uses_catalog_name_and_presence(tmp_path: Path) -> None:
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
        progress = save.story_progress
        assert progress is not None
        context = StoryContext(
            background_id=save.background_id,
            current_node_id="shared_cultivator_01",
            flags=parse_flags(progress.flags_json),
            cultivation=cultivation_state_from_player(save.player),
            world_day=int(save.world_day),
        )
        result = apply_story_action(context, "travel_together")
        assert result.location_id == "jade_ridge_approach"
        assert result.location_name == "Approach to Jade Ridge"


def test_opening_flow_records_presence_for_story_locations(tmp_path: Path) -> None:
    from tests.conftest_helpers import advance_to_cultivation_hall

    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    advance_to_cultivation_hall(service, loaded.save_id)
    with service._session_factory() as session:
        rows = LocationPresenceRepository(session).list_for_save(loaded.save_id)
        ids = {row.location_id for row in rows}
        assert "hometown_market_lane" in ids
        assert "jade_ridge_approach" in ids
        assert "verdant_gate_cultivation_hall" in ids
        hall = next(row for row in rows if row.location_id == "verdant_gate_cultivation_hall")
        assert hall.visit_count >= 1



def test_migration_0008_creates_location_presence(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "loc.db"
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
        assert version == ("0012_npc_world_state",)
        tables = {
            row[0]
            for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        }
        assert "location_presence" in tables

    get_settings.cache_clear()
