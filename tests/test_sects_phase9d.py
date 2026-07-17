"""Phase 9d: sect membership lifecycle + institutional standing."""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from ai_adventure.config import get_settings
from ai_adventure.engine.constants import EVENT_TYPE_SECT_JOINED
from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.locations import clear_location_catalog_cache
from ai_adventure.engine.npcs import clear_npc_catalog_cache, get_npc, plan_npc_interaction
from ai_adventure.engine.npcs import NpcWorldStateRecord
from ai_adventure.engine.sects import (
    assert_sect_catalog_valid,
    clear_sect_catalog_cache,
    get_sect,
    plan_sect_join,
)
from ai_adventure.repositories.sects import SectRepository, SectStandingRepository
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


def test_sect_catalog_includes_authored_initial_standing() -> None:
    assert_sect_catalog_valid()
    sect = get_sect("sect_verdant_gate")
    assert sect.initial_standing == 5
    assert sect.min_standing_to_join == 0
    assert "outer_disciple" in sect.ranks_by_id


def test_plan_sect_join_seeds_initial_standing() -> None:
    plan = plan_sect_join(
        sect_id="sect_verdant_gate",
        rank_id="outer_disciple",
        current_membership_sect_id=None,
        current_membership_rank_id=None,
        current_standing=1,
        waive_standing_gate=True,
    )
    assert plan.standing_score == 5
    assert plan.seeded_standing is True


def test_plan_sect_join_rejects_unknown_rank() -> None:
    with pytest.raises(EngineValidationError, match="Unknown rank"):
        plan_sect_join(
            sect_id="sect_verdant_gate",
            rank_id="peak_lord",
            current_membership_sect_id=None,
            current_membership_rank_id=None,
            current_standing=None,
            waive_standing_gate=True,
        )


def test_plan_sect_join_rejects_multi_sect() -> None:
    with pytest.raises(EngineValidationError, match="multi-sect"):
        plan_sect_join(
            sect_id="sect_verdant_gate",
            rank_id="outer_disciple",
            current_membership_sect_id="sect_other",
            current_membership_rank_id="outer_disciple",
            current_standing=None,
            waive_standing_gate=True,
        )


def test_plan_sect_join_enforces_min_standing() -> None:
    sect = get_sect("sect_verdant_gate")
    from ai_adventure.engine.sects import SectCatalog, SectDefinition

    gated = SectDefinition(
        sect_id=sect.sect_id,
        display_name=sect.display_name,
        home_location_id=sect.home_location_id,
        description=sect.description,
        ranks=list(sect.ranks),
        initial_standing=0,
        min_standing_to_join=10,
    )
    catalog = SectCatalog(sects=[gated], pack_ids=["test"])
    with pytest.raises(EngineValidationError, match="below join requirement"):
        plan_sect_join(
            sect_id=sect.sect_id,
            rank_id="outer_disciple",
            current_membership_sect_id=None,
            current_membership_rank_id=None,
            current_standing=None,
            waive_standing_gate=False,
            catalog=catalog,
        )
    ok = plan_sect_join(
        sect_id=sect.sect_id,
        rank_id="outer_disciple",
        current_membership_sect_id=None,
        current_membership_rank_id=None,
        current_standing=None,
        waive_standing_gate=True,
        catalog=catalog,
    )
    assert ok.standing_score == 0


def test_migration_0013_creates_sect_standing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "migrate.db"
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
        assert "sect_standing" in tables

    get_settings.cache_clear()


