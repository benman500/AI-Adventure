"""Tests for Cursor implementation and repair prompt construction."""

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


def _assert_script_and_temp_file_restrictions(prompt: str) -> None:
    lower = prompt.lower()
    assert "powershell" in lower
    assert "batch" in lower
    assert "shell" in lower
    assert "python" in lower
    assert "ad hoc" in lower or "test-runner" in lower or "test runners" in lower
    assert ".ps1" in prompt
    assert "run_ui_tests.ps1" in prompt
    assert "project-root" in lower
    assert "directly in the terminal" in lower
    assert "python -m pytest -q" in prompt
    assert "automation_v2 run directory" in prompt
    assert "repository root" in lower
    assert "application directories" in lower
    assert "guardrails" in lower


def test_implementation_prompt_forbids_temp_scripts_and_root_helpers() -> None:
    """Implementation prompts ban temp scripts and root helpers."""
    prompt = build_cursor_prompt(_sample_plan())
    _assert_script_and_temp_file_restrictions(prompt)
    assert "REVIEW REPAIRS REQUIRED:" not in prompt


def test_repair_prompt_includes_same_script_restrictions() -> None:
    """Repair prompts keep the same script and diagnostic-file bans."""
    prompt = build_cursor_prompt(
        _sample_plan(),
        repair_instructions=["Remove the root helper script."],
    )
    assert "REVIEW REPAIRS REQUIRED:" in prompt
    assert "Remove the root helper script." in prompt
    _assert_script_and_temp_file_restrictions(prompt)
    assert "still apply during repair" in prompt.lower()
