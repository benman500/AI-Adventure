"""Scope and safety checks for changed files."""

from __future__ import annotations

from automation_v2.config import AutomationConfig
from automation_v2.models import GuardrailResult

# Orchestrator-generated runtime artifacts. Never treated as implementation.
RUNTIME_ARTIFACT_EXACT = frozenset(
    {
        "automation_v2/state.json",
        "automation_v2/AGENT_REPORT.md",
        "automation/AGENT_REPORT.md",
    }
)

RUNTIME_ARTIFACT_PREFIXES = (
    "automation_v2/runs/",
)


def normalize_repo_path(path: str) -> str:
    """Normalize a repository-relative path for comparisons."""
    return path.replace("\\", "/").strip()


def is_runtime_artifact(path: str) -> bool:
    """Return True for automation framework runtime artifacts."""
    normalized = normalize_repo_path(path)
    if normalized in RUNTIME_ARTIFACT_EXACT:
        return True
    return any(
        normalized.startswith(prefix) for prefix in RUNTIME_ARTIFACT_PREFIXES
    )


def filter_implementation_files(changed_files: list[str]) -> list[str]:
    """Drop runtime artifacts; keep real project implementation files."""
    return [
        normalize_repo_path(path)
        for path in changed_files
        if not is_runtime_artifact(path)
    ]


def collect_runtime_artifacts(changed_files: list[str]) -> list[str]:
    """Return runtime artifacts present in ``changed_files`` (diagnostics)."""
    return [
        normalize_repo_path(path)
        for path in changed_files
        if is_runtime_artifact(path)
    ]


def filter_diff_for_review(
    diff: dict[str, str | list[str] | bool],
) -> dict[str, str | list[str] | bool]:
    """Return a reviewer-facing diff that excludes runtime artifacts."""
    changed = diff.get("changed_files", [])
    if not isinstance(changed, list):
        changed = []
    all_files = [str(item) for item in changed]
    implementation_files = filter_implementation_files(all_files)
    runtime_artifacts = collect_runtime_artifacts(all_files)

    # Prefer an already-separated diagnostic list when present.
    existing_runtime = diff.get("runtime_artifacts")
    if isinstance(existing_runtime, list):
        runtime_artifacts = [
            normalize_repo_path(str(item)) for item in existing_runtime
        ]

    stat = str(diff.get("stat", ""))
    body = str(diff.get("diff", ""))
    note = (
        "Runtime artifacts excluded from implementation review: "
        "automation_v2/runs/**, automation_v2/state.json, "
        "automation/AGENT_REPORT.md, automation_v2/AGENT_REPORT.md.\n"
    )
    return {
        "stat": note + stat,
        "diff": body,
        "changed_files": implementation_files,
        "runtime_artifacts": runtime_artifacts,
        "runtime_artifacts_excluded": True,
    }


def validate_changed_files(
    changed_files: list[str],
    allowed_areas: list[str],
    config: AutomationConfig,
) -> GuardrailResult:
    """Validate changed files against task scope and safety restrictions.

    Runtime automation artifacts are recorded for diagnostics but ignored for
    scope decisions. Violations never discard changes automatically; the
    decision becomes human_review.
    """
    violations: list[str] = []

    normalized_allowed_areas = [
        area.replace("\\", "/").rstrip("/") for area in allowed_areas
    ]

    runtime_artifacts = collect_runtime_artifacts(changed_files)
    relevant_changed_files = filter_implementation_files(changed_files)

    forbidden_prefixes = tuple(config.forbidden_path_prefixes) + (".env.",)
    forbidden_names = {name.lower() for name in config.forbidden_exact_names}

    for normalized in relevant_changed_files:
        lower_name = normalized.lower()
        base_name = normalized.rsplit("/", 1)[-1]

        if (
            lower_name.startswith("alembic/versions/")
            or lower_name == "alembic/versions"
        ):
            violations.append(f"Migration path changed: {normalized}")
            continue

        if any(
            lower_name == prefix.lower().rstrip("/")
            or lower_name.startswith(prefix.lower())
            for prefix in forbidden_prefixes
        ):
            violations.append(f"Forbidden path changed: {normalized}")
            continue

        if base_name.lower() in forbidden_names:
            violations.append(
                f"Dependency or lock file changed: {normalized}"
            )
            continue

        allowed = any(
            normalized == area or normalized.startswith(area + "/")
            for area in normalized_allowed_areas
        )

        if not allowed:
            violations.append(f"File outside allowed areas: {normalized}")

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
        runtime_artifacts=runtime_artifacts,
    )
