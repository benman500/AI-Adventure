
Read AGENTS.md, PROJECT_CONTEXT.md, and CURRENT_MILESTONE.md first.

Implement exactly this approved task:

TITLE:
Responsive and accessibility audit

IMPLEMENTATION BRIEF:
Read the required project documentation, then inspect the current player-facing templates, CSS, existing client-side behavior, and presentation tests. Audit representative character creation and living-loop pages at narrow mobile, tablet, and desktop widths for overflow, overlap, alignment, keyboard navigation, focus visibility, collapsible-section semantics, clickable-card keyboard access, and reduced-motion behavior. Identify concrete presentation deficiencies and correct them by making meaningful changes to at least one allowed template or static implementation file. Use existing server-rendered patterns and native HTML/CSS wherever possible; preserve routes, form field names, submitted values, service boundaries, and gameplay behavior. Add or adjust focused presentation tests for stable accessibility and markup requirements where practical. Do not treat updates to tests or automation/AGENT_REPORT.md alone as implementation. Record files changed, tests run, results, and remaining risks in automation/AGENT_REPORT.md.

ALLOWED AREAS:
[
  "src/ai_adventure/presentation/templates",
  "src/ai_adventure/presentation/static",
  "tests",
  "automation/AGENT_REPORT.md"
]

ACCEPTANCE CRITERIA:
[
  "Player-facing pages remain usable at narrow mobile, tablet, and desktop widths.",
  "Important text, cards, controls, and panels do not overlap or cause unintended horizontal scrolling.",
  "Interactive elements display clearly visible keyboard-focus states.",
  "Clickable cards are keyboard accessible where applicable without changing their submitted values or behavior.",
  "Collapsed and expanded sections use understandable labels, states, and accessible semantics.",
  "Reduced-motion preferences disable or minimize nonessential transitions and animations.",
  "Existing routes, field names, submitted values, service boundaries, and gameplay behavior remain unchanged.",
  "At least one allowed template or static implementation file receives a meaningful presentation correction.",
  "Focused presentation tests and the full test suite pass."
]

FORBIDDEN CHANGES:
[
  "Gameplay, progression, engine-rule, catalog, or persistence changes",
  "Database migrations or save-format changes",
  "New dependencies, frameworks, systems, or architectural layers",
  "Conversion away from the current server-rendered architecture",
  "Route, endpoint, form field name, or submitted-value changes",
  "Deployment, secret, environment, or production database changes",
  "Weakening, deleting, or skipping existing tests",
  "Report-only, test-only, or automation-only completion without an implementation change",
  "Large unrelated refactors or changes to more than 25 files"
]

STOP CONDITIONS:
[
  "A required correction cannot be completed within the allowed areas.",
  "A correction would require changing gameplay rules, backend service behavior, routes, field names, or submitted values.",
  "A correction would require a migration, new dependency, architecture change, or JavaScript framework.",
  "Expected accessible behavior is ambiguous and selecting an approach would require a product decision.",
  "The task would exceed 25 changed files or require a broad unrelated refactor.",
  "Focused or full-suite failures indicate behavior outside the presentation scope must change."
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
