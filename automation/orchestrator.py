from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from openai import OpenAI


ROOT = Path(__file__).resolve().parents[1]
AUTOMATION_DIR = ROOT / "automation"
TASK_FILE = AUTOMATION_DIR / "tasks.json"
RUNS_DIR = AUTOMATION_DIR / "runs"

PROJECT_CONTEXT = ROOT / "PROJECT_CONTEXT.md"
CURRENT_MILESTONE = ROOT / "CURRENT_MILESTONE.md"
AGENT_RULES = ROOT / "AGENTS.md"

MODEL = os.getenv("OPENAI_AUTOMATION_MODEL", "gpt-5.6")
MAX_HOURS = float(os.getenv("AUTOMATION_MAX_HOURS", "4"))
MAX_REPAIR_ATTEMPTS = int(os.getenv("AUTOMATION_MAX_REPAIRS", "2"))
MAX_CHANGED_FILES = int(os.getenv("AUTOMATION_MAX_CHANGED_FILES", "25"))

FORBIDDEN_PATH_PREFIXES = (
    ".env",
    "alembic/versions/",
    ".github/workflows/",
)

client = OpenAI()


def run_command(
    args: list[str],
    *,
    timeout: int | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a command using UTF-8 and safely replace invalid output characters."""
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"

    return subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
        shell=False,
        env=environment,
    )


def require_clean_worktree() -> None:
    result = run_command(["git", "status", "--porcelain"])
    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    if result.stdout.strip():
        raise RuntimeError(
            "Git has uncommitted changes. Commit or stash them before starting."
        )


def current_branch() -> str:
    result = run_command(["git", "branch", "--show-current"])
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


def verify_agent_branch() -> None:
    branch = current_branch()
    if not branch.startswith("agent/"):
        raise RuntimeError(
            f"Automation must run on an agent branch. Current branch: {branch}"
        )


def read_required_context() -> str:
    files = [AGENT_RULES, PROJECT_CONTEXT, CURRENT_MILESTONE]
    sections: list[str] = []

    for file_path in files:
        if not file_path.exists():
            raise FileNotFoundError(f"Required file is missing: {file_path}")

        sections.append(
            f"\n\n===== {file_path.name} =====\n"
            + file_path.read_text(encoding="utf-8")
        )

    return "".join(sections)


def ask_openai(instructions: str, input_text: str) -> str:
    response = client.responses.create(
        model=MODEL,
        instructions=instructions,
        input=input_text,
    )
    return response.output_text


def clean_json_text(raw: str) -> str:
    value = raw.strip()

    if value.startswith("```"):
        lines = value.splitlines()
        lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        value = "\n".join(lines)

    if value.lstrip().startswith("json"):
        value = value.lstrip()[4:].lstrip()

    return value


def plan_task(task: dict[str, Any], context: str) -> dict[str, Any]:
    instructions = """
You are the supervising planner for an existing cultivation RPG.

Review the proposed queued task against the locked project context.

Return JSON only with this exact shape:

{
  "decision": "approve" | "human_review",
  "title": "short task title",
  "implementation_brief": "precise bounded instructions for Cursor",
  "allowed_areas": ["path prefixes"],
  "acceptance_criteria": ["criterion"],
  "forbidden_changes": ["change"],
  "focused_tests": ["test command"],
  "stop_conditions": ["condition"]
}

Rules:

- Do not invent a larger task.
- Do not add architecture.
- Do not add new systems.
- Keep the work inside the current milestone.
- Choose human_review if the task requires migrations, dependencies,
  game-rule changes, or unclear product decisions.
"""

    raw = ask_openai(
        instructions,
        context + "\n\nQUEUED TASK:\n" + json.dumps(task, indent=2),
    )
    return json.loads(clean_json_text(raw))


def build_cursor_prompt(
    plan: dict[str, Any],
    repair_instructions: list[str] | None = None,
) -> str:
    prompt = f"""
Read AGENTS.md, PROJECT_CONTEXT.md, and CURRENT_MILESTONE.md first.

Implement exactly this approved task:

TITLE:
{plan["title"]}

IMPLEMENTATION BRIEF:
{plan["implementation_brief"]}

ALLOWED AREAS:
{json.dumps(plan["allowed_areas"], indent=2)}

ACCEPTANCE CRITERIA:
{json.dumps(plan["acceptance_criteria"], indent=2)}

FORBIDDEN CHANGES:
{json.dumps(plan["forbidden_changes"], indent=2)}

STOP CONDITIONS:
{json.dumps(plan["stop_conditions"], indent=2)}

Instructions:

1. Inspect the relevant implementation and tests.
2. Stay within the approved scope.
3. Make the smallest coherent implementation.
4. Run focused tests while working.
5. Run the full test suite before finishing.
6. Do not commit, push, merge, migrate, or install dependencies.
7. If blocked or ambiguous, stop and explain in automation/AGENT_REPORT.md.
8. Write automation/AGENT_REPORT.md when complete.
"""

    if repair_instructions:
        prompt += "\n\nREVIEW REPAIRS REQUIRED:\n"
        prompt += "\n".join(f"- {item}" for item in repair_instructions)
        prompt += "\nRepair only these findings. Do not broaden the task."

    return prompt


def invoke_cursor(prompt_file: Path, log_file: Path) -> None:
    command = [
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(AUTOMATION_DIR / "run_cursor.ps1"),
        str(prompt_file),
    ]

    result = run_command(command, timeout=60 * 90)

    log_file.write_text(
        "STDOUT\n"
        "======\n"
        + result.stdout
        + "\n\nSTDERR\n"
        "======\n"
        + result.stderr,
        encoding="utf-8",
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Cursor exited with code {result.returncode}. "
            f"Read {log_file}."
        )


def changed_files() -> list[str]:
    result = run_command(["git", "diff", "--name-only"])
    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    return [
        line.strip().replace("\\", "/")
        for line in result.stdout.splitlines()
        if line.strip()
    ]


def validate_changed_files(
    files: list[str],
    allowed_areas: list[str],
) -> list[str]:
    violations: list[str] = []

    normalized_allowed = [
        value.replace("\\", "/").rstrip("/")
        for value in allowed_areas
    ]

    for file_name in files:
        if any(
            file_name == prefix.rstrip("/")
            or file_name.startswith(prefix)
            for prefix in FORBIDDEN_PATH_PREFIXES
        ):
            violations.append(f"Forbidden path changed: {file_name}")
            continue

        allowed = any(
            file_name == area or file_name.startswith(area + "/")
            for area in normalized_allowed
        )

        # The agent report is always permitted.
        if file_name == "automation/AGENT_REPORT.md":
            allowed = True

        if not allowed:
            violations.append(f"File outside allowed areas: {file_name}")

    if len(files) > MAX_CHANGED_FILES:
        violations.append(
            f"{len(files)} files changed; maximum is {MAX_CHANGED_FILES}."
        )

    return violations


def run_tests(run_dir: Path) -> dict[str, Any]:
    result = run_command(
        [sys.executable, "-m", "pytest", "-q"],
        timeout=60 * 45,
    )

    test_log = run_dir / "pytest.txt"
    test_log.write_text(
        result.stdout + "\n\n" + result.stderr,
        encoding="utf-8",
    )

    return {
        "returncode": result.returncode,
        "stdout_tail": result.stdout[-15000:],
        "stderr_tail": result.stderr[-8000:],
        "log_file": str(test_log),
    }


def collect_diff() -> dict[str, Any]:
    stat = run_command(["git", "diff", "--stat"])
    diff = run_command(
        ["git", "diff", "--", ".", ":(exclude)automation/runs"]
    )

    stat_output = stat.stdout or ""
    diff_output = diff.stdout or ""

    return {
        "stat": stat_output,
        "diff_tail": diff_output[-60000:],
        "changed_files": changed_files(),
    }


def review_task(
    plan: dict[str, Any],
    evidence: dict[str, Any],
    context: str,
) -> dict[str, Any]:
    instructions = """
You are the supervising reviewer for an existing cultivation RPG.

Judge the implementation only against the approved task, locked architecture,
test results, changed files, and diff.

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
- no tests were weakened.

Choose human_review for:

- migrations,
- dependency changes,
- destructive changes,
- new architecture,
- ambiguous design decisions,
- suspiciously broad refactors,
- changes outside allowed areas.
"""

    payload = {
        "plan": plan,
        "evidence": evidence,
        "locked_context": context,
    }

    raw = ask_openai(instructions, json.dumps(payload, indent=2))
    return json.loads(clean_json_text(raw))


def commit_approved_task(task_id: str, title: str) -> None:
    add_result = run_command(["git", "add", "."])
    if add_result.returncode != 0:
        raise RuntimeError(add_result.stderr)

    commit_result = run_command(
        ["git", "commit", "-m", f"agent: {task_id} {title}"]
    )
    if commit_result.returncode != 0:
        raise RuntimeError(commit_result.stderr)


def make_run_directory(task_id: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = RUNS_DIR / f"{timestamp}-{task_id}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def main() -> None:
    require_clean_worktree()
    verify_agent_branch()

    context = read_required_context()

    if not TASK_FILE.exists():
        raise FileNotFoundError(f"Task queue not found: {TASK_FILE}")

    tasks = json.loads(TASK_FILE.read_text(encoding="utf-8"))

    if not isinstance(tasks, list) or not tasks:
        raise ValueError("automation/tasks.json must contain a non-empty list.")

    start_time = time.monotonic()
    approved_count = 0

    for task in tasks:
        elapsed_hours = (time.monotonic() - start_time) / 3600

        if elapsed_hours >= MAX_HOURS:
            print(f"Stopping: {MAX_HOURS} hour limit reached.")
            break

        task_id = str(task["id"])
        run_dir = make_run_directory(task_id)

        print(f"\nPlanning {task_id}: {task['title']}")

        plan = plan_task(task, context)
        (run_dir / "plan.json").write_text(
            json.dumps(plan, indent=2),
            encoding="utf-8",
        )

        if plan["decision"] != "approve":
            print(f"Stopped for human review before {task_id}.")
            return

        repair_instructions: list[str] | None = None

        for attempt in range(MAX_REPAIR_ATTEMPTS + 1):
            prompt = build_cursor_prompt(plan, repair_instructions)
            prompt_file = run_dir / f"cursor_prompt_{attempt}.md"
            prompt_file.write_text(prompt, encoding="utf-8")

            print(f"Running Cursor for {task_id}, attempt {attempt + 1}")
            invoke_cursor(
                prompt_file,
                run_dir / f"cursor_output_{attempt}.txt",
            )

            files = changed_files()
            violations = validate_changed_files(
                files,
                plan["allowed_areas"],
            )

            tests = run_tests(run_dir)
            diff = collect_diff()

            evidence = {
                "tests": tests,
                "diff": diff,
                "scope_violations": violations,
            }

            (run_dir / f"evidence_{attempt}.json").write_text(
                json.dumps(evidence, indent=2),
                encoding="utf-8",
            )

            if violations:
                print("Stopped because scope guardrails were violated:")
                for violation in violations:
                    print(f"- {violation}")
                return

            review = review_task(plan, evidence, context)
            (run_dir / f"review_{attempt}.json").write_text(
                json.dumps(review, indent=2),
                encoding="utf-8",
            )

            if review["decision"] == "approve":
                commit_approved_task(task_id, plan["title"])
                approved_count += 1
                print(f"Approved and committed: {task_id}")
                break

            if review["decision"] == "human_review":
                print(f"Stopped for human review during {task_id}.")
                print(review["summary"])
                return

            repair_instructions = review.get(
                "repair_instructions",
                [],
            )

            if attempt >= MAX_REPAIR_ATTEMPTS:
                print(f"Stopped: repair limit reached for {task_id}.")
                return

        # Ensure the repository is clean after the approved commit.
        require_clean_worktree()

    print(
        f"\nAutomation finished. "
        f"{approved_count} task(s) approved and committed."
    )
    print("Nothing was pushed or merged.")


if __name__ == "__main__":
    main()
