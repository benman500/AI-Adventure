from __future__ import annotations

from automation_v2.models import GuardrailResult

from automation_v2.config import AutomationConfig

INTERNAL_AUTOMATION_PATHS = (
    "automation_v2/runs/",
    "automation_v2/state.json",
    "automation_v2/AGENT_REPORT.md",
)

FORBIDDEN_PATH_PREFIXES = (
    ".env",
    ".env.",
    "alembic/versions/",
    ".github/workflows/",
)

FORBIDDEN_FILE_NAMES = {
    "requirements.txt",
    "requirements.lock",
    "poetry.lock",
    "pdm.lock",
    "Pipfile.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
}


def validate_changed_files(
    changed_files: list[str],
    allowed_areas: list[str],
    config: AutomationConfig,
) -> GuardrailResult:
    """
    Validate changed files against task scope and safety restrictions.

    Violations never discard changes automatically. The decision becomes
    human_review so a human can inspect the worktree.
    """
    violations: list[str] = []

    normalized_allowed_areas = [
        area.replace("\\", "/").rstrip("/")
        for area in allowed_areas
    ]

    relevant_changed_files: list[str] = []

    for file_name in changed_files:
        normalized = file_name.replace("\\", "/")

        # Runtime logs and state are produced by the orchestrator itself,
        # not by the implementation task.
        if any(
            normalized == internal.rstrip("/")
            or normalized.startswith(internal)
            for internal in INTERNAL_AUTOMATION_PATHS
        ):
            continue

        relevant_changed_files.append(normalized)

        lower_name = normalized.lower()
        base_name = normalized.rsplit("/", 1)[-1]

        if lower_name.startswith("alembic/versions/") or lower_name == "alembic/versions":
            violations.append(f"Migration path changed: {normalized}")
            continue

        if any(
            lower_name == prefix.lower().rstrip("/")
            or lower_name.startswith(prefix.lower())
            for prefix in FORBIDDEN_PATH_PREFIXES
        ):
            violations.append(f"Forbidden path changed: {normalized}")
            continue

        if base_name in FORBIDDEN_FILE_NAMES:
            violations.append(
                f"Dependency or lock file changed: {normalized}"
            )
            continue

        allowed = any(
            normalized == area
            or normalized.startswith(area + "/")
            for area in normalized_allowed_areas
        )

        if not allowed:
            violations.append(
                f"File outside allowed areas: {normalized}"
            )

    if len(relevant_changed_files) > config.max_changed_files:
        violations.append(
            f"{len(relevant_changed_files)} files changed; "
            f"maximum is {config.max_changed_files}."
        )

    return GuardrailResult(
        ok=not violations,
        violations=violations,
        decision="approve" if not violations else "human_review",
        changed_files=relevant_changed_files,
    )