"""OpenAI planner for automation_v2 using the Responses API."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Protocol

from automation_v2.config import AutomationConfig
from automation_v2.models import ApprovedPlan, TaskDefinition


class PlannerClient(Protocol):
    """Minimal OpenAI client surface used by the planner (mockable)."""

    def complete(self, *, instructions: str, input_text: str) -> str:
        """Return model output text."""


class OpenAIResponsesClient:
    """Thin wrapper around the official OpenAI Responses API."""

    def __init__(self, model: str) -> None:
        """Create a client. Reads ``OPENAI_API_KEY`` from the environment only."""
        # Import lazily so unit tests can mock without requiring network setup.
        from openai import OpenAI

        # OpenAI() reads OPENAI_API_KEY from the environment. Never log it.
        self._client = OpenAI()
        self._model = model

    def complete(self, *, instructions: str, input_text: str) -> str:
        """Call Responses API and return output text."""
        response = self._client.responses.create(
            model=self._model,
            instructions=instructions,
            input=input_text,
        )
        return response.output_text


PLANNER_INSTRUCTIONS = """
You are the supervising planner for an existing cultivation RPG.

Review the proposed queued task against the locked project context.

Return JSON only with this exact shape:

{
  "decision": "approve" | "human_review",
  "title": "short task title",
  "implementation_brief": "precise bounded instructions for Cursor",
  "allowed_areas": ["path prefixes"],
  "acceptance_criteria": ["criterion"],
  "focused_tests": ["pytest target"],
  "forbidden_changes": ["change"],
  "stop_conditions": ["condition"]
}

focused_tests rules (mandatory):

- focused_tests must be a JSON array of pytest targets only.
- Every entry must be exactly one of:
  - a test file path (for example tests/test_play_layout_ui.py),
  - a test directory path (for example tests or tests/automation_v2),
  - or a pytest node id (for example tests/test_foo.py::test_bar).
- Never output prose, commands, markdown, explanations, or instructions.
- Never output entries that start with "Run", "Please", or similar wording.
- Never output "python -m pytest...", "pytest ...", shell commands, or -k/-m
  option strings. Those belong elsewhere; focused_tests are targets only.
- If no focused tests can be determined, return an empty array: [].

Rules:

- Do not invent a larger task.
- Do not widen the queued task beyond its goal and allowed_areas.
- Do not add architecture.
- Do not add new systems.
- Keep the work inside the current milestone.
- Choose human_review if the task requires migrations, architecture changes,
  new dependencies, unclear product decisions, or gameplay-rule changes.
- For concrete implementation or redesign tasks (especially presentation/UI),
  write an implementation_brief that requires Cursor to inspect the current
  templates/CSS/tests, identify concrete deficiencies, and make meaningful
  changes to at least one allowed implementation file. Updating only reports,
  automation state, run logs, or automation framework files is not enough.
- Require criterion-by-criterion evidence in the completion report only when
  claiming every acceptance criterion is already satisfied before the run.
