"""Phase 4a: event engine core, catalog validation, WorldClock, actor_id, cooldowns."""

from __future__ import annotations

import json
from pathlib import Path
from random import Random

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from ai_adventure.config import get_settings
from ai_adventure.db import models as _models  # noqa: F401
from ai_adventure.engine.actors import ActorRef, actor_ref_from_player
from ai_adventure.engine.constants import (
    PATH_STATUS_CONFIRMED_ORDINARY,
    PATH_STATUS_PROVISIONAL,
    STARTING_BODY,
    STARTING_CULTIVATION_PATH,
    STARTING_DAO,
    STARTING_FOUNDATION_QUALITY,
    STARTING_FOUNDATION_STABILITY,
    STARTING_QI,
    STARTING_REALM_COMPREHENSION,
    STARTING_REALM_ID,
    STARTING_SOUL,
    STARTING_STAGE_ID,
)
from ai_adventure.engine.cultivation_state import CultivationState
from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.events import (
    CooldownState,
    EventContext,
    clear_event_catalog_cache,
    evaluate_trigger,
    load_event_catalog,
    resolution_to_event_log_payload,
)
from ai_adventure.engine.time import advance_world_days, current_world_day
from ai_adventure.repositories.events import EventCooldownRepository
from ai_adventure.repositories.saves import SaveRepository
from tests.conftest_helpers import VALID_IDENTITY_ANSWERS, make_service


def _base_state(**overrides: object) -> CultivationState:
    data = {
        "cultivation_path": STARTING_CULTIVATION_PATH,
        "path_status": PATH_STATUS_CONFIRMED_ORDINARY,
        "realm_id": STARTING_REALM_ID,
        "stage_id": STARTING_STAGE_ID,
        "body": STARTING_BODY,
        "qi": STARTING_QI,
        "soul": STARTING_SOUL,
        "dao": STARTING_DAO,
        "foundation_quality": STARTING_FOUNDATION_QUALITY,
        "qi_reserve_current": 5,
        "qi_reserve_max": 10,
        "cultivation_progress": 40,
        "realm_comprehension": STARTING_REALM_COMPREHENSION,
        "foundation_stability": STARTING_FOUNDATION_STABILITY,
        "practice_sessions": 0,
        "anomaly_state": "none",
        "breakthrough_readiness": "not_ready",
        "breakthrough_attempts_current_stage": 0,
    }
    data.update(overrides)
    return CultivationState(**data)  # type: ignore[arg-type]


def _write_catalog(tmp_path: Path, events: list[dict]) -> Path:
    root = tmp_path / "events"
    root.mkdir()
    (root / "seed.json").write_text(
        json.dumps({"schema_version": 1, "events": events}, indent=2),
        encoding="utf-8",
    )
    (root / "event_manifest.json").write_text(
        json.dumps({"content_files": ["seed.json"]}),
        encoding="utf-8",
    )
    clear_event_catalog_cache()
    return root


def _template(
    *,
    event_id: str = "evt_test_insight",
    weight: int = 10,
    chance: float = 1.0,
    cooldown_days: int = 0,
    max_fires_per_save: int | None = None,
    path_status_in: list[str] | None = None,
    effects: list[dict] | None = None,
    category: str = "cultivation",
    kinds: list[str] | None = None,
) -> dict:
    return {
        "id": event_id,
        "category": category,
        "label": "Test Event",
        "enabled": True,
        "weight": weight,
        "cooldown_days": cooldown_days,
        "max_fires_per_save": max_fires_per_save,
        "trigger": {
            "kinds": kinds or ["after_cultivation_session"],
            "chance": chance,
        },
        "requirements": {
            "path_status_in": path_status_in
            if path_status_in is not None
            else [PATH_STATUS_CONFIRMED_ORDINARY],
            "subject_must_be_player": True,
        },
        "context": {
            "location_tags": [],
            "weather_tags": [],
            "time_tags": [],
            "cultivation_tags": [],
            "npc_tags": [],
            "environment_tags": [],
        },
        "effects": effects
        if effects is not None
        else [
            {
                "type": "modify_cultivation",
                "payload": {"realm_comprehension_delta": 2},
            }
        ],
        "presentation": {
            "placeholder_text": "A fleeting insight settles.",
            "narration_keys": ["test"],
        },
    }


