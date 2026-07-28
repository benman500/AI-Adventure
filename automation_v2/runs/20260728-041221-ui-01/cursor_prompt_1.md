
Read AGENTS.md, PROJECT_CONTEXT.md, and CURRENT_MILESTONE.md first.

Implement exactly this approved task:

TITLE:
Create story-first play layout

IMPLEMENTATION BRIEF:
Inspect the existing play-scene templates, styles, and relevant tests. Refactor only the presentation markup and CSS so the current location and narrative occupy the dominant responsive main column, with Working Toward remaining visible in a quieter secondary sidebar. Place character and cultivation information in accessible collapsible sections using the existing server-rendered approach and native HTML where practical. Preserve all routes, forms, action names, submitted values, template context assumptions, and gameplay behavior. Ensure the layout stacks cleanly on mobile. Add or adjust narrowly scoped presentation tests only where needed, without weakening existing assertions.

ALLOWED AREAS:
[
  "src/ai_adventure/presentation/templates",
  "src/ai_adventure/presentation/static",
  "tests"
]

ACCEPTANCE CRITERIA:
[
  "Story content and current location are the dominant visual focus of the play scene.",
  "Working Toward remains visible without requiring the player to expand a section.",
  "Character and cultivation details are available in accessible collapsible sections.",
  "Existing actions, forms, routes, template data, and gameplay behavior remain unchanged.",
  "The layout is readable and usable at mobile widths without horizontal overflow.",
  "Focused presentation tests and the full test suite pass."
]

FORBIDDEN CHANGES:
[
  "Gameplay, progression, cultivation, aspiration, event, travel, or location rules.",
  "Service, engine, persistence, transaction, route, or template-context contracts.",
  "Database schema or migrations.",
  "New dependencies, JavaScript frameworks, catalogs, systems, or architectural layers.",
  "Conversion away from the existing server-rendered architecture.",
  "Unrelated refactors or edits outside the allowed areas.",
  "Deleting, skipping, weakening, or rewriting tests merely to make them pass."
]

STOP CONDITIONS:
[
  "The layout cannot be implemented without changing gameplay behavior, routes, services, persistence, or template-context contracts.",
  "Collapsible details require a new dependency, framework, or architectural mechanism.",
  "Required presentation behavior is ambiguous after inspecting the existing play scene and tests.",
  "The work would require editing outside the allowed areas or changing more than 25 files.",
  "Existing failures indicate that preserving current gameplay requires changes beyond this UI-only task."
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