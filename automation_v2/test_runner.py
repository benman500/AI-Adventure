"""Pytest execution for automation_v2."""

from __future__ import annotations

import shlex
import sys
from pathlib import Path

from automation_v2.config import AutomationConfig
from automation_v2.models import TestResult
from automation_v2.process_runner import run_command

_FORBIDDEN_PROGRAMS = frozenset(
    {
        "powershell",
        "powershell.exe",
        "pwsh",
        "pwsh.exe",
        "cmd",
        "cmd.exe",
        "bash",
        "bash.exe",
        "sh",
        "sh.exe",
        "zsh",
        "zsh.exe",
        "fish",
        "fish.exe",
        "wsl",
        "wsl.exe",
    }
)

_PYTHON_NAMES = frozenset(
    {
        "python",
        "python.exe",
        "python3",
        "python3.exe",
        "py",
        "py.exe",
    }
)

_QUIET_FLAGS = frozenset({"-q", "--quiet"})

_SAFE_OPTION_FLAGS = frozenset(
    {
        "-k",
        "-m",
        "-x",
        "-v",
        "-vv",
        "-vvv",
        "-s",
        "-q",
        "--quiet",
        "--lf",
        "--ff",
        "--nf",
        "--basetemp",
    }
)

_OPTIONS_WITH_VALUE = frozenset({"-k", "-m", "--basetemp"})


def _contains_unsafe_shell_syntax(entry: str) -> bool:
    """Return True when an entry includes shell metacharacters we refuse."""
    # Pytest node ids use ``::``; bare ``:`` is fine. Reject redirection/pipes.
    if any(char in entry for char in ("|", "&", ";", ">", "<", "`", "\n", "\r")):
        return True
    return False


def _program_name(token: str) -> str:
    return Path(token).name.lower()


def _unwrap_quotes(token: str) -> str:
    """Remove one layer of surrounding quotes kept by Windows shlex."""
    if len(token) >= 2 and token[0] == token[-1] and token[0] in {'"', "'"}:
        return token[1:-1]
    return token


def _looks_like_pytest_command(entry: str) -> bool:
    lower = entry.lower().strip()
    if lower.startswith("pytest"):
        return True
    if lower.startswith("python") or lower.startswith("py "):
        return True
    if " -m pytest" in f" {lower}" or lower.startswith("-m pytest"):
        return True
    return False


def _is_safe_option_token(token: str) -> bool:
    if token in _SAFE_OPTION_FLAGS:
        return True
    if token.startswith("--tb"):
        return True
    if "=" in token and token.startswith("-"):
        return _is_safe_option_token(token.split("=", 1)[0])
    return False


def _validate_pytest_spec_tokens(tokens: list[str], *, entry: str) -> None:
    """Reject forbidden programs and unsupported options in a pytest spec."""
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token.startswith("-"):
            if not _is_safe_option_token(token):
                raise ValueError(
                    f"Unsupported pytest option in focused test entry: {entry!r}"
                )
            if token in _OPTIONS_WITH_VALUE and "=" not in token:
                index += 1
                if index >= len(tokens):
                    raise ValueError(
                        f"Option {token!r} requires a value in focused test "
                        f"entry: {entry!r}"
                    )
            index += 1
            continue

        if _program_name(token) in _FORBIDDEN_PROGRAMS:
            raise ValueError(
                f"Forbidden program in focused test entry: {entry!r}"
            )
        index += 1


def _split_pytest_spec(raw: str) -> list[str]:
    """Split a path/options pytest specification with shlex."""
    tokens = [
        _unwrap_quotes(token)
        for token in shlex.split(raw, posix=False)
        if token
    ]
    return [token for token in tokens if token not in _QUIET_FLAGS]


