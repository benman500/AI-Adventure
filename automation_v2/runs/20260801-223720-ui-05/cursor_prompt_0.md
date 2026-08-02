
Read AGENTS.md, PROJECT_CONTEXT.md, and CURRENT_MILESTONE.md first.

Implement exactly this approved task:

TITLE:
Improve gameplay action hierarchy

IMPLEMENTATION BRIEF:
Inspect the existing gameplay templates, stylesheets, and presentation tests to identify where actions currently use indistinguishable styling or lack clear interaction states. Establish a consistent visual hierarchy using the existing server-rendered templates and CSS: emphasize primary decisions, visually quiet secondary and utility controls, and improve grouping or spacing where needed without adding, removing, renaming, or reordering actions. Preserve every existing route, form method, field name, submitted value, and gameplay behavior. Add or refine hover, active, disabled, and keyboard-focus-visible states; ensure controls remain readable and usable at mobile widths; and place any motion behind reduced-motion preference handling. Make meaningful changes to at least one implementation file under the allowed template or static paths, update focused presentation tests where appropriate, run the focused tests and full suite, and record files, results, and remaining risks in automation/AGENT_REPORT.md.

ALLOWED AREAS:
[
  "src/ai_adventure/presentation/templates",
  "src/ai_adventure/presentation/static",
  "tests",
  "automation/AGENT_REPORT.md"
]

ACCEPTANCE CRITERIA:
[
  "Existing gameplay views consistently distinguish primary actions from secondary and utility actions through styling, grouping, or emphasis.",
  "Action controls no longer present as an undifferentiated wall of identical rectangles.",
  "Interactive controls have clear hover, active, disabled, and keyboard-focus-visible states.",
  "Existing action names, order, routes, form methods, field names, submitted values, and gameplay behavior remain unchanged.",
  "Controls remain accessible, readable, and usable at mobile widths without clipping or harmful overflow.",
  "Any transitions respect reduced-motion preferences.",
  "Focused presentation tests and the full test suite pass."
]

FORBIDDEN CHANGES:
[
  "Gameplay rules, progression, engine behavior, or action availability",
  "Adding, removing, renaming, or reordering gameplay actions",
  "Changing routes, form methods, field names, or submitted values",
  "Database models, migrations, catalogs, or save formats",
  "New dependencies, JavaScript frameworks, systems, or architectural layers",
  "Conversion away from the existing server-rendered presentation architecture",
  "Weakening, deleting, or skipping existing tests",
  "Changes outside the listed allowed areas"
]

STOP CONDITIONS:
[
  "The desired primary versus secondary classification is ambiguous and cannot be inferred safely from current templates, styling, tests, or established usage.",
  "A required improvement would change action semantics, order, availability, submitted data, or gameplay rules.",
  "The work requires a migration, new dependency, architecture change, or edits outside the allowed areas.",
  "Focused or full-suite failures reveal unrelated defects that cannot be resolved within the allowed scope.",
  "The bounded task would require changes to more than 25 files."
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
