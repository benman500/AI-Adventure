
Read AGENTS.md, PROJECT_CONTEXT.md, and CURRENT_MILESTONE.md first.

Implement exactly this approved task:

TITLE:
Story-first responsive play layout

IMPLEMENTATION BRIEF:
After reading the required project documents and inspecting the existing play-scene templates, styles, and presentation tests, refactor only the existing server-rendered play layout. Give the story and current location a prominent main narrative column, retain Working Toward as visible information, and place character and cultivation details in a quieter secondary sidebar using accessible collapsible markup. Add or adjust existing CSS for clear action hierarchy, comfortable spacing, and a readable single-column mobile layout. Preserve all existing routes, form actions, template context variables, gameplay behavior, and presentation content. Update or add narrowly scoped presentation tests only where needed, then update automation/AGENT_REPORT.md if that file is within the permitted template/static/tests scope; otherwise stop and report the scope conflict.

ALLOWED AREAS:
[
  "src/ai_adventure/presentation/templates",
  "src/ai_adventure/presentation/static",
  "tests"
]

ACCEPTANCE CRITERIA:
[
  "Story content and current location are the primary visual focus of the play scene.",
  "Working Toward remains visible without requiring expansion.",
  "Character and cultivation details are accessible through collapsible secondary UI.",
  "The layout becomes a readable single-column presentation on mobile-sized screens.",
  "Existing routes, form submissions, template data, and gameplay behavior are unchanged.",
  "All focused presentation tests and the full pytest suite pass."
]

FORBIDDEN CHANGES:
[
  "Gameplay, progression, engine, service, validation, event, persistence, or catalog changes.",
  "Database or save-format changes.",
  "New dependencies, JavaScript frameworks, or architectural layers.",
  "Conversion away from server-rendered templates.",
  "Route, endpoint, form-action, or template-context contract changes.",
  "Unrelated template or styling refactors.",
  "Weakening, skipping, deleting, or rewriting tests solely to make them pass."
]

STOP CONDITIONS:
[
  "The play-scene template or its styling cannot be identified unambiguously after inspecting the repository.",
  "Meeting the layout requirements would require backend, gameplay-rule, route, persistence, or template-context changes.",
  "Accessible collapsing would require a new dependency or framework.",
  "Required edits fall outside the allowed path prefixes, including automation/AGENT_REPORT.md.",
  "Existing tests reveal that the requested visual hierarchy conflicts with locked presentation or gameplay behavior."
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
