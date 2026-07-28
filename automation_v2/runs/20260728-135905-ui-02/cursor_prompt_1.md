
Read AGENTS.md, PROJECT_CONTEXT.md, and CURRENT_MILESTONE.md first.

Implement exactly this approved task:

TITLE:
Modernize character creation presentation

IMPLEMENTATION BRIEF:
After reading the required project documentation, inspect the existing character-creation templates, styles, and presentation tests. Redesign only the server-rendered character-creation markup and existing static styling. Visually separate each question using semantic fieldsets or equivalent accessible grouping; place every personality answer immediately beneath its corresponding question; and present background options as fully clickable label-based cards. Preserve every existing form action, HTTP method, route, input type, field name, submitted value, validation path, and gameplay behavior exactly. Add clear selected, hover, and keyboard-visible focus states without requiring a new framework or dependency. Ensure the layout adapts cleanly to desktop and mobile widths and retains usable keyboard navigation. Add or update narrowly scoped presentation tests that verify the preserved form contract and the structural association of questions and choices. Update automation/AGENT_REPORT.md with files changed, tests, results, risks, and any review needs.

ALLOWED AREAS:
[
  "src/ai_adventure/presentation/templates",
  "src/ai_adventure/presentation/static",
  "tests",
  "automation/AGENT_REPORT.md"
]

ACCEPTANCE CRITERIA:
[
  "Each character-creation question is visually distinct and has an understandable accessible label or legend.",
  "Background options are fully clickable cards backed by the existing form controls.",
  "Each personality answer is rendered directly beneath and structurally associated with the correct question.",
  "Selected, hovered, and keyboard-focused options have clear visual states.",
  "Existing form actions, methods, field names, submitted values, routes, validation, and gameplay behavior are unchanged.",
  "Character creation remains usable with keyboard navigation and at desktop and mobile widths.",
  "Focused presentation tests verify the form contract and choice grouping.",
  "The focused tests and full pytest suite pass.",
  "automation/AGENT_REPORT.md records the completed work and test results."
]

FORBIDDEN CHANGES:
[
  "Changes to gameplay rules, character creation mechanics, validation behavior, services, engines, persistence, or routes.",
  "Changes to existing form field names, submitted values, form actions, or HTTP methods.",
  "Database or save-format changes.",
  "New dependencies, JavaScript frameworks, architecture, catalogs, or gameplay systems.",
  "Conversion away from the existing server-rendered presentation architecture.",
  "Unrelated template, styling, test, or application refactors.",
  "Weakening, deleting, or skipping existing tests."
]

STOP CONDITIONS:
[
  "The current question-to-answer or field-to-value mapping cannot be determined unambiguously from the implementation and tests.",
  "The redesign would require changing a route, backend validation, submitted value, gameplay rule, service, engine, or persistence behavior.",
  "The work requires a migration, new dependency, new framework, or architectural change.",
  "Existing tests indicate that the requested presentation conflicts with the preserved form contract.",
  "Completion would require changes outside the allowed areas or more than 25 changed files."
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


REVIEW REPAIRS REQUIRED:
- Fix failing tests without weakening or deleting them.
- Re-run focused tests and the full suite.
Repair only these findings. Do not broaden the task.