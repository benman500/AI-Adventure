"""Tests for automation_v2.guardrails."""

from __future__ import annotations

from pathlib import Path

from automation_v2.config import load_config
from automation_v2.guardrails import (
    filter_diff_for_review,
    filter_implementation_files,
    is_runtime_artifact,
    validate_changed_files,
)


ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_config(ROOT)

ALLOWED = [
    "src/ai_adventure/presentation/templates",
    "src/ai_adventure/presentation/static",
    "tests",
]

RUNTIME_ARTIFACTS = [
    "automation_v2/runs/20260728-example/cursor_prompt_0.md",
    "automation_v2/state.json",
    "automation/AGENT_REPORT.md",
    "automation_v2/AGENT_REPORT.md",
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
    assert "automation_v2/AGENT_REPORT.md" not in result.changed_files
    assert "automation_v2/AGENT_REPORT.md" in result.runtime_artifacts


def test_runtime_artifacts_ignored_for_scope() -> None:
    """Orchestrator runtime artifacts never count as implementation changes."""
    result = validate_changed_files(RUNTIME_ARTIFACTS, ALLOWED, CONFIG)
    assert result.ok is True
    assert result.decision == "approve"
    assert result.violations == []
    assert result.changed_files == []
    assert set(result.runtime_artifacts) == {
        "automation_v2/runs/20260728-example/cursor_prompt_0.md",
        "automation_v2/state.json",
        "automation/AGENT_REPORT.md",
        "automation_v2/AGENT_REPORT.md",
    }


def test_runtime_artifacts_with_real_files_still_checks_project_files() -> None:
    """Real project files are still validated when runtime artifacts are present."""
    result = validate_changed_files(
        [
            *RUNTIME_ARTIFACTS,
            "src/ai_adventure/presentation/templates/new_game.html",
            "src/ai_adventure/presentation/static/css/main.css",
            "tests/test_character_creation_ui.py",
        ],
        ALLOWED,
        CONFIG,
    )
    assert result.ok is True
    assert result.decision == "approve"
    assert result.changed_files == [
        "src/ai_adventure/presentation/templates/new_game.html",
        "src/ai_adventure/presentation/static/css/main.css",
        "tests/test_character_creation_ui.py",
    ]
    assert "automation/AGENT_REPORT.md" not in result.changed_files
    assert "automation_v2/state.json" not in result.changed_files


def test_genuine_out_of_scope_still_triggers_human_review() -> None:
    """Out-of-scope project files still force human review despite artifacts."""
    result = validate_changed_files(
        [
            *RUNTIME_ARTIFACTS,
            "src/ai_adventure/engine/combat.py",
        ],
        ALLOWED,
        CONFIG,
    )
    assert result.ok is False
    assert result.decision == "human_review"
    assert any("outside allowed areas" in item for item in result.violations)
    assert "src/ai_adventure/engine/combat.py" in result.changed_files
    assert "automation_v2/state.json" not in result.changed_files


def test_filter_implementation_files_and_diff() -> None:
    """Diff helpers keep diagnostics but expose only implementation files."""
    files = [
        *RUNTIME_ARTIFACTS,
        "src/ai_adventure/presentation/static/css/main.css",
    ]
    assert all(is_runtime_artifact(path) for path in RUNTIME_ARTIFACTS)
    assert filter_implementation_files(files) == [
        "src/ai_adventure/presentation/static/css/main.css"
    ]

    filtered = filter_diff_for_review(
        {
            "stat": "raw stat",
            "diff": "raw diff",
            "changed_files": files,
        }
    )
    assert filtered["changed_files"] == [
        "src/ai_adventure/presentation/static/css/main.css"
    ]
    assert filtered["runtime_artifacts_excluded"] is True
    assert "Runtime artifacts excluded" in str(filtered["stat"])


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
