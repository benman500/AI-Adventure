from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from ai_adventure.api import create_app
from ai_adventure.config import get_settings
from ai_adventure.db.models import GameSave
from ai_adventure.engine.alchemy import (
    clear_alchemy_recipe_catalog_cache,
    validate_alchemy_recipe_catalog_against_bundles,
    alchemy_ownership_to_effect_instances,
)
from ai_adventure.engine.events import EventTemplate, effective_activation_chance, effective_event_weight
from ai_adventure.engine.modifiers import aggregate, ModifierContext
from ai_adventure.engine.modifiers import consumer_number
from ai_adventure.engine.modifiers import ModifierSnapshot
from ai_adventure.engine.constants import EVENT_TYPE_ALCHEMY_RECIPE_AWAKENED
from ai_adventure.engine.alchemy import get_alchemy_recipe
from ai_adventure.engine.modifiers import ModifierSnapshot
from ai_adventure.engine.alchemy import AlchemyRecipeOwnershipRecord
from ai_adventure.services.techniques import build_actor_modifier_snapshot
from ai_adventure.services.alchemy import AlchemyService
from ai_adventure.repositories import (
    AlchemyRecipeOwnershipRepository,
    SaveRepository,
    EventLogRepository,
)
from tests.conftest_helpers import create_test_save


@pytest.fixture(autouse=True)
def _clear_caches() -> None:
    clear_alchemy_recipe_catalog_cache()
    yield
    clear_alchemy_recipe_catalog_cache()


def test_alchemy_recipe_catalog_validates() -> None:
    validate_alchemy_recipe_catalog_against_bundles()


def test_alchemy_ownership_to_effect_instances_emits_alchemy_source_kind(
    tmp_path: Path,
) -> None:
    service = create_test_save(tmp_path)
    save_id = service.list_saves()[0].save_id

    with service._session_factory() as session:  # noqa: SLF001
        save = session.get(GameSave, save_id)
        assert save is not None and save.player is not None

        recipe_id = "alchemy_calming_draught"
        AlchemyRecipeOwnershipRepository(session).upsert_awakened(
            save_id=save_id,
            actor_id=str(save.player.actor_id),
            recipe_id=recipe_id,
            world_day=int(save.world_day),
            grade_rank=1,
        )
        session.flush()

        rows = AlchemyRecipeOwnershipRepository(session).list_for_actor(
            save_id=save_id,
            actor_id=str(save.player.actor_id),
        )
        records = AlchemyRecipeOwnershipRepository.to_engine_records(rows)
        instances = alchemy_ownership_to_effect_instances(records)

    assert len(instances) == 1
    assert instances[0].source_kind == "alchemy"
    assert instances[0].source_id == "alchemy_calming_draught"
    assert instances[0].bundle_id == "bundle_alchemy_calming_draught"


def test_snapshot_includes_alchemy_effects_for_cultivate_and_world_event(
    tmp_path: Path,
) -> None:
    service = create_test_save(tmp_path)
    save_id = service.list_saves()[0].save_id

    AlchemyService(service._session_factory).awaken_recipe(
        save_id, "alchemy_calming_draught", grade_rank=1
    )

    with service._session_factory() as session:  # noqa: SLF001
        save = session.get(GameSave, save_id)
        assert save is not None and save.player is not None

        session_snap = build_actor_modifier_snapshot(
            session,
            save_id=save_id,
            actor_id=str(save.player.actor_id),
            world_day=int(save.world_day),
            activity="cultivate_session",
        )
        world_snap = build_actor_modifier_snapshot(
            session,
            save_id=save_id,
            actor_id=str(save.player.actor_id),
            world_day=int(save.world_day),
            activity="world_event",
        )

    assert session_snap.number("session_stability_flat") == pytest.approx(2.0)
    assert world_snap.number("weight_mult", category="cultivation") == pytest.approx(1.05)
    assert world_snap.number("chance_flat", category="cultivation") == pytest.approx(0.02)


def test_alchemy_biases_event_weight_and_chance(
    tmp_path: Path,
) -> None:
    service = create_test_save(tmp_path)
    save_id = service.list_saves()[0].save_id

    AlchemyService(service._session_factory).awaken_recipe(
        save_id, "alchemy_calming_draught", grade_rank=1
    )

    with service._session_factory() as session:  # noqa: SLF001
        save = session.get(GameSave, save_id)
        assert save is not None and save.player is not None

        modifiers = build_actor_modifier_snapshot(
            session,
            save_id=save_id,
            actor_id=str(save.player.actor_id),
            world_day=int(save.world_day),
            activity="world_event",
        )

    template = EventTemplate.model_validate(
        {
            "id": "e1",
            "category": "cultivation",
            "label": "e1",
            "enabled": True,
            "weight": 10,
            "trigger": {"kinds": ["after_cultivation_session"], "chance": 0.55},
            "effects": [{"type": "noop", "payload": {}}],
            "presentation": {"placeholder_text": "x"},
        }
    )

    assert effective_event_weight(template, modifiers) == pytest.approx(10 * 1.05)
    assert effective_activation_chance(template, modifiers) == pytest.approx(0.55 + 0.02)


def test_migration_0011_creates_alchemy_recipe_ownership(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "alchemy.db"
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
            for row in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            ).fetchall()
        }
        assert "alchemy_recipe_ownership" in tables

    get_settings.cache_clear()


def test_consumers_never_import_alchemy_for_math() -> None:
    """Guardrail: pure consumer modules must not import alchemy source logic."""

    import ai_adventure.engine.breakthroughs as breakthroughs
    import ai_adventure.engine.cultivation_sessions as sessions
    import ai_adventure.engine.events as events

    for module in (sessions, breakthroughs, events):
        source = Path(module.__file__).read_text(encoding="utf-8")
        assert "engine.alchemy" not in source

