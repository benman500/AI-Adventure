"""Tests for automation_v2.state_manager."""

from __future__ import annotations

from pathlib import Path

from automation_v2.models import AutomationState
from automation_v2.state_manager import StateManager


def test_state_save_and_resume(tmp_path: Path) -> None:
    """State survives atomic save and can be reloaded after a crash."""
    state_file = tmp_path / "state.json"
    manager = StateManager(state_file)

    state = AutomationState(
        task_id="ui-01",
        current_stage="implementing",
        attempt_number=1,
        last_successful_stage="planning",
        last_error=None,
        started_at="2026-07-28T00:00:00+00:00",
        completed_tasks=[],
        run_dir=str(tmp_path / "runs" / "x-ui-01"),
        repair_instructions=["fix spacing"],
    )
    manager.save(state)

    assert state_file.exists()
    assert not state_file.with_name("state.json.tmp").exists()

    reloaded = manager.load()
    assert reloaded.task_id == "ui-01"
    assert reloaded.current_stage == "implementing"
    assert reloaded.attempt_number == 1
    assert reloaded.last_successful_stage == "planning"
    assert reloaded.repair_instructions == ["fix spacing"]
    assert reloaded.run_dir == state.run_dir


def test_set_stage_persists(tmp_path: Path) -> None:
    """set_stage updates and persists current/last-successful stage."""
    manager = StateManager(tmp_path / "state.json")
    state = AutomationState(task_id="ui-01", current_stage="queued")
    manager.set_stage(state, "planning")
    manager.set_stage(state, "planning", mark_successful=True)

    reloaded = manager.load()
    assert reloaded.current_stage == "planning"
    assert reloaded.last_successful_stage == "planning"


def test_missing_state_file_returns_idle(tmp_path: Path) -> None:
    """A missing state file loads as idle queued state."""
    manager = StateManager(tmp_path / "missing.json")
    state = manager.load()
    assert state.task_id is None
    assert state.current_stage == "queued"
    assert state.completed_tasks == []
