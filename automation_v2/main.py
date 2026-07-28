"""Coordinate automation_v2 modules. Implementation logic lives elsewhere."""

from __future__ import annotations

import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from automation_v2.config import AutomationConfig, load_config
from automation_v2.cursor_runner import CursorNotFoundError, invoke_cursor
from automation_v2.git_manager import GitError, GitManager
from automation_v2.guardrails import validate_changed_files
from automation_v2.models import (
    ApprovedPlan,
    AutomationState,
    TaskDefinition,
)
from automation_v2.planner import Planner, read_project_context, save_plan
from automation_v2.reviewer import Reviewer, save_review
from automation_v2.state_manager import StateManager
from automation_v2.test_runner import run_tests


def load_tasks(path: Path) -> list[TaskDefinition]:
    """Load the task queue from tasks.json."""
    if not path.exists():
        raise FileNotFoundError(f"Task queue not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError(f"{path} must contain a non-empty JSON list")
    return [TaskDefinition.from_dict(item) for item in data]


def make_run_directory(runs_dir: Path, task_id: str) -> Path:
    """Create a timestamped run directory for a task."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = runs_dir / f"{timestamp}-{task_id}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_cursor_prompt(
    plan: ApprovedPlan,
    repair_instructions: list[str] | None = None,
    *,
    test_output: str | None = None,
    changed_files: list[str] | None = None,
) -> str:
    """Build the Cursor agent prompt for an approved plan or repair pass."""
    presentation_task = any(
        "presentation" in area.replace("\\", "/")
        or area.replace("\\", "/").endswith("/templates")
        or "/templates" in area.replace("\\", "/")
        or "/static" in area.replace("\\", "/")
        for area in plan.allowed_areas
    )
    character_creation_task = any(
        token in f"{plan.title}\n{plan.implementation_brief}".lower()
        for token in ("character creation", "character-creation", "new_game")
    )

    prompt = f"""
Read AGENTS.md, PROJECT_CONTEXT.md, and CURRENT_MILESTONE.md first.

Implement exactly this approved task:

TITLE:
{plan.title}

IMPLEMENTATION BRIEF:
{plan.implementation_brief}

ALLOWED AREAS:
{json.dumps(plan.allowed_areas, indent=2)}

ACCEPTANCE CRITERIA:
{json.dumps(plan.acceptance_criteria, indent=2)}

FORBIDDEN CHANGES:
{json.dumps(plan.forbidden_changes, indent=2)}

STOP CONDITIONS:
{json.dumps(plan.stop_conditions, indent=2)}

Instructions:

1. Inspect the relevant implementation and tests.
2. Stay within the approved scope.
3. Make the smallest coherent implementation.
4. Run focused tests while working.
5. Run the full test suite before finishing.
6. Do not commit, push, merge, migrate, or install dependencies.
7. If blocked or ambiguous, stop and explain in automation_v2/AGENT_REPORT.md.
8. Write automation_v2/AGENT_REPORT.md when complete.

No silent no-op completions:

9. If every acceptance criterion is already satisfied, provide specific evidence
   for each criterion in the completion report under a heading named
   "Already satisfied criteria", with one bullet per criterion in the form:
   - <criterion text>: <specific evidence from the current code/UI before this run>
   Otherwise, make meaningful changes to at least one allowed implementation
   file (templates, CSS, presentation Python/tests, or assets as applicable).
10. For presentation or UI tasks, modifying only reports, automation state,
    run logs, or automation framework files does not count as implementing
    the task.

Temporary files and test execution:

11. Do not create temporary PowerShell, batch, shell, Python, helper, or ad hoc
    test-runner scripts anywhere in the repository (for example .ps1, .bat,
    .cmd, .sh, or one-off .py runners).
12. Do not add project-root scripts (for example run_ui_tests.ps1) or expand
    allowed areas to include them. Guardrails must not be weakened.
13. Run approved test commands directly in the terminal
    (for example: python -m pytest -q). Never create a script to wrap tests.
14. Temporary diagnostic files may only be written inside the current
    automation_v2 run directory. Never write temporary files to the
    repository root or application directories.
"""

    if presentation_task:
        prompt += """
Presentation / UI requirements:

15. Inspect the current templates and CSS in the allowed areas.
16. Identify concrete presentation deficiencies relative to the acceptance
    criteria before editing.
17. Implement the redesign with meaningful template/CSS/test changes unless
    you can demonstrate every acceptance criterion is already satisfied.
18. Preserve routes, form field names, submitted values, validation behavior,
    and gameplay behavior.
19. Update or add focused presentation tests when necessary.
20. Run focused tests and the full suite before finishing.
"""

    if character_creation_task:
        prompt += """
Character-creation specifics:

21. Inspect the existing character-creation template(s) and related CSS.
22. Identify concrete deficiencies (grouping, clickable background cards,
    answer placement, selected/hover/focus states, responsive layout).
23. Implement the redesign in those presentation files unless every acceptance
    criterion is already satisfied with criterion-by-criterion evidence.
24. Preserve character-creation routes, form field names, submitted values,
    validation, and gameplay behavior.
25. Update or add focused presentation tests when necessary, then run focused
    tests and the full suite.
"""

    if repair_instructions:
        prompt += "\n\nREVIEW REPAIRS REQUIRED:\n"
        prompt += "\n".join(f"- {item}" for item in repair_instructions)
        prompt += "\n\nORIGINAL ACCEPTANCE CRITERIA:\n"
        prompt += "\n".join(
            f"- {item}" for item in plan.acceptance_criteria
        )
        if changed_files is not None:
            prompt += "\n\nCHANGED FILES FROM PREVIOUS ATTEMPT:\n"
            if changed_files:
                prompt += "\n".join(f"- {item}" for item in changed_files)
            else:
                prompt += (
                    "- (none — no allowed implementation files changed; "
                    "this is a silent no-op unless criterion-by-criterion "
                    "evidence proves the task was already complete)"
                )
        if test_output:
            prompt += "\n\nTEST OUTPUT FROM PREVIOUS ATTEMPT:\n"
            prompt += test_output[-12000:]
        prompt += (
            "\n\nRepair the implementation rather than merely rewriting the "
            "report. Make meaningful changes to at least one allowed "
            "implementation file unless every acceptance criterion is already "
            "satisfied with specific criterion-by-criterion evidence."
            "\nThe PowerShell/batch/shell/Python script ban and run-directory "
            "diagnostic-file limit above still apply during repair."
        )
    return prompt


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _elapsed_hours(start: float) -> float:
    return (time.monotonic() - start) / 3600.0


def _save_traceback(run_dir: Path | None, exc: BaseException) -> Path | None:
    if run_dir is None:
        return None
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "unexpected_error.txt"
    path.write_text(
        "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
        encoding="utf-8",
    )
    return path


class Orchestrator:
    """Process one automation task at a time with crash-safe state."""

    def __init__(
        self,
        config: AutomationConfig,
        *,
        git: GitManager | None = None,
        planner: Planner | None = None,
        reviewer: Reviewer | None = None,
        state_manager: StateManager | None = None,
    ) -> None:
        """Wire dependencies. Defaults construct real collaborators."""
        self.config = config
        self.git = git or GitManager(config.repository_root)
        self.planner = planner or Planner(config)
        self.reviewer = reviewer or Reviewer(config)
        self.state_manager = state_manager or StateManager(config.state_file)
        self._context: str | None = None

    @property
    def context(self) -> str:
        """Lazy-loaded project context documents."""
        if self._context is None:
            self._context = read_project_context(self.config)
        return self._context

    def run(self) -> int:
        """Run the queued tasks. Returns a process exit code."""
        start = time.monotonic()
        state = self.state_manager.load()
        run_dir: Path | None = (
            Path(state.run_dir) if state.run_dir else None
        )

        try:
            self.git.verify_agent_branch()
            if state.current_stage in {"queued", "approved"} or (
                state.task_id is None
            ):
                self.git.require_clean_worktree()

            tasks = load_tasks(self.config.tasks_file)
            return self._process_tasks(tasks, state, start)
        except (GitError, CursorNotFoundError, FileNotFoundError, ValueError) as exc:
            self._fail(state, run_dir, exc)
            print(f"Error: {exc}")
            return 1
        except Exception as exc:  # noqa: BLE001 - top-level safety net
            path = _save_traceback(run_dir, exc)
            self._fail(state, run_dir, exc)
            message = f"Unexpected error: {exc}"
            if path is not None:
                message += f" (details saved to {path})"
            print(message)
            return 1

    def _fail(
        self,
        state: AutomationState,
        run_dir: Path | None,
        exc: BaseException,
    ) -> None:
        state.current_stage = "failed"
        state.last_error = str(exc)
        if run_dir is not None:
            state.run_dir = str(run_dir)
        self.state_manager.save(state)

    def _process_tasks(
        self,
        tasks: list[TaskDefinition],
        state: AutomationState,
        start: float,
    ) -> int:
        completed = set(state.completed_tasks)
        approved_count = 0

        for task in tasks:
            if task.id in completed:
                continue

            if _elapsed_hours(start) >= self.config.max_runtime_hours:
                print(
                    f"Stopping: {self.config.max_runtime_hours} hour "
                    "limit reached."
                )
                break

            # Resume mid-task when state points at this task.
            if state.task_id and state.task_id != task.id:
                if state.current_stage not in {
                    "approved",
                    "queued",
                    "failed",
                    "human_review",
                }:
                    print(
                        f"State is mid-task {state.task_id}; "
                        "resolve or reset state.json before continuing."
                    )
                    return 1
                continue

            result = self._process_one_task(task, state, start)
            if result == "approved":
                approved_count += 1
                completed.add(task.id)
                state.completed_tasks = sorted(completed)
                state.task_id = None
                state.current_stage = "queued"
                state.attempt_number = 0
                state.repair_instructions = []
                state.run_dir = None
                state.last_successful_stage = "approved"
                state.last_error = None
                self.state_manager.save(state)
                continue
            if result == "human_review":
                print(f"Stopped cleanly for human review: {task.id}")
                return 0
            if result == "failed":
                return 1
            if result == "time_limit":
                break

        print(
            f"\nAutomation finished. "
            f"{approved_count} task(s) approved and committed."
        )
        print("Nothing was pushed or merged.")
        return 0

    def _process_one_task(
        self,
        task: TaskDefinition,
        state: AutomationState,
        start: float,
    ) -> str:
        resume_stage = state.current_stage if state.task_id == task.id else "queued"
        if resume_stage in {"failed", "human_review"}:
            print(
                f"Task {task.id} previously ended in {resume_stage}. "
                "Clear or update state.json to retry."
            )
            return resume_stage

        if state.task_id != task.id or state.run_dir is None:
            run_dir = make_run_directory(self.config.runs_dir, task.id)
            state.task_id = task.id
            state.started_at = _utc_now_iso()
            state.run_dir = str(run_dir)
            state.attempt_number = 0
            state.repair_instructions = []
            state.current_stage = "queued"
            state.last_error = None
            self.state_manager.save(state)
        else:
            run_dir = Path(state.run_dir)

        plan: ApprovedPlan | None = None
        plan_path = run_dir / "plan.json"
        if plan_path.exists() and resume_stage not in {"queued", "planning"}:
            plan = ApprovedPlan(**json.loads(plan_path.read_text(encoding="utf-8")))

        # --- PLAN ---
        if resume_stage in {"queued", "planning"} or plan is None:
            print(f"[PLAN] {task.id}: {task.title}")
            state.current_stage = "planning"
            self.state_manager.save(state)

            plan = self.planner.plan(task, self.context)
            save_plan(plan, plan_path)

            if plan.decision != "approve":
                state.current_stage = "human_review"
                state.last_error = plan.implementation_brief
                self.state_manager.save(state)
                print(f"[PLAN] human_review required for {task.id}")
                return "human_review"

            state.last_successful_stage = "planning"
            self.state_manager.save(state)

        assert plan is not None

        attempt = state.attempt_number
        repair_instructions = list(state.repair_instructions)
        last_test_output: str | None = None
        last_changed_files: list[str] | None = None

        while attempt <= self.config.max_repair_attempts:
            if _elapsed_hours(start) >= self.config.max_runtime_hours:
                print(
                    f"Stopping: {self.config.max_runtime_hours} hour "
                    "limit reached."
                )
                return "time_limit"

            stage_label = "repairing" if repair_instructions else "implementing"
            print(
                f"[CURSOR] {task.id} attempt {attempt + 1} "
                f"({stage_label})"
            )
            state.current_stage = stage_label  # type: ignore[assignment]
            state.attempt_number = attempt
            state.repair_instructions = repair_instructions
            self.state_manager.save(state)

            prompt = build_cursor_prompt(
                plan,
                repair_instructions or None,
                test_output=last_test_output,
                changed_files=last_changed_files,
            )
            cursor_result = invoke_cursor(
                prompt=prompt,
                run_dir=run_dir,
                attempt=attempt,
                config=self.config,
            )
            if cursor_result.timed_out:
                state.current_stage = "failed"
                state.last_error = "Cursor timed out"
                self.state_manager.save(state)
                print("[CURSOR] timed out")
                return "failed"
            if cursor_result.returncode != 0:
                # Allow repair path via review rather than hard-failing always;
                # still record the failure for evidence.
                print(
                    f"[CURSOR] exited with code {cursor_result.returncode}; "
                    "continuing to guardrails/tests/review"
                )

            state.last_successful_stage = stage_label
            self.state_manager.save(state)

            # --- GUARDRAILS ---
            print("[GUARDRAILS]")
            changed = self.git.list_changed_files()
            guardrail = validate_changed_files(
                changed,
                plan.allowed_areas,
                self.config,
            )
            (run_dir / f"guardrails_{attempt}.json").write_text(
                json.dumps(guardrail.to_dict(), indent=2),
                encoding="utf-8",
            )
            last_changed_files = list(guardrail.changed_files)
            if not guardrail.ok:
                state.current_stage = "human_review"
                state.last_error = "; ".join(guardrail.violations)
                self.state_manager.save(state)
                print("[GUARDRAILS] human_review required:")
                for item in guardrail.violations:
                    print(f"  - {item}")
                return "human_review"

            # --- TESTS ---
            print("[TESTS]")
            state.current_stage = "testing"
            self.state_manager.save(state)
            tests = run_tests(
                run_dir=run_dir,
                config=self.config,
                focused_tests=plan.focused_tests,
            )
            (run_dir / f"tests_{attempt}.json").write_text(
                json.dumps(
                    {
                        "passed": tests.passed,
                        "returncode": tests.returncode,
                        "timed_out": tests.timed_out,
                        "focused_passed": tests.focused_passed,
                        "log_file": tests.log_file,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            last_test_output = (
                f"stdout:\n{tests.stdout[-8000:]}\n\n"
                f"stderr:\n{tests.stderr[-4000:]}"
            )
            state.last_successful_stage = "testing"
            self.state_manager.save(state)

            # --- REVIEW ---
            print("[REVIEW]")
            state.current_stage = "reviewing"
            self.state_manager.save(state)
            diff = self.git.collect_diff()
            review = self.reviewer.review(
                plan=plan,
                tests=tests,
                guardrails=guardrail,
                diff=diff,
                context=self.context,
            )
            save_review(review, run_dir / f"review_{attempt}.json")

            if review.decision == "approve":
                print("[COMMIT]")
                self.git.commit_approved_task(task.id, plan.title)
                state.current_stage = "approved"
                state.last_successful_stage = "approved"
                state.last_error = None
                self.state_manager.save(state)
                print(f"[COMMIT] approved and committed: {task.id}")
                return "approved"

            if review.decision == "human_review":
                state.current_stage = "human_review"
                state.last_error = review.summary
                self.state_manager.save(state)
                print(f"[REVIEW] human_review: {review.summary}")
                return "human_review"

            # repair
            repair_instructions = list(review.repair_instructions)
            state.repair_instructions = repair_instructions
            state.current_stage = "repairing"
            self.state_manager.save(state)
            print(f"[REVIEW] repair requested: {review.summary}")

            if attempt >= self.config.max_repair_attempts:
                state.current_stage = "human_review"
                state.last_error = "Repair limit reached"
                self.state_manager.save(state)
                print(f"[REVIEW] repair limit reached for {task.id}")
                return "human_review"

            attempt += 1
            state.attempt_number = attempt
            self.state_manager.save(state)

        state.current_stage = "human_review"
        state.last_error = "Repair limit reached"
        self.state_manager.save(state)
        return "human_review"


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for automation_v2."""
    _ = argv
    try:
        config = load_config()
    except ValueError as exc:
        print(f"Configuration error: {exc}")
        return 1

    config.runs_dir.mkdir(parents=True, exist_ok=True)
    orchestrator = Orchestrator(config)
    return orchestrator.run()


if __name__ == "__main__":
    sys.exit(main())
