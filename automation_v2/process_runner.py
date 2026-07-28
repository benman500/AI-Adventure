"""Subprocess execution for automation_v2.

This is the only module that may import and use subprocess.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from automation_v2.models import CommandResult


def run_command(
    args: list[str],
    *,
    cwd: Path,
    timeout: float | None = None,
    env: dict[str, str] | None = None,
) -> CommandResult:
    """Run a command with UTF-8 output handling and optional timeout.

    Always uses ``shell=False``, captures output, and never lets a decoding
    error crash the caller. ``stdout``/``stderr`` of ``None`` become ``""``.
    """
    if not args:
        raise ValueError("run_command requires a non-empty argument list")

    environment = os.environ.copy()
    if env:
        environment.update(env)
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"

    started = time.monotonic()
    timed_out = False
    returncode = -1
    stdout = ""
    stderr = ""

    try:
        completed = subprocess.run(
            args,
            cwd=str(cwd),
            shell=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=environment,
            check=False,
        )
        returncode = int(completed.returncode)
        stdout = completed.stdout if completed.stdout is not None else ""
        stderr = completed.stderr if completed.stderr is not None else ""
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        returncode = -1
        raw_stdout = exc.stdout
        raw_stderr = exc.stderr
        stdout = _coerce_output(raw_stdout)
        stderr = _coerce_output(raw_stderr)
    except UnicodeError:
        # Extremely defensive: text mode with errors="replace" should avoid
        # this, but never let decoding crash the framework.
        timed_out = False
        returncode = -1
        stdout = ""
        stderr = "Output decoding failed; replaced with empty strings."

    duration = time.monotonic() - started
    return CommandResult(
        command=list(args),
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        duration_seconds=duration,
        timed_out=timed_out,
    )


def _coerce_output(value: str | bytes | None) -> str:
    """Normalize subprocess output fragments to a UTF-8 string."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value
