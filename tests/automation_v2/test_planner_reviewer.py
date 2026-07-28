"""Tests for planner and reviewer JSON handling without real API calls."""

from __future__ import annotations

from pathlib import Path

from automation_v2.config import load_config
from automation_v2.models import (
    ApprovedPlan,
    GuardrailResult,
    TaskDefinition,
    TestResult,
)
from automation_v2.planner import Planner, parse_json_object, validate_plan_payload
from automation_v2.reviewer import Reviewer, validate_review_payload


ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_config(ROOT)

TASK = TaskDefinition(
    id="ui-01",
    title="Create story-first play layout",
    goal="Refactor play layout without gameplay changes.",
    allowed_areas=[
        "src/ai_adventure/presentation/templates",
        "src/ai_adventure/presentation/static",
        "tests",
    ],
    acceptance_criteria=["All tests pass"],
)


class ScriptedClient:
    """Return scripted completions for planner/reviewer tests."""

    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.calls = 0
        self.last_input_text = ""
        self.last_instructions = ""

    def complete(self, *, instructions: str, input_text: str) -> str:
        self.last_instructions = instructions
        self.last_input_text = input_text
        index = min(self.calls, len(self.responses) - 1)
        self.calls += 1
        return self.responses[index]


VALID_PLAN_JSON = """
{
  "decision": "approve",
  "title": "Create story-first play layout",
  "implementation_brief": "Adjust templates and CSS only.",
  "allowed_areas": [
    "src/ai_adventure/presentation/templates",
    "src/ai_adventure/presentation/static",
    "tests"
  ],
  "acceptance_criteria": ["All tests pass"],
  "forbidden_changes": ["No gameplay changes"],
  "focused_tests": ["tests/test_play_layout_ui.py"],
  "stop_conditions": ["Stop if ambiguous"]
}
"""


def test_parse_json_object_strips_fences() -> None:
    """Markdown-fenced JSON is accepted."""
    data = parse_json_object("```json\n{\"decision\": \"approve\"}\n```")
    assert data["decision"] == "approve"


def test_planner_retries_malformed_json() -> None:
    """Malformed planner JSON is retried without calling a real API."""
    client = ScriptedClient(
        [
            "not json",
            "{still bad",
            VALID_PLAN_JSON,
        ]
    )
    planner = Planner(CONFIG, client=client)
    plan = planner.plan(TASK, context="locked context")
    assert plan.decision == "approve"
    assert client.calls == 3


def test_planner_human_review_after_retry_exhaustion() -> None:
    """Repeated malformed JSON yields human_review."""
    client = ScriptedClient(["nope", "still nope", "again nope"])
    planner = Planner(CONFIG, client=client)
    plan = planner.plan(TASK, context="locked context")
    assert plan.decision == "human_review"
    assert client.calls == 3


def test_planner_rejects_widened_allowed_areas() -> None:
    """Planner output cannot widen beyond the queued task areas."""
    payload = parse_json_object(VALID_PLAN_JSON)
    payload["allowed_areas"] = [
        "src/ai_adventure/presentation/templates",
        "src/ai_adventure/engine",
    ]
    try:
        validate_plan_payload(payload, TASK)
        raised = False
    except ValueError:
        raised = True
    assert raised is True


def test_reviewer_retries_malformed_json() -> None:
    """Malformed reviewer JSON is retried with a mock client."""
    client = ScriptedClient(
        [
            "not json",
            '{"decision": "approve", "summary": "ok", '
            '"repair_instructions": [], "risks": []}',
        ]
    )
    reviewer = Reviewer(CONFIG, client=client)
    plan = ApprovedPlan(
        decision="approve",
        title="t",
        implementation_brief="b",
        allowed_areas=list(TASK.allowed_areas),
        acceptance_criteria=["ok"],
        forbidden_changes=[],
        focused_tests=[],
        stop_conditions=[],
    )
    tests = TestResult(
        passed=True,
        returncode=0,
        stdout="ok",
        stderr="",
        log_file="pytest.txt",
    )
    guardrails = GuardrailResult(
        ok=True,
        violations=[],
        decision="approve",
        changed_files=["tests/a.py"],
    )
    result = reviewer.review(
        plan=plan,
        tests=tests,
        guardrails=guardrails,
        diff={"stat": "", "diff": "", "changed_files": []},
        context="ctx",
    )
    assert result.decision == "approve"
    assert client.calls == 2


