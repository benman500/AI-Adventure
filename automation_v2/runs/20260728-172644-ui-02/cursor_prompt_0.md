
Read AGENTS.md, PROJECT_CONTEXT.md, and CURRENT_MILESTONE.md first.

Implement exactly this approved task:

TITLE:
Modernize character creation

IMPLEMENTATION BRIEF:
Read the required project documents, then inspect the current character-creation templates, shared/static CSS, form markup, validation rendering, and relevant presentation tests. Identify concrete presentation deficiencies and redesign the existing server-rendered character-creation page within the allowed areas. Make meaningful changes to at least one character-creation template or stylesheet: visually group each question with its answers, render background radio choices as fully clickable cards using labels, place personality answers directly beneath their associated questions, and provide clear selected, hover, and keyboard-focus states. Improve spacing, typography, action hierarchy, validation clarity, and responsive behavior at desktop and mobile widths. Preserve the existing form action, HTTP method, routes, field names, submitted values, validation behavior, question-to-answer mapping, and gameplay behavior. Use the existing frontend approach without adding dependencies, frameworks, systems, or mechanics. Add or update focused presentation tests where appropriate, run focused tests and the complete pytest suite, and update automation/AGENT_REPORT.md with the required completion details.

ALLOWED AREAS:
[
  "src/ai_adventure/presentation/templates",
  "src/ai_adventure/presentation/static",
  "tests",
  "automation/AGENT_REPORT.md"
]

ACCEPTANCE CRITERIA:
[
  "Each character-creation question is visually separated and easy to understand.",
  "Background choices are fully clickable cards while retaining the existing input names and values.",
  "Each personality answer is rendered directly beneath the question it answers, with the existing question-to-answer mapping preserved.",
  "Selected, hovered, and keyboard-focused choices have clear and accessible visual states.",
  "Existing form field names, submitted values, form action, routes, and validation behavior remain unchanged.",
  "The page remains usable without horizontal overflow or obscured controls at desktop and mobile widths.",
  "At least one allowed character-creation template or stylesheet receives a meaningful implementation change; report-only or test-only changes are insufficient.",
  "Focused presentation tests and the full test suite pass."
]

FORBIDDEN CHANGES:
[
  "Gameplay, progression, engine, service, validation-rule, or persistence changes",
  "Database or migration changes",
  "Route, form action, HTTP method, field name, or submitted-value changes",
  "New catalogs, systems, architecture, dependencies, or JavaScript frameworks",
  "Conversion away from the existing server-rendered presentation architecture",
  "Changes outside the allowed areas",
  "Weakening, deleting, or skipping existing tests",
  "Large unrelated refactors or changes to more than 25 files"
]

STOP CONDITIONS:
[
  "The current form contract or question-to-answer mapping cannot be determined from the existing templates, handlers, and tests.",
  "Meeting the goal would require changing routes, submitted values, validation behavior, gameplay rules, services, persistence, or files outside the allowed areas.",
  "The work would require a migration, new dependency, architectural change, new framework, or product decision not specified by the task.",
  "Relevant existing tests reveal conflicting requirements that cannot be resolved without changing behavior.",
  "The implementation would exceed 25 changed files or require a large unrelated refactor."
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
