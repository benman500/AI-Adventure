"""Tests for automation_v2.guardrails."""

from __future__ import annotations

from pathlib import Path

from automation_v2.config import load_config
from automation_v2.guardrails import validate_changed_files


ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_config(ROOT)

ALLOWED = [
    "src/ai_adventure/presentation/templates",
    "src/ai_adventure/presentation/static",
    "tests",
]


def test_allowed_paths_pass() -> None:
    """Files inside allowed areas are accepted."""
    result = validate_changed_files(
        [
            "src/ai_adventure/presentation/templates/play.html",
            "src/ai_adventure/presentation/static/css/main.css",
            "tests/test_play_layout_ui.py",
            "automation_v2/AGENT_REPORT.md",
        ],
        ALLOWED,
        CONFIG,
    )
    assert result.ok is True
    assert result.decision == "approve"
    assert result.violations == []


def test_outside_allowed_areas_rejected() -> None:
    """Files outside allowed areas require human review."""
    result = validate_changed_files(
        ["src/ai_adventure/engine/combat.py"],
        ALLOWED,
        CONFIG,
    )
    assert result.ok is False
    assert result.decision == "human_review"
    assert any("outside allowed areas" in item for item in result.violations)


def test_forbidden_env_file() -> None:
    """Changing .env files is forbidden."""
    result = validate_changed_files([".env", ".env.local"], ALLOWED, CONFIG)
    assert result.ok is False
    assert result.decision == "human_review"
    assert any(".env" in item for item in result.violations)


def test_forbidden_migration_path() -> None:
    """Migration paths require human review."""
    result = validate_changed_files(
        ["alembic/versions/0001_initial.py"],
        ALLOWED + ["alembic/versions"],
        CONFIG,
    )
    assert result.ok is False
    assert any("Migration" in item for item in result.violations)


def test_forbidden_workflow_and_lock_files() -> None:
    """Workflows, lockfiles, and deployment files are rejected."""
    result = validate_changed_files(
        [
            ".github/workflows/ci.yml",
            "uv.lock",
            "Dockerfile",
            "pyproject.toml",
        ],
        ALLOWED
        + [
            ".github/workflows",
            ".",
        ],
        CONFIG,
    )
    assert result.ok is False
    assert result.decision == "human_review"
    assert len(result.violations) >= 3


def test_changed_file_limit() -> None:
    """Exceeding max_changed_files requires human review."""
    files = [
        f"tests/file_{index}.py" for index in range(CONFIG.max_changed_files + 3)
    ]
    result = validate_changed_files(files, ALLOWED, CONFIG)
    assert result.ok is False
    assert any("maximum is" in item for item in result.violations)


def test_violations_do_not_discard_changes() -> None:
    """Guardrails return human_review and still list the changed files."""
    files = [".env", "src/ai_adventure/presentation/templates/play.html"]
    result = validate_changed_files(files, ALLOWED, CONFIG)
    assert result.decision == "human_review"
    assert ".env" in result.changed_files
    assert (
        "src/ai_adventure/presentation/templates/play.html"
        in result.changed_files
    )
