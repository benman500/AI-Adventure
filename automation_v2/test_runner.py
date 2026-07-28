"""Pytest execution for automation_v2."""

from __future__ import annotations

import sys
from pathlib import Path

from automation_v2.config import AutomationConfig
from automation_v2.models import TestResult
from automation_v2.process_runner import run_command


def _write_log(path: Path, stdout: str, stderr: str) -> None:
    path.write_text(
        "STDOUT\n======\n"
        + stdout
        + "\n\nSTDERR\n======\n"
        + stderr,
        encoding="utf-8",
    )


def run_focused_tests(
    focused_tests: list[str],
    *,
    run_dir: Path,
    config: AutomationConfig,
) -> TestResult | None:
    """Run optional focused pytest targets. Return None when none supplied."""
    if not focused_tests:
        return None

    run_dir.mkdir(parents=True, exist_ok=True)
    log_file = run_dir / "pytest_focused.txt"

    # Focused entries may be paths or extra pytest args; always invoke via
    # python -m pytest for consistency.
    args = [sys.executable, "-m", "pytest", "-q", *focused_tests]
    result = run_command(
        args,
        cwd=config.repository_root,
        timeout=float(config.pytest_timeout_seconds),
    )
    _write_log(log_file, result.stdout, result.stderr)

    passed = result.returncode == 0 and not result.timed_out
    return TestResult(
        passed=passed,
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        log_file=str(log_file),
        focused_passed=passed,
        timed_out=result.timed_out,
    )


def run_full_suite(
    *,
    run_dir: Path,
    config: AutomationConfig,
) -> TestResult:
    """Always run ``python -m pytest -q`` before approval.

    A failed test returns a structured result and does not raise.
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    log_file = run_dir / "pytest.txt"
    args = [sys.executable, "-m", "pytest", "-q"]
    result = run_command(
        args,
        cwd=config.repository_root,
        timeout=float(config.pytest_timeout_seconds),
    )
    _write_log(log_file, result.stdout, result.stderr)

    passed = result.returncode == 0 and not result.timed_out
    return TestResult(
        passed=passed,
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        log_file=str(log_file),
        focused_passed=None,
        timed_out=result.timed_out,
    )


def run_tests(
    *,
    run_dir: Path,
    config: AutomationConfig,
    focused_tests: list[str] | None = None,
) -> TestResult:
    """Run focused tests when supplied, then always run the full suite.

    The returned ``TestResult`` reflects the full-suite outcome required for
    approval. Focused failures are recorded in a separate log and cause the
    overall result to be marked failed without crashing the framework.
    """
    focused = run_focused_tests(
        focused_tests or [],
        run_dir=run_dir,
        config=config,
    )
    full = run_full_suite(run_dir=run_dir, config=config)

    if focused is not None and not focused.passed:
        return TestResult(
            passed=False,
            returncode=focused.returncode if not full.passed else focused.returncode,
            stdout=full.stdout,
            stderr=(
                "Focused tests failed.\n"
                + focused.stderr
                + "\n\n--- full suite ---\n"
                + full.stderr
            ),
            log_file=full.log_file,
            focused_passed=False,
            timed_out=focused.timed_out or full.timed_out,
        )

    return TestResult(
        passed=full.passed,
        returncode=full.returncode,
        stdout=full.stdout,
        stderr=full.stderr,
        log_file=full.log_file,
        focused_passed=None if focused is None else focused.passed,
        timed_out=full.timed_out,
    )
