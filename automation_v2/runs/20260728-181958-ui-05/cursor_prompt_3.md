
Read AGENTS.md, PROJECT_CONTEXT.md, and CURRENT_MILESTONE.md first.

Implement exactly this approved task:

TITLE:
Improve gameplay action hierarchy

IMPLEMENTATION BRIEF:
Read the required project documentation, then inspect the current gameplay templates, stylesheets, and relevant presentation tests. Identify concrete locations where actions are rendered as visually identical controls or become crowded at mobile widths. Make meaningful changes to at least one template or stylesheet within the allowed areas to establish a consistent visual hierarchy for existing primary, secondary, and utility actions. Reuse the current server-rendered structure and styling conventions where practical. Add or refine hover, active, disabled, and visible keyboard-focus states; keep text and controls readable and usable at mobile widths; and ensure any transitions are disabled or minimized under prefers-reduced-motion. Preserve the exact action set and behavior: do not add, remove, rename, or reorder gameplay actions, and do not change routes, form methods, field names, submitted values, validation, or mechanics. Add or update focused presentation tests where the existing test approach supports stable assertions, then run focused tests and the complete suite. Update automation/AGENT_REPORT.md with the required completion details.

ALLOWED AREAS:
[
  "src/ai_adventure/presentation/templates",
  "src/ai_adventure/presentation/static",
  "tests",
  "automation/AGENT_REPORT.md"
]

ACCEPTANCE CRITERIA:
[
  "Primary actions are visually distinct from secondary and utility actions.",
  "Buttons and action controls no longer appear as an undifferentiated wall of identical rectangles.",
  "Hover, active, disabled, and keyboard-focus states are clear.",
  "Existing action names, routes, form methods, field names, submitted values, and action ordering remain unchanged.",
  "Controls remain accessible, readable, and usable at mobile widths.",
  "Any transitions respect the prefers-reduced-motion user preference.",
  "At least one allowed template or stylesheet receives a meaningful implementation change; report-only or test-only changes are insufficient.",
  "Focused presentation tests and the full test suite pass."
]

FORBIDDEN CHANGES:
[
  "Adding, removing, renaming, or behaviorally reordering gameplay actions",
  "Changing routes, HTTP methods, form field names, submitted values, validation, services, or game rules",
  "Adding JavaScript frameworks, dependencies, systems, catalogs, or architecture",
  "Database or migration changes",
  "Conversion away from the existing server-rendered presentation architecture",
  "Unrelated visual redesigns or refactors outside action hierarchy and control usability",
  "Weakening, deleting, or skipping existing tests"
]

STOP CONDITIONS:
[
  "A required hierarchy cannot be implemented without changing action behavior, order, routes, methods, names, or submitted values.",
  "Classifying an action as primary, secondary, or utility requires an unclear product or gameplay decision.",
  "The work would require a migration, new dependency, architectural change, new framework, or gameplay-rule change.",
  "The necessary implementation lies outside the allowed areas.",
  "Focused or full-suite failures indicate behavior changes that cannot be resolved within this bounded presentation task.",
  "Completing the task would require changes to more than 25 files."
]

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


REVIEW REPAIRS REQUIRED:
- Fix failing tests without weakening or deleting them.
- Re-run focused tests and the full suite.

ORIGINAL ACCEPTANCE CRITERIA:
- Primary actions are visually distinct from secondary and utility actions.
- Buttons and action controls no longer appear as an undifferentiated wall of identical rectangles.
- Hover, active, disabled, and keyboard-focus states are clear.
- Existing action names, routes, form methods, field names, submitted values, and action ordering remain unchanged.
- Controls remain accessible, readable, and usable at mobile widths.
- Any transitions respect the prefers-reduced-motion user preference.
- At least one allowed template or stylesheet receives a meaningful implementation change; report-only or test-only changes are insufficient.
- Focused presentation tests and the full test suite pass.

CHANGED FILES FROM PREVIOUS ATTEMPT:
- src/ai_adventure/presentation/static/css/main.css
- src/ai_adventure/presentation/templates/play_scene.html
- tests/test_action_hierarchy_ui.py

TEST OUTPUT FROM PREVIOUS ATTEMPT:
stdout:
........................................................................ [ 22%]
........................................................................ [ 45%]
........................................................................ [ 68%]
........................................................................ [ 91%]
............................                                             [100%]
============================== warnings summary ===============================
tests/test_alchemy_phase8.py: 1 warning
tests/test_alembic_migrations.py: 3 warnings
tests/test_event_engine_phase4a.py: 1 warning
tests/test_locations_phase5a.py: 1 warning
tests/test_npcs_phase9b.py: 1 warning
tests/test_sects_phase9d.py: 1 warning
tests/test_spiritual_roots_phase7.py: 1 warning
tests/test_techniques_phase6c.py: 1 warning
  C:\Users\benjamyn\Desktop\ai-projects\AI- Adventure\.venv\Lib\site-packages\alembic\config.py:612: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
316 passed, 10 warnings in 39.94s


stderr:
Focused tests failed.
ERROR: file or directory not found: Run



--- full suite ---


Repair the implementation rather than merely rewriting the report. Make meaningful changes to at least one allowed implementation file unless every acceptance criterion is already satisfied with specific criterion-by-criterion evidence.
The PowerShell/batch/shell/Python script ban and run-directory diagnostic-file limit above still apply during repair.