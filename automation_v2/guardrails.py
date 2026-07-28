"""Scope and safety guardrails for changed files."""

from __future__ import annotations

from pathlib import PurePosixPath

from automation_v2.config import AutomationConfig
from automation_v2.models import GuardrailResult


def _normalize(path: str) -> str:
    """Normalize path separators without stripping significant leading dots."""
    normalized = path.replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _is_env_file(path: str) -> bool:
    name = PurePosixPath(path).name
    return name == ".env" or name.startswith(".env.")


def _is_migration_path(path: str) -> bool:
    normalized = _normalize(path)
    return (
        normalized.startswith("alembic/versions/")
        or "/alembic/versions/" in normalized
        or normalized.startswith("migrations/")
        or "/migrations/" in f"/{normalized}"
    )


def _is_workflow_or_deployment(path: str, config: AutomationConfig) -> bool:
    normalized = _normalize(path)
    for prefix in config.forbidden_path_prefixes:
        cleaned = prefix.replace("\\", "/").rstrip("/")
        if cleaned == ".env":
            continue
        if cleaned.endswith("/"):
            cleaned = cleaned.rstrip("/")
        if normalized == cleaned or normalized.startswith(cleaned + "/"):
            return True
        if cleaned in {"alembic/versions"} and _is_migration_path(normalized):
            return True
    name = PurePosixPath(normalized).name
    deployment_names = {
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        "Procfile",
        "fly.toml",
        "railway.toml",
        "render.yaml",
    }
    return name in deployment_names or normalized.startswith(".github/workflows/")


def _is_lock_or_dependency_file(path: str, config: AutomationConfig) -> bool:
    name = PurePosixPath(_normalize(path)).name
    return name in set(config.forbidden_exact_names)


def _is_production_config(path: str) -> bool:
    normalized = _normalize(path)
    name = PurePosixPath(normalized).name.lower()
    if name in {"production.env", "prod.env", "secrets.yaml", "secrets.yml"}:
        return True
    if "production" in name and name.endswith(
        (".env", ".yml", ".yaml", ".json", ".toml", ".ini", ".cfg")
    ):
        return True
    return False


def _path_allowed(path: str, allowed_areas: list[str], always_allowed: tuple[str, ...]) -> bool:
    normalized = _normalize(path)
    if normalized in {_normalize(item) for item in always_allowed}:
        return True

    for area in allowed_areas:
        cleaned = _normalize(area).rstrip("/")
        if normalized == cleaned or normalized.startswith(cleaned + "/"):
            return True
    return False


def validate_changed_files(
    changed_files: list[str],
    allowed_areas: list[str],
    config: AutomationConfig,
) -> GuardrailResult:
    """Validate changed files against allowed areas and forbidden paths.

    Violations never discard changes automatically. The decision becomes
    ``human_review`` so a human can inspect the worktree.
    """
    violations: list[str] = []
    normalized_files = [_normalize(path) for path in changed_files]

    for file_name in normalized_files:
        if _is_env_file(file_name):
            violations.append(f"Forbidden .env file changed: {file_name}")
            continue
        if _is_migration_path(file_name):
            violations.append(f"Migration path changed: {file_name}")
            continue
        if _is_workflow_or_deployment(file_name, config):
            violations.append(
                f"Workflow/deployment path changed: {file_name}"
            )
            continue
        if _is_lock_or_dependency_file(file_name, config):
            violations.append(
                f"Dependency/lock or production packaging file changed: "
                f"{file_name}"
            )
            continue
        if _is_production_config(file_name):
            violations.append(
                f"Production configuration changed: {file_name}"
            )
            continue

        if not _path_allowed(
            file_name,
            allowed_areas,
            config.always_allowed_files,
        ):
            violations.append(f"File outside allowed areas: {file_name}")

    if len(normalized_files) > config.max_changed_files:
        violations.append(
            f"{len(normalized_files)} files changed; "
            f"maximum is {config.max_changed_files}."
        )

    ok = not violations
    return GuardrailResult(
        ok=ok,
        violations=violations,
        decision="approve" if ok else "human_review",
        changed_files=normalized_files,
    )
