"""Tests for automation_v2.process_runner."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from automation_v2.process_runner import run_command


ROOT = Path(__file__).resolve().parents[2]


def test_utf8_output_is_captured() -> None:
    """Valid UTF-8 stdout is returned as text."""
    result = run_command(
        [
            sys.executable,
            "-c",
            "import sys; sys.stdout.write('café — 修仙')",
        ],
        cwd=ROOT,
        timeout=30,
    )
    assert result.returncode == 0
    assert result.timed_out is False
    assert "café" in result.stdout
    assert "修仙" in result.stdout
    assert result.stderr == ""


def test_invalid_byte_sequences_are_replaced() -> None:
    """Invalid bytes in subprocess output must not crash the framework."""
    result = run_command(
        [
            sys.executable,
            "-c",
            "import sys; sys.stdout.buffer.write(b'ok\\xff\\xfe end')",
        ],
        cwd=ROOT,
        timeout=30,
    )
    assert result.returncode == 0
    assert "ok" in result.stdout
    assert "end" in result.stdout
    assert "\ufffd" in result.stdout or "\xff" not in result.stdout.encode(
        "utf-8",
        errors="surrogatepass",
    )


def test_stdout_none_becomes_empty_string() -> None:
    """None stdout/stderr from CompletedProcess become empty strings."""
    fake = MagicMock()
    fake.returncode = 0
    fake.stdout = None
    fake.stderr = None

    with patch("automation_v2.process_runner.subprocess.run", return_value=fake):
        result = run_command(["git", "--version"], cwd=ROOT, timeout=10)

    assert result.stdout == ""
    assert result.stderr == ""
    assert result.returncode == 0
    assert result.timed_out is False


def test_timeout_sets_timed_out_flag() -> None:
    """Command timeouts return timed_out=True without raising."""
    result = run_command(
        [sys.executable, "-c", "import time; time.sleep(5)"],
        cwd=ROOT,
        timeout=0.3,
    )
    assert result.timed_out is True
    assert result.returncode == -1
    assert result.duration_seconds >= 0.2


def test_timeout_expired_none_output_coerced() -> None:
    """TimeoutExpired with None stdout/stderr is coerced safely."""
    with patch(
        "automation_v2.process_runner.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=["x"], timeout=1),
    ):
        result = run_command(["x"], cwd=ROOT, timeout=1)

    assert result.timed_out is True
    assert result.stdout == ""
    assert result.stderr == ""
