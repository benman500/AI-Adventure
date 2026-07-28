"""OpenAI reviewer for automation_v2 using the Responses API."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from automation_v2.config import AutomationConfig
from automation_v2.guardrails import (
    filter_diff_for_review,
    filter_substantive_implementation_files,
)
from automation_v2.models import (
    ApprovedPlan,
    GuardrailResult,
    ReviewResult,
    TestResult,
    VALID_REVIEW_DECISIONS,
)
from automation_v2.planner import (
    OpenAIResponsesClient,
    parse_json_object,
)


class ReviewerClient(Protocol):
    """Minimal OpenAI client surface used by the reviewer (mockable)."""

    def complete(self, *, instructions: str, input_text: str) -> str:
        """Return model output text."""


REVIEWER_INSTRUCTIONS = """
You are the supervising reviewer for an existing cultivation RPG.

Judge the implementation only against the approved task, locked architecture,
test results, changed files, diff, and the implementation report.

Ignore automation framework runtime artifacts when judging scope. These files
are produced by the orchestrator for diagnostics and are not implementation
work. Do not request human review merely because they appear in a raw worktree:

- automation_v2/runs/**
- automation_v2/state.json
- automation/AGENT_REPORT.md
- automation_v2/AGENT_REPORT.md

The supplied changed_files list and diff are already filtered to implementation
files (templates, CSS, Python, tests, assets, and similar project files).
Judge allowed-area scope only from that filtered evidence.

For presentation or UI tasks, modifying only reports, automation state, run
logs, or automation framework files does not count as implementing the task.

If the task required a concrete implementation or redesign, no allowed
implementation files changed, and the implementation report lacks specific
criterion-by-criterion evidence that every acceptance criterion was already
satisfied before the run, you must choose repair.

You may approve a no-change result only when the implementation report contains
specific evidence for each acceptance criterion showing it was already
satisfied before the run.

Return JSON only:

{
  "decision": "approve" | "repair" | "human_review",
  "summary": "review summary",
  "repair_instructions": ["specific repair"],
  "risks": ["risk"]
}

Approve only when:

- acceptance criteria are satisfied,
- tests pass,
- the task stayed in scope,
- no architecture or game-rule changes were introduced,
- no tests were weakened or deleted merely to make the task pass,
- and either allowed implementation files changed, or the report proves every
  criterion was already satisfied before the run.

Never approve failed tests.
Never approve scope violations.
Never approve weakened or deleted tests merely to make the task pass.
Never approve a silent no-op or report-only completion for an implementation
or redesign task.

Choose human_review for:

- migrations,
- dependency changes,
- destructive changes,
- new architecture,
- ambiguous design decisions,
- suspiciously broad refactors,
- changes outside allowed areas in the filtered implementation file list.
"""

_IMPLEMENTATION_KEYWORDS = (
    "redesign",
    "implement",
    "modernize",
    "improve",
    "create",
    "update",
    "refactor",
    "presentation",
    "template",
    "css",
    "layout",
    "visual",
    "ui",
    "card",
    "character creation",
    "character-creation",
)

_ALREADY_COMPLETE_MARKERS = (
    "already satisfied criteria",
    "already satisfied",
    "already met",
    "already complete",
    "already present",
    "already implemented",
    "before this run",
    "before the run",
)

_REPORT_CANDIDATES = (
    "automation/AGENT_REPORT.md",
    "automation_v2/AGENT_REPORT.md",
)


def plan_requires_implementation(plan: ApprovedPlan) -> bool:
    """Return True when the plan asks for concrete implementation work."""
    text = " ".join(
        [
            plan.title,
            plan.implementation_brief,
            *plan.acceptance_criteria,
        ]
    ).lower()
    return any(keyword in text for keyword in _IMPLEMENTATION_KEYWORDS)


def load_implementation_report(repository_root: Path) -> str:
    """Load the newest available agent completion report text."""
    chunks: list[str] = []
    for relative in _REPORT_CANDIDATES:
        path = repository_root / relative
        if path.is_file():
            chunks.append(path.read_text(encoding="utf-8"))
    return "\n\n".join(chunks)


def report_has_criterion_by_criterion_evidence(
    report_text: str,
    acceptance_criteria: list[str],
) -> bool:
    """Return True when the report evidences each criterion as already done."""
    if not report_text.strip() or not acceptance_criteria:
        return False

    lower = report_text.lower()
    if not any(marker in lower for marker in _ALREADY_COMPLETE_MARKERS):
        return False
    if "already satisfied criteria" not in lower:
        return False

    for criterion in acceptance_criteria:
        key = " ".join(criterion.lower().split())
        if not key:
            return False
        snippet = key[:60]
        if snippet not in lower:
            return False
    return True


def silent_noop_repair_result(plan: ApprovedPlan) -> ReviewResult:
    """Build a deterministic repair decision for empty implementation work."""
    return ReviewResult(
        decision="repair",
        summary=(
            "The task required implementation, but no allowed implementation "
            "files changed and the completion report lacks criterion-by-criterion "
            "evidence that every acceptance criterion was already satisfied."
        ),
        repair_instructions=[
            "Inspect the existing implementation in the allowed areas "
            "(templates, CSS, presentation tests, and assets as applicable).",
            "Identify concrete deficiencies relative to each acceptance criterion.",
            "Make meaningful changes to at least one allowed implementation file. "
            "Modifying only reports, automation state, run logs, or automation "
            "framework files does not count.",
            "Preserve routes, form field names, submitted values, validation, "
            "and gameplay behavior.",
            "Update or add focused presentation tests when necessary.",
            "Run focused tests and the full suite.",
            "Repair the implementation rather than merely rewriting the report.",
            *[f"Acceptance criterion: {item}" for item in plan.acceptance_criteria],
        ],
        risks=["Silent no-op or report-only completion"],
    )


def validate_review_payload(data: dict[str, Any]) -> ReviewResult:
    """Validate reviewer JSON into a ReviewResult."""
    decision = data.get("decision")
    if decision not in VALID_REVIEW_DECISIONS:
        raise ValueError(
            "Review decision must be one of: approve, repair, human_review"
        )
    summary = data.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("Review summary must be a non-empty string")

    repairs = data.get("repair_instructions", [])
    risks = data.get("risks", [])
    if not isinstance(repairs, list) or not all(
        isinstance(item, str) for item in repairs
    ):
        raise ValueError("repair_instructions must be a list of strings")
    if not isinstance(risks, list) or not all(
        isinstance(item, str) for item in risks
    ):
        raise ValueError("risks must be a list of strings")

    return ReviewResult(
        decision=decision,  # type: ignore[arg-type]
        summary=summary.strip(),
        repair_instructions=list(repairs),
        risks=list(risks),
    )


def apply_hard_review_rules(
    result: ReviewResult,
    *,
    plan: ApprovedPlan,
    tests: TestResult,
    guardrails: GuardrailResult,
    substantive_files: list[str],
    report_text: str,
) -> ReviewResult:
    """Override model decisions that violate non-negotiable rules."""
    if not tests.passed or tests.timed_out:
        if result.decision == "approve":
            return ReviewResult(
                decision="repair",
                summary=(
                    "Tests failed or timed out; approval is not allowed. "
                    + result.summary
                ),
                repair_instructions=result.repair_instructions
                or ["Fix failing tests without weakening or deleting them."],
                risks=result.risks + ["Failed tests blocked approval"],
            )
    if not guardrails.ok:
        return ReviewResult(
            decision="human_review",
            summary=(
                "Scope or safety guardrails were violated; "
                "human review required. "
                + result.summary
            ),
            repair_instructions=[],
            risks=result.risks + list(guardrails.violations),
        )

    if (
        plan_requires_implementation(plan)
        and not substantive_files
        and not report_has_criterion_by_criterion_evidence(
            report_text,
            plan.acceptance_criteria,
        )
    ):
        if result.decision == "approve":
            return silent_noop_repair_result(plan)
    return result


class Reviewer:
    """Review implementation evidence and return a structured decision."""

    def __init__(
        self,
        config: AutomationConfig,
        client: ReviewerClient | None = None,
    ) -> None:
        """Create a reviewer. Uses OpenAI when ``client`` is omitted."""
        self._config = config
        self._client = client or OpenAIResponsesClient(config.openai_model)

    def review(
        self,
        *,
        plan: ApprovedPlan,
        tests: TestResult,
        guardrails: GuardrailResult,
        diff: dict[str, Any],
        context: str,
        max_json_retries: int = 2,
    ) -> ReviewResult:
        """Review evidence with JSON validation and hard rule overrides.

        Malformed JSON is retried up to ``max_json_retries`` times.
        """
        # Hard fail before spending tokens when clearly unsafe/incomplete.
        if not guardrails.ok:
            return ReviewResult(
                decision="human_review",
                summary="Guardrail violations require human review.",
                repair_instructions=[],
                risks=list(guardrails.violations),
            )
        if not tests.passed or tests.timed_out:
            return ReviewResult(
                decision="repair",
                summary="Tests did not pass; repair required before approval.",
                repair_instructions=[
                    "Fix failing tests without weakening or deleting them.",
                    "Re-run focused tests and the full suite.",
                ],
                risks=["Failed or timed-out tests"],
            )

        filtered_diff = filter_diff_for_review(diff)
        changed = filtered_diff.get("changed_files", [])
        if not isinstance(changed, list):
            changed = []
        substantive_files = filter_substantive_implementation_files(
            [str(item) for item in changed],
            plan.allowed_areas,
        )
        report_text = load_implementation_report(self._config.repository_root)

        if (
            plan_requires_implementation(plan)
            and not substantive_files
            and not report_has_criterion_by_criterion_evidence(
                report_text,
                plan.acceptance_criteria,
            )
        ):
            return silent_noop_repair_result(plan)

        payload = {
            "plan": plan.to_dict(),
            "tests": {
                "passed": tests.passed,
                "returncode": tests.returncode,
                "timed_out": tests.timed_out,
                "focused_passed": tests.focused_passed,
                "stdout_tail": tests.stdout[-15000:],
                "stderr_tail": tests.stderr[-8000:],
                "log_file": tests.log_file,
            },
            "guardrails": guardrails.to_dict(),
            "diff": filtered_diff,
            "substantive_implementation_files": substantive_files,
            "implementation_report": report_text[-20000:],
            "locked_context": context,
        }
        input_text = json.dumps(payload, indent=2)

        last_error = "unknown"
        attempts = max_json_retries + 1
        for attempt in range(attempts):
            prompt = input_text
            if attempt > 0:
                prompt = (
                    input_text
                    + "\n\nPREVIOUS RESPONSE WAS INVALID JSON. "
                    "Return JSON only matching the required schema. "
                    f"Parse error: {last_error}"
                )
            raw = self._client.complete(
                instructions=REVIEWER_INSTRUCTIONS,
                input_text=prompt,
            )
            try:
                data = parse_json_object(raw)
                result = validate_review_payload(data)
                return apply_hard_review_rules(
                    result,
                    plan=plan,
                    tests=tests,
                    guardrails=guardrails,
                    substantive_files=substantive_files,
                    report_text=report_text,
                )
            except (ValueError, json.JSONDecodeError, TypeError, KeyError) as exc:
                last_error = str(exc)
                if attempt >= max_json_retries:
                    return ReviewResult(
                        decision="human_review",
                        summary=(
                            "Reviewer returned malformed JSON repeatedly: "
                            f"{last_error}"
                        ),
                        repair_instructions=[],
                        risks=["Invalid reviewer JSON"],
                    )

        raise RuntimeError("Reviewer retry loop exited unexpectedly")


def save_review(review: ReviewResult, path: Path) -> None:
    """Write a review JSON file."""
    path.write_text(json.dumps(review.to_dict(), indent=2), encoding="utf-8")
