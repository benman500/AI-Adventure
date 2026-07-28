"""Typed models for the automation_v2 framework."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

ReviewDecision = Literal["approve", "repair", "human_review"]
PlanDecision = Literal["approve", "human_review"]
Stage = Literal[
    "queued",
    "planning",
    "implementing",
    "testing",
    "reviewing",
    "repairing",
    "approved",
    "human_review",
    "failed",
]

VALID_STAGES: frozenset[str] = frozenset(
    {
        "queued",
        "planning",
        "implementing",
        "testing",
        "reviewing",
        "repairing",
        "approved",
        "human_review",
        "failed",
    }
)

VALID_REVIEW_DECISIONS: frozenset[str] = frozenset(
    {"approve", "repair", "human_review"}
)


@dataclass(frozen=True)
class CommandResult:
    """Result of a subprocess invocation."""

    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool


@dataclass(frozen=True)
class TaskDefinition:
    """A queued automation task loaded from tasks.json."""

    id: str
    title: str
    goal: str
    allowed_areas: list[str]
    acceptance_criteria: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskDefinition:
        """Build a task definition from a JSON object."""
        return cls(
            id=str(data["id"]),
            title=str(data["title"]),
            goal=str(data["goal"]),
            allowed_areas=[str(item) for item in data["allowed_areas"]],
            acceptance_criteria=[
                str(item) for item in data["acceptance_criteria"]
            ],
        )


@dataclass(frozen=True)
class ApprovedPlan:
    """Planner output after validation."""

    decision: PlanDecision
    title: str
    implementation_brief: str
    allowed_areas: list[str]
    acceptance_criteria: list[str]
    forbidden_changes: list[str]
    focused_tests: list[str]
    stop_conditions: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the plan for persistence and prompts."""
        return asdict(self)


@dataclass(frozen=True)
class TestResult:
    """Structured result of focused and/or full pytest runs.

    Named ``TestResult`` for the framework domain model. Pytest collection is
    avoided by keeping this module outside ``tests/``.
    """

    passed: bool
    returncode: int
    stdout: str
    stderr: str
    log_file: str
    focused_passed: bool | None = None
    timed_out: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize for evidence payloads."""
        return asdict(self)


# Prevent pytest from collecting this domain model when imported by tests.
TestResult.__test__ = False  # type: ignore[attr-defined]


@dataclass(frozen=True)
class GuardrailResult:
    """Outcome of scope and safety checks on changed files."""

    ok: bool
    violations: list[str]
    decision: Literal["approve", "human_review"]
    changed_files: list[str]
    # Orchestrator runtime artifacts kept for diagnostics only.
    runtime_artifacts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize for evidence payloads."""
        return asdict(self)


@dataclass(frozen=True)
class ReviewResult:
    """Reviewer decision after validating structured JSON."""

    decision: ReviewDecision
    summary: str
    repair_instructions: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize for persistence."""
        return asdict(self)


@dataclass
class AutomationState:
    """Persisted automation progress for crash-safe resume."""

    task_id: str | None = None
    current_stage: Stage = "queued"
    attempt_number: int = 0
    last_successful_stage: str | None = None
    last_error: str | None = None
    started_at: str | None = None
    completed_tasks: list[str] = field(default_factory=list)
    run_dir: str | None = None
    repair_instructions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize state for atomic JSON persistence."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AutomationState:
        """Load state from a JSON object."""
        stage = str(data.get("current_stage", "queued"))
        if stage not in VALID_STAGES:
            stage = "queued"
        return cls(
            task_id=data.get("task_id"),
            current_stage=stage,  # type: ignore[arg-type]
            attempt_number=int(data.get("attempt_number", 0)),
            last_successful_stage=data.get("last_successful_stage"),
            last_error=data.get("last_error"),
            started_at=data.get("started_at"),
            completed_tasks=[
                str(item) for item in data.get("completed_tasks", [])
            ],
            run_dir=data.get("run_dir"),
            repair_instructions=[
                str(item) for item in data.get("repair_instructions", [])
            ],
        )
