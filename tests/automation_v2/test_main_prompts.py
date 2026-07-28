"""Tests for Cursor implementation prompt construction."""

from __future__ import annotations

from automation_v2.main import build_cursor_prompt
from automation_v2.models import ApprovedPlan


def _sample_plan() -> ApprovedPlan:
    return ApprovedPlan(
        decision="approve",
        title="Modernize character creation",
        implementation_brief="Adjust templates and CSS only.",
        allowed_areas=[
            "src/ai_adventure/presentation/templates",
            "src/ai_adventure/presentation/static",
            "tests",
        ],
        acceptance_criteria=["All tests pass"],
        forbidden_changes=["Gameplay changes"],
        focused_tests=["tests/test_play_layout_ui.py"],
        stop_conditions=["Ambiguous requirements"],
    )


def test_cursor_prompt_forbids_temporary_helper_scripts() -> None:
    """Implementation prompts must forbid ad hoc scripts and root helpers."""
    prompt = build_cursor_prompt(_sample_plan())

    assert "temporary scripts" in prompt.lower() or "helper scripts" in prompt
    assert "PowerShell" in prompt or "powershell" in prompt.lower()
    assert "batch files" in prompt.lower() or "batch file" in prompt.lower()
    assert "ad hoc test runners" in prompt.lower() or "test runners" in prompt
    assert "run_ui_tests.ps1" in prompt
    assert "project-root scripts" in prompt.lower() or "project-root" in prompt


def test_cursor_prompt_requires_direct_terminal_pytest() -> None:
    """Cursor must be told to run tests directly in the terminal."""
    prompt = build_cursor_prompt(_sample_plan())

    assert "directly through the terminal" in prompt
    assert "python -m pytest -q" in prompt
    assert "never via a newly written script" in prompt


def test_cursor_prompt_limits_temp_files_to_run_directory() -> None:
    """Temporary debugging files may only live under automation_v2 runs."""
    prompt = build_cursor_prompt(_sample_plan())

    assert "automation_v2 run directory" in prompt
    assert "repository root" in prompt
    assert "application directories" in prompt


def test_repair_prompt_keeps_script_restrictions() -> None:
    """Repair prompts retain the temporary-script restrictions."""
    prompt = build_cursor_prompt(
        _sample_plan(),
        repair_instructions=["Remove the root helper script."],
    )

    assert "REVIEW REPAIRS REQUIRED:" in prompt
    assert "Remove the root helper script." in prompt
    assert "temporary-script" in prompt or "temporary scripts" in prompt.lower()
    assert "PowerShell" in prompt or "powershell" in prompt.lower()
    assert "directly through the terminal" in prompt
