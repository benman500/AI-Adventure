"""Invoke the Cursor agent CLI in headless print mode."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from automation_v2.config import AutomationConfig
from automation_v2.process_runner import run_command


class CursorNotFoundError(RuntimeError):
    """Raised when no configured Cursor agent executable is on PATH."""


@dataclass(frozen=True)
class CursorRunResult:
    """Captured outcome of a Cursor CLI invocation."""

    executable: str
    returncode: int
    timed_out: bool
    prompt_file: Path
    log_file: Path
    stdout: str
    stderr: str


def resolve_cursor_executable(config: AutomationConfig) -> str:
    """Return the first configured Cursor executable found on PATH."""
    for candidate in config.cursor_executable_candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise CursorNotFoundError(
        "Cursor CLI was not found. Install it and confirm that one of "
        f"{list(config.cursor_executable_candidates)} works on PATH."
    )


def build_cursor_command(
    executable: str,
    prompt_text: str,
    config: AutomationConfig,
) -> list[str]:
    """Build the argv list for headless print mode.

    Argument prefixes come from ``config.cursor_print_args`` so CLI syntax
    changes can be adjusted in ``config.py`` / environment variables.
    """
    return [executable, *config.cursor_print_args, prompt_text]


def invoke_cursor(
    *,
    prompt: str,
    run_dir: Path,
    attempt: int,
    config: AutomationConfig,
) -> CursorRunResult:
    """Write the prompt file, run Cursor, and capture a log.

    Never uses ``shell=True`` and does not route through PowerShell.
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    prompt_file = run_dir / f"cursor_prompt_{attempt}.md"
    log_file = run_dir / f"cursor_output_{attempt}.txt"
    prompt_file.write_text(prompt, encoding="utf-8")

    executable = resolve_cursor_executable(config)
    command = build_cursor_command(executable, prompt, config)

    result = run_command(
        command,
        cwd=config.repository_root,
        timeout=float(config.cursor_timeout_seconds),
    )

    log_file.write_text(
        "COMMAND\n"
        "=======\n"
        + " ".join(command[: len(command) - 1] + ["<prompt>"])
        + "\n\nSTDOUT\n"
        "======\n"
        + result.stdout
        + "\n\nSTDERR\n"
        "======\n"
        + result.stderr
        + (
            "\n\nTIMED OUT\n"
            if result.timed_out
            else ""
        ),
        encoding="utf-8",
    )

    return CursorRunResult(
        executable=executable,
        returncode=result.returncode,
        timed_out=result.timed_out,
        prompt_file=prompt_file,
        log_file=log_file,
        stdout=result.stdout,
        stderr=result.stderr,
    )
