
Read AGENTS.md, PROJECT_CONTEXT.md, and CURRENT_MILESTONE.md first.

Implement exactly this approved task:

TITLE:
Modernize character creation

IMPLEMENTATION BRIEF:
Inspect the existing character-creation templates, styles, and presentation tests. Redesign only the server-rendered presentation: visually separate each question, place its personality answers immediately beneath it, and render background options as accessible fully clickable cards using the existing form controls. Add clear selected, hover, and keyboard-focus states, establish an obvious action hierarchy, and support desktop and mobile widths. Preserve the current form structure required by the backend, including all routes, methods, field names, submitted values, validation behavior, question-to-answer mappings, and gameplay behavior. Prefer semantic HTML and CSS; use only minimal existing-project JavaScript if the current selection behavior cannot be expressed with native controls and CSS. Add or update focused presentation tests without weakening existing assertions. Run focused tests and the complete suite, then update automation/AGENT_REPORT.md with changes, results, and risks.

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
  "Background choices are fully clickable cards backed by the existing form controls.",
  "Personality answers appear directly beneath and remain correctly associated with their existing questions.",
  "Selected, hovered, and keyboard-focused choices have clear visual states.",
  "Existing routes, HTTP methods, form field names, submitted values, validation, and gameplay behavior remain unchanged.",
  "Character creation remains usable at desktop and mobile widths.",
  "Controls remain keyboard accessible and retain semantic labels.",
  "Focused presentation tests and the full test suite pass.",
  "automation/AGENT_REPORT.md records files changed, tests run, results, remaining risks, and any review needs."
]

FORBIDDEN CHANGES:
[
  "Changing gameplay rules, character-creation mechanics, or progression.",
  "Changing routes, service logic, validation rules, field names, or submitted values.",
  "Changing database models, saves, migrations, catalogs, or authored gameplay content.",
  "Adding dependencies, frameworks, architecture, or new systems.",
  "Converting character creation away from the current server-rendered architecture.",
  "Editing files outside the allowed areas.",
  "Deleting, skipping, weakening, or rewriting tests merely to make them pass.",
  "Large unrelated refactors or more than 25 changed files."
]

STOP CONDITIONS:
[
  "The existing question-to-answer mapping or required submitted values cannot be determined from the implementation and tests.",
  "The redesign would require changes to routes, services, validation, gameplay rules, persistence, or files outside the allowed areas.",
  "The task would require a new dependency, framework, architecture, migration, or product decision.",
  "Existing behavior cannot be preserved while meeting the requested presentation criteria.",
  "More than 25 files would need to change.",
  "Focused or full-suite failures reveal issues that cannot be resolved within this UI-only scope."
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

Temporary files and test execution:

9. Do not create temporary PowerShell, batch, shell, Python, helper, or ad hoc
   test-runner scripts anywhere in the repository (for example .ps1, .bat,
   .cmd, .sh, or one-off .py runners).
10. Do not add project-root scripts (for example run_ui_tests.ps1) or expand
    allowed areas to include them. Guardrails must not be weakened.
11. Run approved test commands directly in the terminal
    (for example: python -m pytest -q). Never create a script to wrap tests.
12. Temporary diagnostic files may only be written inside the current
    automation_v2 run directory. Never write temporary files to the
    repository root or application directories.
