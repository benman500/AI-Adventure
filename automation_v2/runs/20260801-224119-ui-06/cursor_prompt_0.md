
Read AGENTS.md, PROJECT_CONTEXT.md, and CURRENT_MILESTONE.md first.

Implement exactly this approved task:

TITLE:
Polish player-facing visual consistency

IMPLEMENTATION BRIEF:
Inspect the current player-facing templates, stylesheets, and presentation tests to identify concrete inconsistencies in typography, spacing, hierarchy, borders, color usage, contrast, and keyboard-focus treatment. Make a restrained polish pass in at least one existing template or stylesheet within the allowed implementation areas. Reuse the current server-rendered structure and existing style conventions; consolidate or adjust existing CSS where practical rather than introducing a new styling system. Preserve all text, forms, routes, controls, responsive behavior, and gameplay behavior. Update or add narrowly scoped presentation tests only where needed to verify stable structural or accessibility-facing expectations. Record changed files, tests, results, and remaining risks in automation/AGENT_REPORT.md.

ALLOWED AREAS:
[
  "src/ai_adventure/presentation/templates",
  "src/ai_adventure/presentation/static",
  "tests",
  "automation/AGENT_REPORT.md"
]

ACCEPTANCE CRITERIA:
[
  "Location titles, section headings, body text, helper text, and labels have a clear and consistent visual hierarchy.",
  "Paragraphs, cards, sections, form controls, and action groups use consistent spacing across existing player-facing screens.",
  "The existing dark cultivation theme uses restrained parchment, gold, and muted natural accents without introducing a replacement theme.",
  "Story, character information, actions, cards, and helper content remain visually distinguishable without excessive borders.",
  "No existing text, form behavior, routes, navigation, responsive behavior, or gameplay behavior is removed or changed.",
  "Text contrast and visible keyboard-focus states remain adequate for interactive controls.",
  "At least one allowed template or stylesheet implementation file receives a meaningful presentation improvement; report-only or test-only changes are insufficient.",
  "Focused presentation tests and the full test suite pass."
]

FORBIDDEN CHANGES:
[
  "Gameplay rules, progression, engine logic, services, persistence, catalogs, or authored content",
  "Database schema changes or migrations",
  "New dependencies, JavaScript frameworks, architecture, or styling systems",
  "Changes to routes, request handling, form semantics, submitted values, or control behavior",
  "Removal or rewriting of existing player-facing text",
  "Conversion away from the current server-rendered architecture",
  "Weakening, deleting, or skipping tests",
  "Edits outside the listed allowed areas",
  "Large unrelated refactors"
]

STOP CONDITIONS:
[
  "A desired visual change requires modifying gameplay, routes, persistence, form behavior, or application architecture.",
  "The existing templates or styles do not provide enough information to preserve current behavior safely.",
  "The task would require a new dependency, framework, migration, or product-level visual decision not established by the existing theme.",
  "Required work cannot be completed within the allowed areas.",
  "Focused or full-suite failures reveal behavior changes or unrelated defects that cannot be resolved within this bounded presentation task.",
  "More than 25 files would need to be changed."
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
