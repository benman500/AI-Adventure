"""OpenAI reviewer for automation_v2 using the Responses API."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from automation_v2.config import AutomationConfig
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
from automation_v2.guardrails import filter_diff_for_review


class ReviewerClient(Protocol):
    """Minimal OpenAI client surface used by the reviewer (mockable)."""

    def complete(self, *, instructions: str, input_text: str) -> str:
        """Return model output text."""


REVIEWER_INSTRUCTIONS = """
You are the supervising reviewer for an existing cultivation RPG.

Judge the implementation only against the approved task, locked architecture,
test results, changed files, and diff.

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
- no tests were weakened or deleted merely to make the task pass.

Never approve failed tests.
Never approve scope violations.
Never approve weakened or deleted tests merely to make the task pass.

Choose human_review for:

- migrations,
- dependency changes,
- destructive changes,
- new architecture,
- ambiguous design decisions,
- suspiciously broad refactors,
- changes outside allowed areas in the filtered implementation file list.
"""


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
    tests: TestResult,
    guardrails: GuardrailResult,
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
            "diff": filter_diff_for_review(diff),
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
                    tests=tests,
                    guardrails=guardrails,
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
