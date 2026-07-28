"""Tests for Cursor implementation and repair prompt construction."""

from __future__ import annotations

from automation_v2.main import build_cursor_prompt
from automation_v2.models import ApprovedPlan


def _sample_plan() -> ApprovedPlan:
    return ApprovedPlan(
        decision="approve",
        title="Modernize character creation",
        implementation_brief=(
            "Inspect the existing character-creation templates and CSS, "
            "then redesign the presentation."
        ),
        allowed_areas=[
            "src/ai_adventure/presentation/templates",
            "src/ai_adventure/presentation/static",
            "tests",
        ],
        acceptance_criteria=[
            "Each character-creation question is visually separated",
            "Background choices are fully clickable cards",
            "Focused presentation tests and the full test suite pass",
        ],
        forbidden_changes=["Gameplay changes"],
        focused_tests=["tests/test_character_creation_ui.py"],
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


def _assert_no_silent_noop_rules(prompt: str) -> None:
    lower = prompt.lower()
    assert "if every acceptance criterion is already satisfied" in lower
    assert "already satisfied criteria" in lower
    assert "make meaningful changes to at least one allowed implementation" in lower
    assert "reports" in lower
    assert "automation state" in lower
    assert "run logs" in lower
    assert "automation framework" in lower


def test_implementation_prompt_forbids_temp_scripts_and_root_helpers() -> None:
    """Implementation prompts ban temp scripts and root helpers."""
    prompt = build_cursor_prompt(_sample_plan())
    _assert_script_and_temp_file_restrictions(prompt)
    assert "REVIEW REPAIRS REQUIRED:" not in prompt


def test_implementation_prompt_forbids_silent_noop_completion() -> None:
    """Implementation prompts require real work or criterion evidence."""
    prompt = build_cursor_prompt(_sample_plan())
    _assert_no_silent_noop_rules(prompt)
    lower = prompt.lower()
    assert "inspect the existing character-creation template" in lower
    assert "identify concrete deficiencies" in lower
    assert "implement the redesign" in lower
    assert "preserve" in lower
    assert "routes" in lower
    assert "form field names" in lower
    assert "submitted values" in lower
    assert "validation" in lower
    assert "gameplay" in lower
    assert "focused presentation tests" in lower
    assert "full suite" in lower or "full test suite" in lower


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


def test_repair_prompt_requires_actual_implementation_work() -> None:
    """Repair prompts include feedback, tests, files, and criteria."""
    prompt = build_cursor_prompt(
        _sample_plan(),
        repair_instructions=[
            "No allowed implementation files changed.",
            "Implement the character-creation redesign.",
        ],
        test_output="FAILED tests/test_character_creation_ui.py",
        changed_files=[],
    )
    lower = prompt.lower()
    _assert_no_silent_noop_rules(prompt)
    assert "REVIEW REPAIRS REQUIRED:" in prompt
    assert "No allowed implementation files changed." in prompt
    assert "ORIGINAL ACCEPTANCE CRITERIA:" in prompt
    assert "Each character-creation question is visually separated" in prompt
    assert "CHANGED FILES FROM PREVIOUS ATTEMPT:" in prompt
    assert "silent no-op" in lower
    assert "TEST OUTPUT FROM PREVIOUS ATTEMPT:" in prompt
    assert "FAILED tests/test_character_creation_ui.py" in prompt
    assert "rather than merely rewriting the report" in lower
    assert "make meaningful changes to at least one allowed implementation" in lower
