
Read AGENTS.md, PROJECT_CONTEXT.md, and CURRENT_MILESTONE.md first.

Implement exactly this approved task:

TITLE:
Create story-first play layout

IMPLEMENTATION BRIEF:
Refactor only the existing play-scene template markup and associated styles into a responsive story-first layout. Place the current location and narrative content in the primary column, with a visually quieter secondary sidebar. Keep Working Toward visible without requiring expansion. Place existing character and cultivation details in accessible collapsible sections, preferably using native details/summary elements. On narrow screens, stack content in a readable order with the narrative and primary actions first. Reuse the current server-rendered data, routes, forms, actions, and presentation patterns; do not alter mechanics or introduce new client-side architecture. Preserve selectors and semantics relied upon by existing tests where practical, and add or adjust presentation tests only for the changed layout behavior.

ALLOWED AREAS:
[
  "src/ai_adventure/presentation/templates",
  "src/ai_adventure/presentation/static",
  "tests"
]

ACCEPTANCE CRITERIA:
[
  "The current location and story content are the dominant visual elements in the play scene.",
  "Working Toward remains visible without opening a collapsible section.",
  "Existing character and cultivation details remain available through accessible collapsible sections.",
  "Primary gameplay actions remain obvious and retain their existing behavior.",
  "The layout stacks into a readable story-first order on mobile-width screens without horizontal overflow.",
  "Existing routes, forms, submitted values, gameplay behavior, and server-rendered architecture are unchanged.",
  "All focused presentation tests and the complete pytest suite pass."
]

FORBIDDEN CHANGES:
[
  "Gameplay, progression, validation, clock, engine, event, persistence, or catalog changes",
  "Database or save-format changes",
  "Route, service, or view-model contract changes",
  "New dependencies or JavaScript frameworks",
  "New gameplay systems or client-side state systems",
  "Conversion away from server-rendered templates",
  "Unrelated template or styling refactors",
  "Weakening, deleting, or skipping existing tests"
]

STOP CONDITIONS:
[
  "The layout cannot be implemented using the data already supplied to the play-scene templates.",
  "A route, service, engine rule, persistence model, save format, or database change appears necessary.",
  "A new dependency or client-side framework appears necessary.",
  "The requested collapsible presentation would hide Working Toward or required primary actions.",
  "Implementation would require a broad shared-template refactor or changes outside the allowed areas.",
  "The intended play-scene template or relevant styles cannot be identified unambiguously.",
  "Completing the task would require modifying more than 25 files."
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