def test_empty_production_catalog_loads() -> None:
    clear_event_catalog_cache()
    catalog = load_event_catalog()
    ids = {item.id for item in catalog.events}
    assert "evt_quiet_breath_insight" in ids
    assert "evt_exploration_stub_ridge_path" in ids
    assert "evt_spirit_mist_drift" in ids
    cultivation = [
        e for e in catalog.events if "after_cultivation_session" in e.trigger.kinds
    ]
    assert len(cultivation) >= 10


def test_catalog_rejects_unknown_effect_type(tmp_path: Path) -> None:
    root = _write_catalog(
        tmp_path,
        [_template(effects=[{"type": "grant_technique", "payload": {}}])],
    )
    with pytest.raises(EngineValidationError, match="Invalid event file"):
        load_event_catalog(str(root))


def test_catalog_rejects_malformed_json(tmp_path: Path) -> None:
    root = tmp_path / "events"
    root.mkdir()
    (root / "event_manifest.json").write_text(
        json.dumps({"content_files": ["bad.json"]}),
        encoding="utf-8",
    )
    (root / "bad.json").write_text("{not json", encoding="utf-8")
    clear_event_catalog_cache()
    with pytest.raises(EngineValidationError, match="Corrupted event file"):
        load_event_catalog(str(root))


def test_world_clock_advance_and_reject_negative() -> None:
    assert current_world_day(3) == 3
    assert advance_world_days(3, 2) == 5
    with pytest.raises(EngineValidationError):
        advance_world_days(3, -1)
    with pytest.raises(EngineValidationError):
        current_world_day(0)


def test_evaluate_empty_catalog_returns_structured_no_event(tmp_path: Path) -> None:
    root = tmp_path / "events"
    root.mkdir()
    (root / "event_manifest.json").write_text(
        json.dumps({"content_files": []}),
        encoding="utf-8",
    )
    clear_event_catalog_cache()
    context = EventContext(
        save_id="save-1",
        subject=ActorRef(actor_id="actor-1", kind="player"),
        world_day=5,
        location_id="loc",
        story_flags={},
        cultivation=_base_state(),
        money_copper=10,
        trigger_kind="after_cultivation_session",
    )
    batch = evaluate_trigger(context, rng=Random(1), events_dir=str(root))
    assert batch.max_events == 1
    assert len(batch.slots) == 1
    assert batch.fired is False
    assert batch.first_no_event is not None
    assert batch.first_no_event.reason == "empty_catalog"


def test_weighted_selection_then_chance_miss(tmp_path: Path) -> None:
    root = _write_catalog(tmp_path, [_template(chance=0.0)])
    context = EventContext(
        save_id="save-1",
        subject=ActorRef(actor_id="actor-1", kind="player"),
        world_day=5,
        location_id="loc",
        story_flags={},
        cultivation=_base_state(),
        money_copper=10,
        trigger_kind="after_cultivation_session",
    )
    batch = evaluate_trigger(context, rng=Random(99), events_dir=str(root))
    assert batch.fired is False
    assert batch.first_no_event is not None
    assert batch.first_no_event.reason == "chance_missed"
    assert batch.first_no_event.facts["selected_template_id"] == "evt_test_insight"


