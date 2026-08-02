"""Tests for automation_v2.test_runner focused-test normalization."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

from automation_v2.config import load_config
from automation_v2.models import CommandResult, TestResult
from automation_v2.test_runner import (
    focused_targets_for_run,
    normalize_focused_test_entry,
    normalize_focused_tests,
    run_focused_tests,
    run_tests,
)


ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_config(ROOT)


def _fake_result(command: list[str], *, returncode: int = 0) -> CommandResult:
    return CommandResult(
        command=command,
        returncode=returncode,
        stdout="ok",
        stderr="",
        duration_seconds=0.01,
        timed_out=False,
    )


def test_normalize_strips_full_pytest_command_string() -> None:
    """Full command strings must not become one pytest path argument."""
    tokens = normalize_focused_test_entry("python -m pytest -q tests")
    assert tokens == ["tests"]
    assert "python -m pytest -q tests" not in tokens
    assert "python" not in tokens


def test_normalize_plain_target() -> None:
    """Bare file targets pass through unchanged."""
    assert normalize_focused_test_entry("tests/test_play_layout_ui.py") == [
        "tests/test_play_layout_ui.py"
    ]


def test_normalize_path_with_k_expression() -> None:
    """Path plus -k expression becomes separate argv elements."""
    entry = 'tests -k "character_creation or character_create"'
    tokens = normalize_focused_test_entry(entry)
    assert tokens == [
        "tests",
        "-k",
        "character_creation or character_create",
    ]
    assert entry not in tokens
    assert 'tests -k "character_creation or character_create"' not in tokens


def test_normalize_keeps_node_id_as_one_target() -> None:
    """Pytest node ids remain a single argv element."""
    node = "tests/test_play_layout_ui.py::test_specific_behavior"
    assert normalize_focused_test_entry(node) == [node]


def test_normalize_multiple_focused_targets() -> None:
    """Multiple planner entries expand into multiple targets."""
    targets = normalize_focused_tests(
        [
            "tests/test_play_layout_ui.py",
            "python -m pytest -q tests/test_other.py",
            "tests/test_play_layout_ui.py::test_specific_behavior",
            'tests -k "character_creation or character_create"',
        ]
    )
    assert targets == [
        "tests/test_play_layout_ui.py",
        "tests/test_other.py",
        "tests/test_play_layout_ui.py::test_specific_behavior",
        "tests",
        "-k",
        "character_creation or character_create",
    ]


def test_run_focused_tests_splits_k_expression_args(tmp_path: Path) -> None:
    """Focused runner must not pass the whole -k spec as one path."""
    captured: dict[str, list[str]] = {}

    def fake_run(args: list[str], **kwargs: object) -> CommandResult:
        captured["args"] = list(args)
        return _fake_result(args)

    with patch("automation_v2.test_runner.run_command", side_effect=fake_run):
        result = run_focused_tests(
            ['tests -k "character_creation or character_create"'],
            run_dir=tmp_path,
            config=CONFIG,
        )

    assert result is not None
    assert result.passed is True
    args = captured["args"]
    assert args == [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "tests",
        "-k",
        "character_creation or character_create",
    ]


def test_empty_or_options_only_focused_tests_are_skipped() -> None:
    """Empty / options-only entries skip the focused stage."""
    assert focused_targets_for_run([]) == []
    assert focused_targets_for_run(["python -m pytest -q"]) == []
    assert focused_targets_for_run(["  ", "python -m pytest -q"]) == []


def test_unsafe_shell_syntax_is_rejected() -> None:
    """Pipes, redirects, and chained commands are rejected."""
    for bad in (
        "python -m pytest -q tests | tee out.txt",
        "python -m pytest -q tests && rm -rf /",
        "pytest tests; echo hacked",
        "python -m pytest -q tests > out.txt",
        "powershell -Command Get-ChildItem",
        "cmd.exe /c dir",
        "bash -lc 'pytest'",
    ):
        try:
            normalize_focused_test_entry(bad)
            raised = False
        except ValueError:
            raised = True
        assert raised is True, bad


def test_prose_focused_entry_is_rejected_not_run_as_filename() -> None:
    """Instructional prose must not become a pytest path like 'Run'."""
    prose = (
        "Run the existing presentation/template test module "
        "for character creation"
    )
    try:
        tokens = normalize_focused_test_entry(prose)
        raised = False
    except ValueError:
        tokens = []
        raised = True
    assert raised is True
    assert "Run" not in tokens


def test_run_focused_tests_builds_argv_list_not_one_path(
    tmp_path: Path,
) -> None:
    """Focused runner invokes sys.executable -m pytest with split targets."""
    captured: dict[str, list[str]] = {}

    def fake_run(args: list[str], **kwargs: object) -> CommandResult:
        captured["args"] = list(args)
        return _fake_result(args)

    with patch("automation_v2.test_runner.run_command", side_effect=fake_run):
        result = run_focused_tests(
            ["python -m pytest -q tests"],
            run_dir=tmp_path,
            config=CONFIG,
        )

    assert result is not None
    assert result.passed is True
    args = captured["args"]
    assert args[:4] == [sys.executable, "-m", "pytest", "-q"]
    assert args[4:] == ["tests"]
    assert "python -m pytest -q tests" not in args


def test_run_focused_tests_skips_when_no_targets(tmp_path: Path) -> None:
    """Options-only planner output skips focused tests successfully."""
    with patch("automation_v2.test_runner.run_command") as mocked:
        result = run_focused_tests(
            ["python -m pytest -q"],
            run_dir=tmp_path,
            config=CONFIG,
        )
    assert result is None
    mocked.assert_not_called()


def test_run_tests_full_suite_remains_mandatory(tmp_path: Path) -> None:
    """Full suite always runs even when focused tests are skipped or pass."""
    calls: list[list[str]] = []

    def fake_run(args: list[str], **kwargs: object) -> CommandResult:
        calls.append(list(args))
        return _fake_result(args)

    with patch("automation_v2.test_runner.run_command", side_effect=fake_run):
        result = run_tests(
            run_dir=tmp_path,
            config=CONFIG,
            focused_tests=["python -m pytest -q tests"],
        )

    assert result.passed is True
    assert result.focused_passed is True
    assert len(calls) == 2
    assert calls[0] == [sys.executable, "-m", "pytest", "-q", "tests"]
    assert calls[1] == [sys.executable, "-m", "pytest", "-q"]


def test_run_tests_skips_focused_but_still_runs_full_suite(
    tmp_path: Path,
) -> None:
    """When focused entries normalize away, only the full suite runs."""
    calls: list[list[str]] = []

    def fake_run(args: list[str], **kwargs: object) -> CommandResult:
        calls.append(list(args))
        return _fake_result(args)

    with patch("automation_v2.test_runner.run_command", side_effect=fake_run):
        result = run_tests(
            run_dir=tmp_path,
            config=CONFIG,
            focused_tests=["python -m pytest -q"],
        )

    assert result.passed is True
    assert result.focused_passed is None
    assert calls == [[sys.executable, "-m", "pytest", "-q"]]


def test_run_tests_fails_when_focused_fails_even_if_full_passes(
    tmp_path: Path,
) -> None:
    """Focused failure marks overall result failed."""
    def fake_run(args: list[str], **kwargs: object) -> CommandResult:
        if len(args) > 4:
            return _fake_result(args, returncode=1)
        return _fake_result(args, returncode=0)

    with patch("automation_v2.test_runner.run_command", side_effect=fake_run):
        result = run_tests(
            run_dir=tmp_path,
            config=CONFIG,
            focused_tests=["tests/test_play_layout_ui.py"],
        )

    assert isinstance(result, TestResult)
    assert result.passed is False
    assert result.focused_passed is False
