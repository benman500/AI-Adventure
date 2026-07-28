
Read AGENTS.md, PROJECT_CONTEXT.md, and CURRENT_MILESTONE.md first.

Implement exactly this approved task:

TITLE:
Create story-first play layout

IMPLEMENTATION BRIEF:
After reading the required project documentation, inspect the existing play-scene templates, styles, and presentation tests. Refactor only the server-rendered play layout and existing static styling so the current location and narrative occupy a clear primary column, with a visually quieter secondary sidebar. Keep Working Toward visible without requiring expansion. Place character and cultivation details in accessible collapsible sections using existing platform/template capabilities. Ensure the layout stacks cleanly and remains readable on mobile. Preserve all existing actions, data, routes, mechanics, and service boundaries. Add or adjust focused presentation tests only where needed to verify the rendered structure, without weakening existing coverage. Update automation/AGENT_REPORT.md only if it is within the allowed template/static scope; otherwise stop and request scope clarification before editing it.

ALLOWED AREAS:
[
  "src/ai_adventure/presentation/templates",
  "src/ai_adventure/presentation/static",
  "tests"
]

ACCEPTANCE CRITERIA:
[
  "The current location and story content are the dominant visual elements in the play scene.",
  "Working Toward remains visible in the default layout.",
  "Character and cultivation details are available through accessible collapsible sections.",
  "All existing play actions and displayed gameplay information remain available and functionally unchanged.",
  "The layout uses a main narrative column and quieter secondary sidebar on wider screens.",
  "The layout stacks into a readable, usable mobile presentation without horizontal overflow.",
  "No gameplay rules, routes, persistence behavior, or server-rendered architecture are changed.",
  "Focused presentation tests and the full test suite pass."
]

FORBIDDEN CHANGES:
[
  "Gameplay, progression, calculation, or validation changes",
  "Database or save-format changes",
  "New systems, catalogs, architecture, or dependencies",
  "New JavaScript frameworks or conversion away from server-rendered templates",
  "Route, service, engine, event, or persistence changes",
  "Unrelated template or styling refactors",
  "Deleting, skipping, weakening, or rewriting tests solely to obtain passing results",
  "Changes outside the allowed path prefixes"
]

STOP CONDITIONS:
[
  "The play scene cannot be identified unambiguously from the existing templates and tests.",
  "Implementing collapsible details would require a new dependency, framework, route, persistence change, or gameplay-rule change.",
  "Required information or actions would need to be removed rather than visually reorganized.",
  "The task requires edits outside the allowed path prefixes.",
  "Existing tests reveal that the proposed layout would change gameplay behavior or break the current living loop.",
  "Completion-report requirements cannot be satisfied without editing automation/AGENT_REPORT.md outside the approved scope."
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