def test_story_join_seeds_standing_and_ui(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    advance_to_cultivation_hall(service, loaded.save_id)
    scene = service.get_play_scene(loaded.save_id)
    assert scene.sect_membership is not None
    assert scene.sect_membership["sect_id"] == "sect_verdant_gate"
    assert scene.sect_membership["rank_id"] == "outer_disciple"
    assert scene.sect_membership["standing_score"] == 5
    assert "Verdant Gate" in scene.sect_membership["display_name"]

    events = service.list_events_for_save(loaded.save_id)
    assert any(e["event_type"] == EVENT_TYPE_SECT_JOINED for e in events)

    with service._session_factory() as session:  # noqa: SLF001
        membership = SectRepository(session).get_for_save(loaded.save_id)
        standing = SectStandingRepository(session).get(
            loaded.save_id, "sect_verdant_gate"
        )
        assert membership is not None
        assert standing is not None
        assert int(standing.standing_score) == 5


def test_greet_applies_authored_sect_standing_delta(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    advance_to_cultivation_hall(service, loaded.save_id)

    scene = service.interact_with_npc(loaded.save_id, "npc_instructor_001", "greet")
    assert scene.sect_membership is not None
    assert scene.sect_membership["standing_score"] == 6  # 5 initial + 1 greet

    pei = next(n for n in scene.present_npcs if n["npc_id"] == "npc_instructor_001")
    assert pei["relationship_score"] == 5
    assert pei["sect_standing_score"] == 6


def test_ask_guidance_on_elder_requires_authored_standing(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    advance_to_cultivation_hall(service, loaded.save_id)

    # Move to foundation hall and ensure elder is spawned via travel/story if needed.
    # Elder Yun Mei defaults to foundation hall; spawn ensure + location change.
    with service._session_factory() as session:  # noqa: SLF001
        from ai_adventure.services.npcs import NpcService
        from ai_adventure.repositories.saves import SaveRepository

        NpcService(service._session_factory).ensure_spawned(  # noqa: SLF001
            session,
            save_id=loaded.save_id,
            npc_id="npc_foundation_elder_001",
        )
        save = SaveRepository(session).get_with_player(loaded.save_id)
        assert save is not None and save.player is not None
        save.player.current_location_id = "verdant_gate_foundation_hall"
        save.player.current_location_name = "Verdant Gate — Foundation Hall"
        save.current_location_id = "verdant_gate_foundation_hall"
        save.current_location_name = "Verdant Gate — Foundation Hall"
        session.commit()

    # Standing 5 < elder gate 7
    with pytest.raises(EngineValidationError, match="below the requirement"):
        service.interact_with_npc(
            loaded.save_id, "npc_foundation_elder_001", "ask_guidance"
        )

    # Build standing via greets (+1 each) until gate passes
    service.interact_with_npc(loaded.save_id, "npc_foundation_elder_001", "greet")
    service.interact_with_npc(loaded.save_id, "npc_foundation_elder_001", "greet")
    scene = service.interact_with_npc(
        loaded.save_id, "npc_foundation_elder_001", "ask_guidance"
    )
    assert scene.sect_membership is not None
    # 5 + 1 + 1 + 2 = 9
    assert scene.sect_membership["standing_score"] == 9


def test_instructor_ask_guidance_still_works_at_initial_standing(tmp_path: Path) -> None:
    """Non-elder roles are not gated by min_sect_standing_by_role."""

    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    advance_to_cultivation_hall(service, loaded.save_id)
    scene = service.interact_with_npc(
        loaded.save_id, "npc_instructor_001", "ask_guidance"
    )
    assert scene.sect_membership is not None
    assert scene.sect_membership["standing_score"] == 7  # 5 + 2


def test_plan_npc_standing_delta_deterministic() -> None:
    from ai_adventure.engine.npcs import NpcInteractionPlayerContext

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
        action_id="greet",
    )
    second = plan_npc_interaction(
        definition=definition,
        state=state,
        player=player,
        action_id="greet",
    )
    assert first == second
    assert first.sect_standing_before == 5
    assert first.sect_standing_after == 6
    assert first.sect_standing_delta == 1


def test_standing_persists_across_reload(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Lin Wei",
        background_id="merchant_family",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    advance_to_cultivation_hall(service, loaded.save_id)
    service.interact_with_npc(loaded.save_id, "npc_instructor_001", "greet")

    reloaded = service.get_play_scene(loaded.save_id)
    assert reloaded.sect_membership is not None
    assert reloaded.sect_membership["standing_score"] == 6
