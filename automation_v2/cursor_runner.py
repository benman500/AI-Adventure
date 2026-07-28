"""Invoke the Cursor agent CLI in headless print mode."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from automation_v2.config import AutomationConfig
from automation_v2.process_runner import run_command

_VERSION_DIR_RE = re.compile(
    r"^\d{4}\.\d{1,2}\.\d{1,2}(-\d{2}-\d{2}-\d{2})?-[a-f0-9]+$"
)


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


def _version_sort_key(name: str) -> tuple[int, str]:
    """Sort Cursor version directory names newest-first."""
    date_part = name.split("-")[0]
    parts = date_part.split(".")
    if len(parts) != 3:
        return (0, name)
    try:
        year, month, day = (int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        return (0, name)
    return (year * 10_000 + month * 100 + day, name)


def unwrap_windows_cmd_wrapper(cmd_path: Path) -> list[str] | None:
    """Resolve ``agent.CMD`` to ``[node.exe, index.js]`` when possible.

    Windows ``agent.CMD`` forwards ``%*`` into PowerShell, which corrupts
    multiline prompt arguments. Invoking Node directly preserves argv.
    """
    script_dir = cmd_path.resolve().parent
    local_node = script_dir / "node.exe"
    local_index = script_dir / "index.js"
    if local_node.is_file() and local_index.is_file():
        return [str(local_node), str(local_index)]

    versions_root = script_dir / "versions"
    if not versions_root.is_dir():
        return None

    version_dirs = [
        path
        for path in versions_root.iterdir()
        if path.is_dir() and _VERSION_DIR_RE.match(path.name)
    ]
    if not version_dirs:
        return None

    version_dirs.sort(key=lambda path: _version_sort_key(path.name), reverse=True)
    latest = version_dirs[0]
    node = latest / "node.exe"
    index = latest / "index.js"
    if node.is_file() and index.is_file():
        return [str(node), str(index)]
    return None


def resolve_cursor_argv_prefix(config: AutomationConfig) -> list[str]:
    """Return the argv prefix used to launch Cursor without shell wrappers."""
    resolved = resolve_cursor_executable(config)
    path = Path(resolved)
    if path.suffix.lower() in {".cmd", ".bat"}:
        unwrapped = unwrap_windows_cmd_wrapper(path)
        if unwrapped is not None:
            return unwrapped
    return [resolved]


def build_cursor_command(
    executable: str | list[str],
    prompt_text: str,
    config: AutomationConfig,
) -> list[str]:
    """Build the argv list for headless print mode.

    ``-p`` / ``--print`` is a boolean flag. The complete prompt string is the
    next argv element (one list item, including spaces and newlines). Remaining
    items from ``config.cursor_print_args`` follow.

    Intended shape::

        [executable..., "-p", prompt_text, "--output-format", "text"]
    """
    if isinstance(executable, str):
        command: list[str] = [executable]
    else:
        command = list(executable)

    if not prompt_text:
        raise ValueError("prompt_text must be a non-empty string")
    if prompt_text in {"<prompt>", "{prompt}", "prompt_file"}:
        raise ValueError(
            "prompt_text must be the actual prompt contents, "
            f"not the placeholder {prompt_text!r}"
        )

    print_args = list(config.cursor_print_args)
    prompt_inserted = False

    for arg in print_args:
        command.append(arg)
        if arg in {"-p", "--print"} and not prompt_inserted:
            command.append(prompt_text)
            prompt_inserted = True

    if not prompt_inserted:
        command.append(prompt_text)

    if "<prompt>" in command:
        raise RuntimeError(
            "Refusing to launch Cursor with literal '<prompt>' in argv"
        )
    return command


def _command_for_log(command: list[str], prompt_text: str) -> str:
    """Render argv for logs with the prompt redacted (display only)."""
    redacted: list[str] = []
    for arg in command:
        if arg == prompt_text:
            redacted.append("<prompt>")
        else:
            redacted.append(arg)
    return " ".join(redacted)


def invoke_cursor(
    *,
    prompt: str,
    run_dir: Path,
    attempt: int,
    config: AutomationConfig,
) -> CursorRunResult:
    """Write the prompt file, run Cursor, and capture a log.

    Never uses ``shell=True`` and does not route through PowerShell.
    The prompt file is written for debugging, then its UTF-8 contents are
    read back and passed as a single argv element immediately after ``-p``.
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    prompt_file = run_dir / f"cursor_prompt_{attempt}.md"
    log_file = run_dir / f"cursor_output_{attempt}.txt"
    prompt_file.write_text(prompt, encoding="utf-8")
    prompt_text = prompt_file.read_text(encoding="utf-8")
    if not prompt_text.strip():
        raise ValueError(f"Prompt file is empty: {prompt_file}")

    resolved_executable = resolve_cursor_executable(config)
    argv_prefix = resolve_cursor_argv_prefix(config)
    command = build_cursor_command(argv_prefix, prompt_text, config)

    # Real subprocess argv must contain the prompt, never the log placeholder.
    dash_p_index = command.index("-p")
    if command[dash_p_index + 1] != prompt_text:
        raise RuntimeError("Cursor argv does not place prompt text immediately after -p")
    if "<prompt>" in command:
        raise RuntimeError("Cursor argv still contains literal '<prompt>' placeholder")

    result = run_command(
        command,
        cwd=config.repository_root,
        timeout=float(config.cursor_timeout_seconds),
    )

    log_file.write_text(
        "COMMAND (displayed; prompt redacted)\n"
        "====================================\n"
        + _command_for_log(command, prompt_text)
        + "\n\nARGV NOTES\n"
        "==========\n"
        f"executable_resolved={resolved_executable}\n"
        f"argv_prefix={argv_prefix!r}\n"
        f"prompt_chars={len(prompt_text)}\n"
        f"prompt_follows_-p={command[command.index('-p') + 1] == prompt_text}\n"
        "\n\nSTDOUT\n"
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
        executable=resolved_executable,
        returncode=result.returncode,
        timed_out=result.timed_out,
        prompt_file=prompt_file,
        log_file=log_file,
        stdout=result.stdout,
        stderr=result.stderr,
    )