def test_deterministic_selection_with_injected_rng(tmp_path: Path) -> None:
    root = _write_catalog(
        tmp_path,
        [
            _template(event_id="evt_a", weight=1, chance=1.0),
            _template(event_id="evt_b", weight=1000, chance=1.0),
        ],
    )
    context = EventContext(
        save_id="save-1",
        subject=ActorRef(actor_id="actor-1", kind="player"),
        world_day=5,
        location_id="loc",
        story_flags={},
        cultivation=_base_state(),
        money_copper=10,
        trigger_kind="after_cultivation_session",
    )
    first = evaluate_trigger(context, rng=Random(42), events_dir=str(root))
    second = evaluate_trigger(context, rng=Random(42), events_dir=str(root))
    assert first.fired and second.fired
    assert first.first_resolution is not None
    assert second.first_resolution is not None
    assert first.first_resolution.template_id == second.first_resolution.template_id


def test_provisional_path_not_eligible_by_default(tmp_path: Path) -> None:
    root = _write_catalog(tmp_path, [_template()])
    context = EventContext(
        save_id="save-1",
        subject=ActorRef(actor_id="actor-1", kind="player"),
        world_day=5,
        location_id="loc",
        story_flags={},
        cultivation=_base_state(path_status=PATH_STATUS_PROVISIONAL),
        money_copper=10,
        trigger_kind="after_cultivation_session",
    )
    batch = evaluate_trigger(context, rng=Random(1), events_dir=str(root))
    assert batch.fired is False
    assert batch.first_no_event is not None
    assert batch.first_no_event.reason == "no_eligible"


def test_effects_clamp_cultivation_meters(tmp_path: Path) -> None:
    root = _write_catalog(
        tmp_path,
        [
            _template(
                effects=[
                    {
                        "type": "modify_cultivation",
                        "payload": {
                            "qi_reserve_delta": 100,
                            "realm_comprehension_delta": 100,
                            "foundation_stability_delta": -200,
                        },
                    }
                ]
            )
        ],
    )
    context = EventContext(
        save_id="save-1",
        subject=ActorRef(actor_id="actor-1", kind="player"),
        world_day=5,
        location_id="loc",
        story_flags={},
        cultivation=_base_state(qi_reserve_current=8, foundation_stability=10),
        money_copper=10,
        trigger_kind="after_cultivation_session",
    )
    batch = evaluate_trigger(context, rng=Random(1), events_dir=str(root))
    resolution = batch.first_resolution
    assert resolution is not None
    assert resolution.cultivation.qi_reserve_current == 10
    assert resolution.cultivation.realm_comprehension == 100
    assert resolution.cultivation.foundation_stability == 0
    payload = resolution_to_event_log_payload(resolution)
    assert payload["event_template_id"] == "evt_test_insight"
    assert payload["presentation_authoritative"] is False
    assert "effects_applied" in payload


def test_one_time_and_cooldown_semantics(tmp_path: Path) -> None:
    root = _write_catalog(
        tmp_path,
        [
            _template(
                event_id="evt_once",
                max_fires_per_save=1,
                cooldown_days=0,
                chance=1.0,
            )
        ],
    )
    cool = CooldownState(
        event_template_id="evt_once",
        subject_actor_id="actor-1",
        last_fired_world_day=3,
        fire_count=1,
    )
    context = EventContext(
        save_id="save-1",
        subject=ActorRef(actor_id="actor-1", kind="player"),
        world_day=10,
        location_id="loc",
        story_flags={},
        cultivation=_base_state(),
        money_copper=10,
        trigger_kind="after_cultivation_session",
        cooldowns=(cool,),
    )
    batch = evaluate_trigger(context, rng=Random(1), events_dir=str(root))
    assert batch.fired is False
    assert batch.first_no_event is not None
    assert batch.first_no_event.reason == "no_eligible"