def normalize_focused_test_entry(entry: str) -> list[str]:
    """Normalize one planner focused-test entry into pytest argv fragments.

    Preferred input is a bare target, node id, or path plus safe options such
    as ``tests -k "expression"``. Full ``python -m pytest ...`` command
    strings are accepted only after stripping the executable prefix.

    Raises:
        ValueError: When the entry is unsafe, prose, or not a pytest invocation.
    """
    from automation_v2.planner import is_valid_focused_test_target

    raw = entry.strip()
    if not raw:
        return []

    if _contains_unsafe_shell_syntax(raw):
        raise ValueError(
            f"Unsafe shell syntax in focused test entry: {entry!r}"
        )

    lower = raw.lower()
    if lower.startswith(
        (
            "run ",
            "running ",
            "please ",
            "execute ",
            "invoke ",
        )
    ):
        raise ValueError(
            "Focused test entry looks like prose, not a pytest target: "
            f"{entry!r}"
        )

    if not _looks_like_pytest_command(raw):
        first_token = _unwrap_quotes(shlex.split(raw, posix=False)[0])
        if _program_name(first_token) in _FORBIDDEN_PROGRAMS:
            raise ValueError(
                f"Forbidden program in focused test entry: {entry!r}"
            )
        # Single path / node id: keep as one argv element.
        if " " not in raw and "\t" not in raw:
            if not is_valid_focused_test_target(raw):
                raise ValueError(
                    "Focused test entry must be a test file, test directory, "
                    f"or pytest node id; got: {entry!r}"
                )
            return [raw.replace("\\", "/")]
        # Path plus options (for example: tests -k "a or b").
        tokens = _split_pytest_spec(raw)
        if not tokens:
            return []
        if not is_valid_focused_test_target(tokens[0]):
            raise ValueError(
                "Focused test entry must start with a pytest target; "
                f"got: {entry!r}"
            )
        _validate_pytest_spec_tokens(tokens, entry=entry)
        return tokens

    tokens = [
        _unwrap_quotes(token)
        for token in shlex.split(raw, posix=False)
        if token
    ]
    if not tokens:
        return []

    first = _program_name(tokens[0])
    if first in _FORBIDDEN_PROGRAMS:
        raise ValueError(
            f"Forbidden program in focused test entry: {entry!r}"
        )

    index = 0
    executable_name = Path(sys.executable).name.lower()

    if first in _PYTHON_NAMES or first == executable_name:
        index = 1
        if index >= len(tokens) or tokens[index] != "-m":
            raise ValueError(
                "Focused test commands must use 'python -m pytest', "
                f"got: {entry!r}"
            )
        index += 1
        if index >= len(tokens) or tokens[index].lower() != "pytest":
            raise ValueError(
                "Focused test commands must use 'python -m pytest', "
                f"got: {entry!r}"
            )
        index += 1
    elif first in {"pytest", "pytest.exe"}:
        index = 1
    else:
        raise ValueError(
            "Focused test commands may only invoke pytest "
            f"(via python -m pytest); got: {entry!r}"
        )

    remaining = [
        token
        for token in tokens[index:]
        if token not in _QUIET_FLAGS
    ]
    if remaining:
        _validate_pytest_spec_tokens(remaining, entry=entry)
    return remaining


def normalize_focused_tests(entries: list[str]) -> list[str]:
    """Normalize planner focused-test entries into pytest targets/options.

    Entries that normalize to options only (no path/node targets) are ignored
    for the purpose of deciding whether a focused run is needed.
    """
    normalized: list[str] = []
    seen: set[str] = set()

    for entry in entries:
        for token in normalize_focused_test_entry(entry):
            if token in seen:
                continue
            seen.add(token)
            normalized.append(token)

    return normalized


def focused_targets_for_run(entries: list[str]) -> list[str]:
    """Return argv fragments for a focused run, or ``[]`` to skip.

    Skips when no non-option targets remain after normalization.
    """
    normalized = normalize_focused_tests(entries)
    if not any(not token.startswith("-") for token in normalized):
        return []
    return normalized


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
    """Run optional focused pytest targets.

    Returns ``None`` when no focused tests were supplied or none remain after
    safe normalization (skip successfully and continue to the full suite).
    """
    if not focused_tests:
        return None

    run_dir.mkdir(parents=True, exist_ok=True)
    log_file = run_dir / "pytest_focused.txt"

    try:
        targets = focused_targets_for_run(focused_tests)
    except ValueError as exc:
        message = str(exc)
        _write_log(log_file, "", message)
        return TestResult(
            passed=False,
            returncode=4,
            stdout="",
            stderr=message,
            log_file=str(log_file),
            focused_passed=False,
            timed_out=False,
        )

    if not targets:
        _write_log(
            log_file,
            "",
            "No valid focused test targets after normalization; "
            "skipping focused stage.",
        )
        return None

    args = [sys.executable, "-m", "pytest", "-q", *targets]
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

    Overall ``passed`` is true only when focused work succeeds or is skipped
    and the mandatory full suite passes.
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
