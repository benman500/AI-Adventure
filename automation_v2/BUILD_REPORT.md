# automation_v2 Build Report

## Task completed

Built Version 2 of the local automation framework under `automation_v2/`.

This was an automation-framework-only change. No game code, templates, CSS, gameplay, database, migrations, `pyproject.toml`, or existing application tests were modified. `automation/orchestrator.py` was left intact.

Confirmed before editing:

- Branch: `agent/orchestrator-v2`
- Worktree had only the untracked `automation_v2/` scaffolding
- Existing PoC inspected at `automation/orchestrator.py`

## What was built

| Module | Role |
|--------|------|
| `process_runner.py` | Sole subprocess wrapper (`shell=False`, UTF-8, `errors="replace"`, timeouts) |
| `models.py` | Typed dataclasses for command/task/plan/test/guardrail/review/state |
| `config.py` | Env-driven config with startup validation; no secrets |
| `state_manager.py` | Atomic `state.json` persistence for crash-safe resume |
| `git_manager.py` | Agent-branch checks, clean worktree, diffs, commit-only (no push/merge/reset) |
| `guardrails.py` | Allowed-area + forbidden-path validation → `human_review` (never discards) |
| `cursor_runner.py` | Headless Cursor CLI via `agent`/`cursor-agent` (no PowerShell, no `shell=True`) |
| `test_runner.py` | Focused tests (optional) + always `python -m pytest -q` |
| `planner.py` | OpenAI Responses API planner, strict JSON, retries, no task widening |
| `reviewer.py` | OpenAI Responses API reviewer; never approves failed tests/scope violations |
| `main.py` | Stage coordinator with progress tags, repair limits, time limits, error capture |
| `tasks.json` | Single queued task `ui-01` (story-first play layout) |
| `state.json` | Idle/queued initial state |
| `runs/` | Per-run artifact directory |

## Files changed / added

### Framework

- `automation_v2/__init__.py`
- `automation_v2/main.py`
- `automation_v2/config.py`
- `automation_v2/process_runner.py`
- `automation_v2/git_manager.py`
- `automation_v2/cursor_runner.py`
- `automation_v2/test_runner.py`
- `automation_v2/planner.py`
- `automation_v2/reviewer.py`
- `automation_v2/guardrails.py`
- `automation_v2/state_manager.py`
- `automation_v2/models.py`
- `automation_v2/tasks.json`
- `automation_v2/state.json`
- `automation_v2/runs/.gitkeep`
- `automation_v2/BUILD_REPORT.md`

### Tests

- `tests/automation_v2/__init__.py`
- `tests/automation_v2/test_process_runner.py`
- `tests/automation_v2/test_guardrails.py`
- `tests/automation_v2/test_state_manager.py`
- `tests/automation_v2/test_planner_reviewer.py`
- `tests/automation_v2/test_cursor_runner.py`
- `tests/automation_v2/test_config.py`

## Tests run

```text
python -m pytest -q tests/automation_v2/
# 28 passed

python -m pytest -q
# 276 passed, 10 warnings
```

Covered:

- UTF-8 and invalid-byte subprocess output handling
- `stdout=None` coercion
- Timeout handling
- Allowed / forbidden path validation
- Changed-file limits
- State save and resume (atomic write)
- Malformed planner/reviewer JSON retries (mocked OpenAI)
- Cursor invocation (mocked; no real agent)
- Config validation

No real Cursor agent run and no real OpenAI API credits were used during tests.

## Remaining concerns / human review

1. **Cursor CLI argv** — Print-mode args default to `-p,--output-format,text` and are configurable via `AUTOMATION_CURSOR_PRINT_ARGS` / `config.py`. Confirm against your installed `agent --help` before a live run; CLI syntax varies by version.
2. **Long prompts on Windows** — The full prompt is passed as a trailing argv string (and also written to a UTF-8 file under `runs/`). Very large prompts could hit OS command-line length limits; if that happens, switch to a file/stdin-based invocation via config without changing architecture.
3. **OpenAI package** — The framework imports the already-installed `openai` package at planner/reviewer runtime. It is not declared in `pyproject.toml` (per instructions: do not modify dependencies). Ensure it remains available in the environment used for live automation.
4. **Live run not executed** — Framework build/test only. Do not start an autonomous game-development run until you intentionally invoke `python -m automation_v2.main` on a clean `agent/*` branch with `OPENAI_API_KEY` set.
5. **Resume semantics** — Mid-task resume relies on `state.json` plus `runs/*/plan.json`. If a run directory is deleted while state still points at it, clear or reset `state.json` before retrying.
6. **Guardrail policy** — Violations never discard changes; the orchestrator stops for `human_review` and leaves the worktree for manual inspection.

## Assumptions

- Repository root is the parent of `automation_v2/`.
- Live automation must run on a branch named `agent/...`.
- `OPENAI_API_KEY` is provided only via the environment for live planner/reviewer calls.
- Model name comes from `OPENAI_AUTOMATION_MODEL` (default `gpt-5.6`).
