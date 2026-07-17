"""Developer tooling for the event catalog."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ai_adventure.api import create_app
from ai_adventure.config import Settings
from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.event_devtools import (
    assert_event_catalog_valid,
    collect_event_stats,
    inspect_event,
    list_event_summaries,
    simulate_trigger,
    validate_event_catalog,
)
from ai_adventure.cli.events import main as events_cli_main
from tests.conftest_helpers import prepare_test_database


def _write_catalog(tmp_path: Path, *, events: list[dict], files: dict[str, list[dict]] | None = None) -> Path:
    root = tmp_path / "events"
    root.mkdir()
    if files is None:
        files = {"seed.json": events}
    manifest_files = []
    for name, payload_events in files.items():
        (root / name).write_text(
            json.dumps({"schema_version": 1, "events": payload_events}, indent=2),
            encoding="utf-8",
        )
        manifest_files.append(name)
    (root / "event_manifest.json").write_text(
        json.dumps({"content_files": manifest_files}),
        encoding="utf-8",
    )
    return root


def _minimal_event(event_id: str = "evt_a", **overrides: object) -> dict:
    base = {
        "id": event_id,
        "category": "cultivation",
        "label": "A",
        "enabled": True,
        "weight": 10,
        "cooldown_days": 0,
        "max_fires_per_save": None,
        "trigger": {"kinds": ["after_cultivation_session"], "chance": 1.0},
        "requirements": {
            "path_status_in": ["confirmed_ordinary"],
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
        "effects": [{"type": "noop", "payload": {}}],
        "presentation": {"placeholder_text": "Text.", "narration_keys": []},
        "ai_prompt_key": event_id,
    }
    base.update(overrides)
    return base


def test_production_catalog_validates() -> None:
    report = validate_event_catalog()
    assert report.ok
    assert report.event_count >= 15
    stats = collect_event_stats()
    assert stats.total_events == report.event_count
    assert "after_cultivation_session" in stats.by_trigger_kind


def test_duplicate_event_id_detected(tmp_path: Path) -> None:
    root = _write_catalog(
        tmp_path,
        events=[],
        files={
            "a.json": [_minimal_event("evt_dup")],
            "b.json": [_minimal_event("evt_dup")],
        },
    )
    report = validate_event_catalog(root)
    assert report.ok is False
    assert any(i.code == "duplicate_event_id" for i in report.errors)


def test_invalid_effect_payload_detected(tmp_path: Path) -> None:
    root = _write_catalog(
        tmp_path,
        events=[
            _minimal_event(
                effects=[{"type": "modify_cultivation", "payload": {"hp_delta": 1}}],
            )
        ],
    )
    report = validate_event_catalog(root)
    assert report.ok is False
    assert any(i.code == "invalid_effect_payload" for i in report.errors)


def test_orphan_file_warning(tmp_path: Path) -> None:
    root = _write_catalog(tmp_path, events=[_minimal_event()])
    (root / "orphan.json").write_text(
        json.dumps({"schema_version": 1, "events": []}),
        encoding="utf-8",
    )
    report = validate_event_catalog(root)
    assert report.ok
    assert any(i.code == "orphan_event_file" for i in report.warnings)


def test_inspect_and_list() -> None:
    assert_event_catalog_valid()
    rows = list_event_summaries(trigger_kind="after_cultivation_session", enabled_only=True)
    assert rows
    first = inspect_event(rows[0]["id"])
    assert first["template"]["id"] == rows[0]["id"]
    assert "context" in first["template"]
    assert "ai_prompt_key" in first["template"]


def test_simulate_trigger_deterministic() -> None:
    a = simulate_trigger("after_cultivation_session", trials=200, seed=42)
    b = simulate_trigger("after_cultivation_session", trials=200, seed=42)
    assert a.fire_count == b.fire_count
    assert a.by_template == b.by_template
    assert 0.0 <= a.fire_rate <= 1.0


def test_startup_validation_blocks_bad_catalog(tmp_path: Path) -> None:
    root = _write_catalog(
        tmp_path,
        events=[],
        files={
            "a.json": [_minimal_event("evt_x")],
            "b.json": [_minimal_event("evt_x")],
        },
    )
    # Point packaged loader via monkeypatch of events dir used by assert.
    from ai_adventure.engine import event_devtools as tools

    original = tools._EVENTS_DIR
    tools._EVENTS_DIR = root  # type: ignore[misc]
    from ai_adventure.engine import events as events_mod

    original_events_dir = events_mod._EVENTS_DIR
    events_mod._EVENTS_DIR = root  # type: ignore[misc]
    events_mod.clear_event_catalog_cache()
    try:
        with pytest.raises(EngineValidationError, match="Duplicate|validation failed"):
            create_app(
                Settings(
                    database_url=f"sqlite:///{(tmp_path / 'x.db').as_posix()}",
                    validate_event_catalog_on_startup=True,
                    narrator_backend="stub",
                )
            )
    finally:
        tools._EVENTS_DIR = original  # type: ignore[misc]
        events_mod._EVENTS_DIR = original_events_dir  # type: ignore[misc]
        events_mod.clear_event_catalog_cache()


def test_debug_routes_when_debug_enabled(tmp_path: Path) -> None:
    db_path = tmp_path / "debug.db"
    prepare_test_database(f"sqlite:///{db_path.as_posix()}")
    app = create_app(
        Settings(
            database_url=f"sqlite:///{db_path.as_posix()}",
            debug=True,
            validate_event_catalog_on_startup=True,
            narrator_backend="stub",
        )
    )
    client = TestClient(app)
    assert client.get("/debug/events/validate").status_code == 200
    assert client.get("/debug/events/stats").json()["total_events"] >= 15
    assert client.get("/debug/events/list").status_code == 200
    sim = client.get("/debug/events/simulate/after_cultivation_session?trials=50&seed=1")
    assert sim.status_code == 200
    assert "fire_rate" in sim.json()


def test_cli_validate_and_stats(capsys: pytest.CaptureFixture[str]) -> None:
    assert events_cli_main(["validate"]) == 0
    out = capsys.readouterr().out
    assert '"ok": true' in out
    assert events_cli_main(["stats"]) == 0
    assert events_cli_main(["simulate", "after_cultivation_session", "--trials", "20"]) == 0
