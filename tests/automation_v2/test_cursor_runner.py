"""Tests for cursor_runner without invoking a real Cursor agent."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from automation_v2.config import load_config
from automation_v2.cursor_runner import (
    CursorNotFoundError,
    build_cursor_command,
    invoke_cursor,
    resolve_cursor_argv_prefix,
    resolve_cursor_executable,
    unwrap_windows_cmd_wrapper,
)
from automation_v2.models import CommandResult


ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_config(ROOT)

MULTILINE_PROMPT = (
    "Implement the story-first layout.\n"
    "Keep Working Toward visible.\n"
    "Do not change gameplay."
)


def test_build_cursor_command_places_prompt_immediately_after_dash_p() -> None:
    """The complete prompt is the argument immediately following ``-p``."""
    command = build_cursor_command("agent", "hello prompt", CONFIG)

    assert command[0] == "agent"
    assert "-p" in command
    prompt_index = command.index("-p") + 1
    assert command[prompt_index] == "hello prompt"
    assert "<prompt>" not in command
    assert "{prompt}" not in command
    assert "prompt_file" not in command

    for arg in CONFIG.cursor_print_args:
        assert arg in command

    assert command[prompt_index + 1 :] == [
        arg for arg in CONFIG.cursor_print_args if arg != "-p"
    ]


def test_build_cursor_command_keeps_multiline_prompt_as_one_argument() -> None:
    """Spaces and line breaks stay inside a single argv entry."""
    command = build_cursor_command("agent", MULTILINE_PROMPT, CONFIG)

    assert MULTILINE_PROMPT in command
    assert command.count(MULTILINE_PROMPT) == 1
    prompt_index = command.index("-p") + 1
    assert command[prompt_index] == MULTILINE_PROMPT
    assert "\n" in command[prompt_index]
    assert " " in command[prompt_index]
    assert "<prompt>" not in command


def test_build_cursor_command_rejects_placeholder_prompt() -> None:
    """Literal placeholders must never become the -p argument."""
    for bad in ("<prompt>", "{prompt}", "prompt_file"):
        try:
            build_cursor_command("agent", bad, CONFIG)
            raised = False
        except ValueError:
            raised = True
        assert raised is True


def test_missing_agent_executable() -> None:
    """A missing agent executable is detected clearly."""
    with patch("automation_v2.cursor_runner.shutil.which", return_value=None):
        try:
            resolve_cursor_executable(CONFIG)
            raised = False
        except CursorNotFoundError:
            raised = True
    assert raised is True


def test_unwrap_windows_cmd_wrapper_finds_node_and_index(tmp_path: Path) -> None:
    """Windows CMD wrappers resolve to node.exe + index.js."""
    versions = tmp_path / "versions" / "2026.07.23-abc1234"
    versions.mkdir(parents=True)
    node = versions / "node.exe"
    index = versions / "index.js"
    node.write_bytes(b"")
    index.write_text("// stub", encoding="utf-8")
    cmd = tmp_path / "agent.CMD"
    cmd.write_text("@echo off\n", encoding="utf-8")

    resolved = unwrap_windows_cmd_wrapper(cmd)
    assert resolved == [str(node.resolve()), str(index.resolve())]


def test_resolve_cursor_argv_prefix_unwraps_cmd(tmp_path: Path) -> None:
    """resolve_cursor_argv_prefix avoids launching through agent.CMD."""
    versions = tmp_path / "versions" / "2026.07.23-abc1234"
    versions.mkdir(parents=True)
    node = versions / "node.exe"
    index = versions / "index.js"
    node.write_bytes(b"")
    index.write_text("// stub", encoding="utf-8")
    cmd = tmp_path / "agent.CMD"
    cmd.write_text("@echo off\n", encoding="utf-8")

    with patch(
        "automation_v2.cursor_runner.resolve_cursor_executable",
        return_value=str(cmd),
    ):
        prefix = resolve_cursor_argv_prefix(CONFIG)

    assert prefix == [str(node.resolve()), str(index.resolve())]
    assert not any(part.lower().endswith(".cmd") for part in prefix)


def test_invoke_cursor_passes_file_contents_not_placeholder(
    tmp_path: Path,
) -> None:
    """invoke_cursor reads the prompt file and passes its contents to argv."""
    fake = CommandResult(
        command=["agent", "-p", MULTILINE_PROMPT, "--output-format", "text"],
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
            "automation_v2.cursor_runner.resolve_cursor_argv_prefix",
            return_value=["agent"],
        ),
        patch(
            "automation_v2.cursor_runner.run_command",
            return_value=fake,
        ) as mocked_run,
    ):
        result = invoke_cursor(
            prompt=MULTILINE_PROMPT,
            run_dir=tmp_path,
            attempt=0,
            config=CONFIG,
        )

    assert result.returncode == 0
    assert result.prompt_file.exists()
    assert result.prompt_file.read_text(encoding="utf-8") == MULTILINE_PROMPT
    assert result.log_file.exists()
    log_text = result.log_file.read_text(encoding="utf-8")
    assert "done" in log_text
    # Displayed log may redact the prompt body.
    assert "<prompt>" in log_text
    assert "COMMAND (displayed; prompt redacted)" in log_text

    mocked_run.assert_called_once()
    args, kwargs = mocked_run.call_args
    assert kwargs["cwd"] == CONFIG.repository_root
    command = args[0]
    assert command[0] == "agent"
    assert "-p" in command
    assert command[command.index("-p") + 1] == MULTILINE_PROMPT
    assert MULTILINE_PROMPT in command
    assert "<prompt>" not in command
    assert "{prompt}" not in command
    assert "prompt_file" not in command
    assert "\n" in command[command.index("-p") + 1]