"""


_NODE_SEGMENT_RE = re.compile(
    r"^[A-Za-z_][\w]*(?:\[[^\]]+\])?$"
)


def is_valid_focused_test_target(entry: str) -> bool:
    """Return True when ``entry`` is a bare pytest file, directory, or node id.

    Rejects prose, commands, markdown, explanations, and option strings.
    """
    value = entry.strip().replace("\\", "/")
    if not value:
        return False
    if any(char.isspace() for char in value):
        return False
    if value.startswith("-"):
        return False
    if any(char in value for char in ("|", "&", ";", ">", "<", "`", "#", "*")):
        return False

    lower = value.lower()
    if lower in {"python", "pytest", "py"} or lower.endswith(".exe"):
        return False
    if lower.startswith(("python-", "pytest-")):
        return False

    if "::" in value:
        path_part, *node_parts = value.split("::")
        if not path_part.endswith(".py"):
            return False
        if not node_parts or any(not part for part in node_parts):
            return False
        if not _is_relative_test_path(path_part):
            return False
        return all(_NODE_SEGMENT_RE.match(part) for part in node_parts)

    if value.endswith(".py"):
        return _is_relative_test_path(value)

    return _is_relative_test_directory(value)


def _is_relative_test_path(path: str) -> bool:
    """Return True for a relative file path with ``.py`` suffix."""
    if not path.endswith(".py"):
        return False
    body = path[: -len(".py")]
    if not body or body.startswith("/") or body.startswith("~"):
        return False
    if len(body) >= 2 and body[1] == ":":
        return False
    if ".." in body.split("/"):
        return False
    return bool(re.match(r"^[\w][\w./-]*$", body))


def _is_relative_test_directory(path: str) -> bool:
    """Return True for a relative directory pytest target."""
    if not path or path.startswith("/") or path.startswith("~"):
        return False
    if len(path) >= 2 and path[1] == ":":
        return False
    if ".." in path.split("/"):
        return False
    name = path.rsplit("/", 1)[-1]
    if "." in name:
        return False
    if not re.match(r"^[\w][\w./-]*$", path):
        return False
    # Bare instructional words must not count as directories.
    if "/" not in path and path.lower() not in {"tests", "test"}:
        return False
    return True


def validate_focused_tests(entries: list[str]) -> list[str]:
    """Validate planner focused_tests as bare pytest targets only.

    Raises:
        ValueError: When any entry is prose, a command, or otherwise invalid.
    """
    validated: list[str] = []
    for entry in entries:
        if not isinstance(entry, str):
            raise ValueError("focused_tests entries must be strings")
        cleaned = entry.strip()
        if not cleaned:
            raise ValueError(
                "focused_tests must not contain empty strings; "
                "use [] when no focused tests apply"
            )
        lower = cleaned.lower()
        if lower.startswith(
            (
                "run ",
                "running ",
                "please ",
                "execute ",
                "invoke ",
                "use ",
                "call ",
                "python ",
                "pytest ",
                "py ",
            )
        ) or "-m pytest" in lower:
            raise ValueError(
                "focused_tests must contain pytest targets only, not prose "
                f"or commands: {entry!r}"
            )
        if not is_valid_focused_test_target(cleaned):
            raise ValueError(
                "focused_tests entries must be a test file, test directory, "
                f"or pytest node id; got: {entry!r}"
            )
        validated.append(cleaned.replace("\\", "/"))
    return validated


def clean_json_text(raw: str) -> str:
    """Strip markdown fences and optional leading ``json`` labels."""
    value = raw.strip()
    if value.startswith("```"):
        lines = value.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        value = "\n".join(lines).strip()
    if value.lstrip().lower().startswith("json"):
        value = value.lstrip()[4:].lstrip()
    return value


def parse_json_object(raw: str) -> dict[str, Any]:
    """Parse a JSON object from model output, raising ValueError on failure."""
    cleaned = clean_json_text(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise ValueError("Planner response is not valid JSON") from None
        data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("Planner JSON must be an object")
    return data


def _require_string_list(data: dict[str, Any], key: str) -> list[str]:
    value = data.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"Planner JSON field '{key}' must be a list of strings")
    return list(value)


def validate_plan_payload(
    data: dict[str, Any],
    task: TaskDefinition,
) -> ApprovedPlan:
    """Validate planner JSON and prevent widening the queued task."""
    decision = data.get("decision")
    if decision not in {"approve", "human_review"}:
        raise ValueError("Planner decision must be 'approve' or 'human_review'")

    title = data.get("title")
    brief = data.get("implementation_brief")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Planner title must be a non-empty string")
    if not isinstance(brief, str) or not brief.strip():
        raise ValueError("Planner implementation_brief must be a non-empty string")

    allowed_areas = _require_string_list(data, "allowed_areas")
    acceptance = _require_string_list(data, "acceptance_criteria")
    forbidden = _require_string_list(data, "forbidden_changes")
    focused = validate_focused_tests(_require_string_list(data, "focused_tests"))
    stops = _require_string_list(data, "stop_conditions")

    # Do not allow the planner to widen beyond the queued task areas.
    task_areas = {_normalize_area(area) for area in task.allowed_areas}
    for area in allowed_areas:
        cleaned = _normalize_area(area)
        if not any(
            cleaned == parent or cleaned.startswith(parent + "/")
            for parent in task_areas
        ):
            raise ValueError(
                "Planner widened allowed_areas beyond the queued task: "
                f"{area}"
            )

    return ApprovedPlan(
        decision=decision,  # type: ignore[arg-type]
        title=title.strip(),
        implementation_brief=brief.strip(),
        allowed_areas=allowed_areas,
        acceptance_criteria=acceptance,
        forbidden_changes=forbidden,
        focused_tests=focused,
        stop_conditions=stops,
    )


def _normalize_area(area: str) -> str:
    return area.replace("\\", "/").strip().strip("/")


def _requires_human_review_keywords(task: TaskDefinition) -> bool:
    """Heuristic local check for obvious human-review triggers in the task."""
    blob = " ".join(
        [
            task.title,
            task.goal,
            *task.acceptance_criteria,
        ]
    ).lower()
    triggers = (
        "migration",
        "alembic",
        "new dependency",
        "add dependency",
        "architecture change",
        "gameplay rule",
        "change game rules",
        "rewrite engine",
    )
    return any(token in blob for token in triggers)


def read_project_context(config: AutomationConfig) -> str:
    """Load required project context files as a single string."""
    sections: list[str] = []
    for relative in config.project_context_files:
        path = config.repository_root / relative
        if not path.exists():
            raise FileNotFoundError(f"Required file is missing: {path}")
        sections.append(
            f"\n\n===== {path.name} =====\n"
            + path.read_text(encoding="utf-8")
        )
    return "".join(sections)


class Planner:
    """Plan a queued task into one ApprovedPlan with JSON validation retries."""

    def __init__(
        self,
        config: AutomationConfig,
        client: PlannerClient | None = None,
    ) -> None:
        """Create a planner. Uses OpenAI when ``client`` is omitted."""
        self._config = config
        self._client = client or OpenAIResponsesClient(config.openai_model)

    def plan(
        self,
        task: TaskDefinition,
        context: str | None = None,
        *,
        max_json_retries: int = 2,
    ) -> ApprovedPlan:
        """Produce one ApprovedPlan.

        Malformed JSON is retried up to ``max_json_retries`` times
        (two retries => three total attempts). Returns ``human_review`` when
        the task is unsafe or JSON remains invalid.
        """
        if _requires_human_review_keywords(task):
            return ApprovedPlan(
                decision="human_review",
                title=task.title,
                implementation_brief=(
                    "Task appears to require migrations, architecture, "
                    "dependencies, or gameplay-rule changes."
                ),
                allowed_areas=list(task.allowed_areas),
                acceptance_criteria=list(task.acceptance_criteria),
                forbidden_changes=["Do not implement without human approval"],
                focused_tests=[],
                stop_conditions=["Await human review"],
            )

        locked = (
            context
            if context is not None
            else read_project_context(self._config)
        )
        input_text = locked + "\n\nQUEUED TASK:\n" + json.dumps(
            {
                "id": task.id,
                "title": task.title,
                "goal": task.goal,
                "allowed_areas": task.allowed_areas,
                "acceptance_criteria": task.acceptance_criteria,
            },
            indent=2,
        )

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
                instructions=PLANNER_INSTRUCTIONS,
                input_text=prompt,
            )
            try:
                payload = parse_json_object(raw)
                return validate_plan_payload(payload, task)
            except (ValueError, json.JSONDecodeError, TypeError, KeyError) as exc:
                last_error = str(exc)
                if attempt >= max_json_retries:
                    return ApprovedPlan(
                        decision="human_review",
                        title=task.title,
                        implementation_brief=(
                            "Planner returned malformed JSON repeatedly: "
                            f"{last_error}"
                        ),
                        allowed_areas=list(task.allowed_areas),
                        acceptance_criteria=list(task.acceptance_criteria),
                        forbidden_changes=["Do not implement"],
                        focused_tests=[],
                        stop_conditions=["Await human review"],
                    )

        raise RuntimeError("Planner retry loop exited unexpectedly")


def save_plan(plan: ApprovedPlan, path: Path) -> None:
    """Write an approved plan JSON file."""
    path.write_text(json.dumps(plan.to_dict(), indent=2), encoding="utf-8")
