"""Phase 7: Spiritual Roots as second Modifier Framework source."""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from ai_adventure.config import get_settings
from ai_adventure.db.models import GameSave
from ai_adventure.engine.events import EventTemplate, effective_event_weight
from ai_adventure.engine.modifiers import ModifierContext, aggregate
from ai_adventure.engine.spiritual_roots import (
    STARTER_ROOT_ID,
    SpiritualRootOwnershipRecord,
    clear_spiritual_root_catalog_cache,
    get_spiritual_root,
    list_spiritual_roots,
    spiritual_root_ownership_to_effect_instances,
    validate_spiritual_root_catalog_against_bundles,
)
from ai_adventure.engine.techniques import (
    TechniqueMasteryRecord,
    technique_mastery_to_effect_instances,
)
from ai_adventure.services.spiritual_roots import SpiritualRootService
from ai_adventure.services.techniques import build_actor_modifier_snapshot
from tests.conftest_helpers import create_test_save


@pytest.fixture(autouse=True)
def _clear_root_cache() -> None:
    clear_spiritual_root_catalog_cache()
    yield
    clear_spiritual_root_catalog_cache()


def test_catalog_loads_and_validates_bundles() -> None:
    roots = list_spiritual_roots()
    ids = {item.id for item in roots}
    assert STARTER_ROOT_ID in ids
    assert "root_fire_qi" in ids
    assert "root_earth_attunement" in ids
    validate_spiritual_root_catalog_against_bundles()


def test_adapter_emits_spiritual_root_source_kind() -> None:
    root = get_spiritual_root(STARTER_ROOT_ID)
    instances = spiritual_root_ownership_to_effect_instances(
        [
            SpiritualRootOwnershipRecord(
                actor_id="actor-1",
                root_id=root.id,
                awakened=True,
                grade_rank=1,
            )
        ]
    )
    assert len(instances) == 1
    assert instances[0].source_kind == "spiritual_root"
    assert instances[0].bundle_id == root.effect_bundle_id


def test_root_and_technique_combine_in_aggregate() -> None:
    actor_id = "actor-1"
    root_instances = spiritual_root_ownership_to_effect_instances(
        [
            SpiritualRootOwnershipRecord(
                actor_id=actor_id,
                root_id=STARTER_ROOT_ID,
                awakened=True,
                grade_rank=1,
            )
        ]
    )
    tech_instances = technique_mastery_to_effect_instances(
        [
            TechniqueMasteryRecord(
                actor_id=actor_id,
                technique_id="tech_steady_practice",
                known=True,
                equipped=True,
                mastery_rank=1,
            )
        ]
    )
    snap = aggregate(
        [*tech_instances, *root_instances],
        ModifierContext(actor_id=actor_id, world_day=1, activity="cultivate_session"),
    )
    assert snap.number("session_progress_mult") == pytest.approx(1.10 * 1.05)
    kinds = {c.source_kind for c in snap.contributions}
    assert "technique_mastery" in kinds
    assert "spiritual_root" in kinds


def test_new_character_gets_starter_root(tmp_path: Path) -> None:
    service = create_test_save(tmp_path)
    save_id = service.list_saves()[0].save_id
    scene = service.get_play_scene(save_id)
    wood = next(r for r in scene.spiritual_roots if r["id"] == STARTER_ROOT_ID)
    assert wood["awakened"] is True


def test_session_snapshot_includes_starter_root(tmp_path: Path) -> None:
    service = create_test_save(tmp_path)
    save_id = service.list_saves()[0].save_id
    with service._session_factory() as session:  # noqa: SLF001
        save = session.get(GameSave, save_id)
        assert save is not None and save.player is not None
        snap = build_actor_modifier_snapshot(
            session,
            save_id=save_id,
            actor_id=str(save.player.actor_id),
            world_day=int(save.world_day),
            activity="cultivate_session",
        )
    assert snap.number("session_progress_mult") == pytest.approx(1.05)
    assert any(c.source_kind == "spiritual_root" for c in snap.contributions)


def test_earth_root_biases_event_weight(tmp_path: Path) -> None:
    service = create_test_save(tmp_path)
    save_id = service.list_saves()[0].save_id
    SpiritualRootService(service._session_factory).awaken_root(  # noqa: SLF001
        save_id, "root_earth_attunement"
    )
    with service._session_factory() as session:  # noqa: SLF001
        save = session.get(GameSave, save_id)
        assert save is not None and save.player is not None
        snap = build_actor_modifier_snapshot(
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
            "trigger": {"kinds": ["after_cultivation_session"], "chance": 1.0},
            "effects": [{"type": "noop", "payload": {}}],
            "presentation": {"placeholder_text": "x"},
        }
    )
    assert effective_event_weight(template, snap) == pytest.approx(10 * 1.10)


def test_consumers_never_import_spiritual_roots_for_math() -> None:
    """Guardrail: pure consumer modules must not import spiritual_roots."""

    import ai_adventure.engine.breakthroughs as breakthroughs
    import ai_adventure.engine.cultivation_sessions as sessions
    import ai_adventure.engine.events as events

    for module in (sessions, breakthroughs, events):
        source = Path(module.__file__).read_text(encoding="utf-8")
        assert "spiritual_roots" not in source
        assert "technique_mastery_to_effect" not in source


def test_migration_0010_creates_spiritual_root_ownership(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "roots.db"
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
        assert "spiritual_root_ownership" in tables

    get_settings.cache_clear()