def test_cooldown_blocks_until_day_elapses(tmp_path: Path) -> None:
    root = _write_catalog(
        tmp_path,
        [_template(event_id="evt_cool", cooldown_days=5, chance=1.0)],
    )
    cool = CooldownState(
        event_template_id="evt_cool",
        subject_actor_id="actor-1",
        last_fired_world_day=10,
        fire_count=1,
    )
    blocked = EventContext(
        save_id="save-1",
        subject=ActorRef(actor_id="actor-1", kind="player"),
        world_day=14,
        location_id="loc",
        story_flags={},
        cultivation=_base_state(),
        money_copper=10,
        trigger_kind="after_cultivation_session",
        cooldowns=(cool,),
    )
    ready = EventContext(
        save_id="save-1",
        subject=ActorRef(actor_id="actor-1", kind="player"),
        world_day=15,
        location_id="loc",
        story_flags={},
        cultivation=_base_state(),
        money_copper=10,
        trigger_kind="after_cultivation_session",
        cooldowns=(cool,),
    )
    assert evaluate_trigger(blocked, rng=Random(1), events_dir=str(root)).fired is False
    assert evaluate_trigger(ready, rng=Random(1), events_dir=str(root)).fired is True


def test_actor_id_backfill_on_new_save(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Actor Test",
        background_id="hunter",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    with service._session_factory() as session:  # noqa: SLF001
        save = SaveRepository(session).get_with_player(loaded.save_id)
        assert save is not None and save.player is not None
        assert save.player.actor_id == save.player.id
        assert save.world_rng_counter == 0
        ref = actor_ref_from_player(save.player)
        assert ref.kind == "player"
        assert ref.actor_id == save.player.id


def test_event_cooldown_repository_upsert(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    loaded = service.create_new_game(
        character_name="Cool",
        background_id="hunter",
        identity_answers=VALID_IDENTITY_ANSWERS,
    )
    with service._session_factory() as session:  # noqa: SLF001
        save = SaveRepository(session).get_with_player(loaded.save_id)
        assert save is not None and save.player is not None
        repo = EventCooldownRepository(session)
        row = repo.record_fire(
            save_id=save.id,
            event_template_id="evt_test",
            subject_actor_id=save.player.actor_id,
            world_day=7,
        )
        assert row.fire_count == 1
        assert row.last_fired_world_day == 7
        row2 = repo.record_fire(
            save_id=save.id,
            event_template_id="evt_test",
            subject_actor_id=save.player.actor_id,
            world_day=12,
        )
        assert row2.fire_count == 2
        assert row2.last_fired_world_day == 12
        states = repo.cooldown_states_for_save(save.id)
        assert len(states) == 1
        assert states[0].fire_count == 2
        session.commit()


def test_migration_0007_adds_event_engine_schema(tmp_path: Path, monkeypatch) -> None:
    db2 = tmp_path / "mig2.db"
    url2 = f"sqlite:///{db2.as_posix()}"
    monkeypatch.setenv("AI_ADVENTURE_DATABASE_URL", url2)
    get_settings.cache_clear()

    root = Path(__file__).resolve().parents[1]
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url2)
    command.upgrade(cfg, "0007_event_engine")

    engine = create_engine(url2, future=True)
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
        assert version == ("0007_event_engine",)
        player_cols = {
            row[1] for row in conn.execute(text("PRAGMA table_info(players)")).fetchall()
        }
        save_cols = {
            row[1] for row in conn.execute(text("PRAGMA table_info(game_saves)")).fetchall()
        }
        tables = {
            row[0]
            for row in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            ).fetchall()
        }
        assert "actor_id" in player_cols
        assert "world_rng_counter" in save_cols
        assert "event_cooldowns" in tables
    engine.dispose()
    get_settings.cache_clear()


def test_batch_api_allows_future_multi_event_shape(tmp_path: Path) -> None:
    """max_events>1 is accepted for forward compatibility (still one pass each)."""

    root = _write_catalog(tmp_path, [_template(chance=1.0)])
    context = EventContext(
        save_id="save-1",
        subject=ActorRef(actor_id="actor-1", kind="player"),
        world_day=5,
        location_id="loc",
        story_flags={},
        cultivation=_base_state(),
        money_copper=10,
        trigger_kind="after_cultivation_session",
        max_events=2,
    )
    batch = evaluate_trigger(context, rng=Random(1), events_dir=str(root))
    assert batch.max_events == 2
    assert len(batch.slots) == 2
