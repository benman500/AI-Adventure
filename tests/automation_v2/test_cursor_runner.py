"""Tests for cursor_runner without invoking a real Cursor agent."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from automation_v2.config import load_config
from automation_v2.cursor_runner import (
    CursorNotFoundError,
    build_cursor_command,
    invoke_cursor,
    resolve_cursor_executable,
)
from automation_v2.models import CommandResult


ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_config(ROOT)


def test_build_cursor_command_uses_config_args() -> None:
    """CLI argument configuration comes from config."""
    command = build_cursor_command("agent", "hello prompt", CONFIG)
    assert command[0] == "agent"
    assert command[-1] == "hello prompt"
    for arg in CONFIG.cursor_print_args:
        assert arg in command


def test_missing_agent_executable() -> None:
    """A missing agent executable is detected clearly."""
    with patch("automation_v2.cursor_runner.shutil.which", return_value=None):
        try:
            resolve_cursor_executable(CONFIG)
            raised = False
        except CursorNotFoundError:
            raised = True
    assert raised is True


def test_invoke_cursor_writes_prompt_and_log(tmp_path: Path) -> None:
    """invoke_cursor writes the prompt file and log using process_runner."""
    fake = CommandResult(
        command=["agent", "-p", "--output-format", "text", "prompt"],
        returncode=0,
        stdout="done",
        stderr="",
        duration_seconds=0.1,
        timed_out=False,
    )
    with (
        patch(
            "automation_v2.cursor_runner.resolve_cursor_executable",
            return_value="agent",
        ),
        patch(
            "automation_v2.cursor_runner.run_command",
            return_value=fake,
        ) as mocked_run,
    ):
        result = invoke_cursor(
            prompt="Implement the task",
            run_dir=tmp_path,
            attempt=0,
            config=CONFIG,
        )

    assert result.returncode == 0
    assert result.prompt_file.exists()
    assert result.prompt_file.read_text(encoding="utf-8") == "Implement the task"
    assert result.log_file.exists()
    assert "done" in result.log_file.read_text(encoding="utf-8")
    mocked_run.assert_called_once()
    args, kwargs = mocked_run.call_args
    assert kwargs["cwd"] == CONFIG.repository_root
    assert args[0][0] == "agent"
    assert args[0][-1] == "Implement the task"
