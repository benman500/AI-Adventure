"""Central configuration for automation_v2.

Configurable values are read from environment variables.
This module never contains secrets.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _default_repo_root() -> Path:
    """Resolve the repository root from this package location."""
    return Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class AutomationConfig:
    """Validated runtime configuration for the automation framework."""

    repository_root: Path
    automation_dir: Path
    runs_dir: Path
    tasks_file: Path
    state_file: Path
    max_runtime_hours: float
    max_repair_attempts: int
    max_changed_files: int
    cursor_timeout_seconds: int
    pytest_timeout_seconds: int
    openai_model: str
    openai_model_env_var: str
    cursor_executable_candidates: tuple[str, ...]
    cursor_print_args: tuple[str, ...]
    forbidden_path_prefixes: tuple[str, ...]
    forbidden_exact_names: tuple[str, ...]
    always_allowed_files: tuple[str, ...]
    project_context_files: tuple[str, ...]

    def validate(self) -> None:
        """Raise ValueError when configuration values are invalid."""
        errors: list[str] = []

        if not self.repository_root.is_dir():
            errors.append(
                f"repository_root is not a directory: {self.repository_root}"
            )
        if self.max_runtime_hours <= 0:
            errors.append("max_runtime_hours must be > 0")
        if self.max_repair_attempts < 0:
            errors.append("max_repair_attempts must be >= 0")
        if self.max_changed_files < 1:
            errors.append("max_changed_files must be >= 1")
        if self.cursor_timeout_seconds < 1:
            errors.append("cursor_timeout_seconds must be >= 1")
        if self.pytest_timeout_seconds < 1:
            errors.append("pytest_timeout_seconds must be >= 1")
        if not self.openai_model.strip():
            errors.append("openai_model must be a non-empty string")
        if not self.cursor_executable_candidates:
            errors.append("cursor_executable_candidates must not be empty")
        if not self.cursor_print_args:
            errors.append("cursor_print_args must not be empty")

        if errors:
            raise ValueError(
                "Invalid automation_v2 configuration:\n- "
                + "\n- ".join(errors)
            )


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def load_config(repository_root: Path | None = None) -> AutomationConfig:
    """Load configuration from environment variables and validate it."""
    root = (repository_root or _default_repo_root()).resolve()
    automation_dir = root / "automation_v2"
    model_env_var = "OPENAI_AUTOMATION_MODEL"

    config = AutomationConfig(
        repository_root=root,
        automation_dir=automation_dir,
        runs_dir=automation_dir / "runs",
        tasks_file=automation_dir / "tasks.json",
        state_file=automation_dir / "state.json",
        max_runtime_hours=_env_float("AUTOMATION_MAX_HOURS", 4.0),
        max_repair_attempts=_env_int("AUTOMATION_MAX_REPAIRS", 2),
        max_changed_files=_env_int("AUTOMATION_MAX_CHANGED_FILES", 25),
        cursor_timeout_seconds=_env_int(
            "AUTOMATION_CURSOR_TIMEOUT_SECONDS",
            60 * 90,
        ),
        pytest_timeout_seconds=_env_int(
            "AUTOMATION_PYTEST_TIMEOUT_SECONDS",
            60 * 45,
        ),
        openai_model=os.getenv(model_env_var, "gpt-5.6"),
        openai_model_env_var=model_env_var,
        # Easy to change: first matching executable on PATH is used.
        cursor_executable_candidates=tuple(
            item.strip()
            for item in os.getenv(
                "AUTOMATION_CURSOR_COMMANDS",
                "agent,cursor-agent",
            ).split(",")
            if item.strip()
        ),
        # Headless print-mode arguments before the prompt text.
        # Adjust here (or via AUTOMATION_CURSOR_PRINT_ARGS) if CLI syntax changes.
        cursor_print_args=tuple(
            item
            for item in os.getenv(
                "AUTOMATION_CURSOR_PRINT_ARGS",
                "-p,--output-format,text",
            ).split(",")
            if item != ""
        ),
        forbidden_path_prefixes=(
            ".env",
            "alembic/versions/",
            ".github/workflows/",
            "deploy/",
            "deployment/",
            "infra/",
            "infrastructure/",
        ),
        forbidden_exact_names=(
            "pyproject.toml",
            "uv.lock",
            "poetry.lock",
            "Pipfile.lock",
            "requirements.txt",
            "package-lock.json",
            "yarn.lock",
            "pnpm-lock.yaml",
            "Dockerfile",
            "docker-compose.yml",
            "docker-compose.yaml",
            "Procfile",
            "fly.toml",
            "railway.toml",
            "render.yaml",
        ),
        always_allowed_files=(
            "automation/AGENT_REPORT.md",
            "automation_v2/AGENT_REPORT.md",
        ),
        project_context_files=(
            "AGENTS.md",
            "PROJECT_CONTEXT.md",
            "CURRENT_MILESTONE.md",
        ),
    )
    config.validate()
    return config
