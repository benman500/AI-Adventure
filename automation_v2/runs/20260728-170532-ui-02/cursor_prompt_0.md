
Read AGENTS.md, PROJECT_CONTEXT.md, and CURRENT_MILESTONE.md first.

Implement exactly this approved task:

TITLE:
Modernize character creation presentation

IMPLEMENTATION BRIEF:
Inspect the existing character-creation templates, styles, and presentation tests. Redesign only the server-rendered presentation so each question forms a distinct, readable group; background options are fully clickable cards using correctly associated labels and existing form controls; and personality answers remain directly beneath their corresponding question. Add clear selected, hover, and keyboard-focus-visible states, plus responsive styling for desktop and mobile. Preserve every existing route, form action, HTTP method, input name, submitted value, validation path, and gameplay behavior. Prefer existing shared styling patterns and minimal template/CSS changes; do not introduce a JavaScript framework or move logic out of the existing presentation flow. Add or update focused presentation tests without weakening existing assertions. Run focused tests and the full suite, then update automation/AGENT_REPORT.md with files changed, commands and results, risks, and review items.

ALLOWED AREAS:
[
  "src/ai_adventure/presentation/templates",
  "src/ai_adventure/presentation/static",
  "tests",
  "automation/AGENT_REPORT.md"
]

ACCEPTANCE CRITERIA:
[
  "Each character-creation question is visually separated, readable, and associated with its own answer group.",
  "Background choices are fully clickable cards while retaining the existing form controls, field names, and submitted values.",
  "Personality answers render directly beneath the correct question.",
  "Choices have clear selected, hover, and keyboard focus-visible states.",
  "Existing routes, form actions, HTTP methods, field names, submitted values, validation behavior, and gameplay behavior remain unchanged.",
  "The character-creation page remains usable without horizontal overflow at desktop and mobile widths.",
  "Focused presentation tests pass.",
  "The full test suite passes with python -m pytest -q.",
  "automation/AGENT_REPORT.md records the completed work and test results."
]

FORBIDDEN CHANGES:
[
  "Changing gameplay, character-creation rules, validation rules, or generated character state.",
  "Changing routes, form actions, HTTP methods, input names, option values, or submission behavior.",
  "Adding dependencies, JavaScript frameworks, client-side gameplay logic, or new architectural layers.",
  "Adding database changes, migrations, catalogs, progression systems, or other gameplay systems.",
  "Converting the page away from the existing server-rendered architecture.",
  "Editing files outside the listed allowed areas.",
  "Deleting, skipping, weakening, or rewriting tests solely to make them pass.",
  "Performing unrelated template, styling, or test refactors."
]

STOP CONDITIONS:
[
  "The requested visual design cannot be implemented without changing existing form names, submitted values, routes, validation, or gameplay behavior.",
  "Implementation would require a new dependency, framework, architecture change, migration, or edit outside the allowed areas.",
  "The mapping between personality questions and their answer values is ambiguous in the existing implementation.",
  "Existing focused tests reveal conflicting product expectations that require choosing new behavior.",
  "The full test suite fails for reasons caused by the changes and cannot be fixed within the allowed presentation scope.",
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