def test_reviewer_never_approves_failed_tests() -> None:
    """Failed tests force repair without needing a model call."""
    client = ScriptedClient([])
    reviewer = Reviewer(CONFIG, client=client)
    plan = ApprovedPlan(
        decision="approve",
        title="t",
        implementation_brief="b",
        allowed_areas=list(TASK.allowed_areas),
        acceptance_criteria=["ok"],
        forbidden_changes=[],
        focused_tests=[],
        stop_conditions=[],
    )
    tests = TestResult(
        passed=False,
        returncode=1,
        stdout="FAILED",
        stderr="",
        log_file="pytest.txt",
    )
    guardrails = GuardrailResult(
        ok=True,
        violations=[],
        decision="approve",
        changed_files=[],
    )
    result = reviewer.review(
        plan=plan,
        tests=tests,
        guardrails=guardrails,
        diff={},
        context="ctx",
    )
    assert result.decision == "repair"
    assert client.calls == 0


def test_reviewer_never_approves_scope_violations() -> None:
    """Guardrail violations force human_review."""
    client = ScriptedClient(
        [
            '{"decision": "approve", "summary": "looks fine", '
            '"repair_instructions": [], "risks": []}'
        ]
    )
    reviewer = Reviewer(CONFIG, client=client)
    plan = ApprovedPlan(
        decision="approve",
        title="t",
        implementation_brief="b",
        allowed_areas=list(TASK.allowed_areas),
        acceptance_criteria=["ok"],
        forbidden_changes=[],
        focused_tests=[],
        stop_conditions=[],
    )
    result = reviewer.review(
        plan=plan,
        tests=TestResult(
            passed=True,
            returncode=0,
            stdout="",
            stderr="",
            log_file="x",
        ),
        guardrails=GuardrailResult(
            ok=False,
            violations=["File outside allowed areas: secrets.env"],
            decision="human_review",
            changed_files=["secrets.env"],
        ),
        diff={},
        context="ctx",
    )
    assert result.decision == "human_review"
    assert client.calls == 0


def test_reviewer_filters_runtime_artifacts_from_diff_payload() -> None:
    """Reviewer evidence ignores automation runtime artifacts for scope."""
    import json

    client = ScriptedClient(
        [
            '{"decision": "approve", "summary": "in scope", '
            '"repair_instructions": [], "risks": []}'
        ]
    )
    reviewer = Reviewer(CONFIG, client=client)
    plan = ApprovedPlan(
        decision="approve",
        title="t",
        implementation_brief="b",
        allowed_areas=list(TASK.allowed_areas),
        acceptance_criteria=["ok"],
        forbidden_changes=[],
        focused_tests=[],
        stop_conditions=[],
    )
    result = reviewer.review(
        plan=plan,
        tests=TestResult(
            passed=True,
            returncode=0,
            stdout="298 passed",
            stderr="",
            log_file="pytest.txt",
        ),
        guardrails=GuardrailResult(
            ok=True,
            violations=[],
            decision="approve",
            changed_files=[
                "src/ai_adventure/presentation/templates/new_game.html"
            ],
            runtime_artifacts=[
                "automation_v2/runs/x/review_0.json",
                "automation_v2/state.json",
                "automation/AGENT_REPORT.md",
            ],
        ),
        diff={
            "stat": "includes runtime noise",
            "diff": "raw",
            "changed_files": [
                "automation_v2/runs/x/review_0.json",
                "automation_v2/state.json",
                "automation/AGENT_REPORT.md",
                "automation_v2/AGENT_REPORT.md",
                "src/ai_adventure/presentation/templates/new_game.html",
            ],
        },
        context="ctx",
    )
    assert result.decision == "approve"
    assert "automation_v2/runs" in client.last_instructions
    payload = json.loads(client.last_input_text)
    assert payload["diff"]["changed_files"] == [
        "src/ai_adventure/presentation/templates/new_game.html"
    ]
    assert payload["diff"]["runtime_artifacts_excluded"] is True
    assert "automation/AGENT_REPORT.md" not in payload["diff"]["changed_files"]


def test_validate_review_payload_rejects_unknown_decision() -> None:
    """Review decisions are limited to approve/repair/human_review."""
    try:
        validate_review_payload(
            {
                "decision": "ship_it",
                "summary": "nope",
                "repair_instructions": [],
                "risks": [],
            }
        )
        raised = False
    except ValueError:
        raised = True
    assert raised is True
