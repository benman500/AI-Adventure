
Read AGENTS.md, PROJECT_CONTEXT.md, and CURRENT_MILESTONE.md first.

Implement exactly this approved task:

TITLE:
Modernize NPC interaction cards

IMPLEMENTATION BRIEF:
Read the required project documents, then inspect the current NPC templates, shared layout/partials, CSS, and relevant presentation tests. Identify concrete hierarchy, grouping, action-emphasis, unavailable-state, and responsive-layout deficiencies. Make meaningful changes to at least one NPC-related template or stylesheet within the allowed areas so each NPC’s existing name, role, and description are clearly structured; interactions are visibly contained with their NPC; and existing semantic cues distinguish primary from secondary actions. Improve unavailable interaction presentation only where the current UI already supports unavailable interactions, preserving their existing accessibility and behavior. Add or update focused presentation tests for the rendered structure and preserved form contracts. Do not fabricate NPC facts or infer new gameplay states. Preserve every existing interaction identifier, route, form action and method, field name, submitted value, requirement, reward, and service behavior. Use the current server-rendered architecture and existing styling approach. Verify desktop and mobile readability, run focused NPC tests and the full test suite, then update automation/AGENT_REPORT.md with the required completion details.

ALLOWED AREAS:
[
  "src/ai_adventure/presentation/templates",
  "src/ai_adventure/presentation/static",
  "tests",
  "automation/AGENT_REPORT.md"
]

ACCEPTANCE CRITERIA:
[
  "Each visible NPC presents its existing name, role, and description with a clear readable hierarchy.",
  "Every NPC interaction is visually grouped with the NPC to which it belongs.",
  "Primary and secondary interactions are visually distinguishable using existing semantics without changing behavior.",
  "Interactions already represented as unavailable remain understandable and accessible, without introducing new availability rules.",
  "Existing interaction IDs, routes, form actions and methods, field names, submitted values, requirements, rewards, and gameplay behavior remain unchanged.",
  "NPC cards and their actions remain readable and usable at desktop and mobile widths.",
  "Focused presentation tests cover the relevant NPC rendering and form contracts.",
  "The focused tests and the complete pytest suite pass.",
  "automation/AGENT_REPORT.md records files changed, tests run, results, remaining risks, and any human-review needs."
]

FORBIDDEN CHANGES:
[
  "Gameplay rules, interaction availability logic, requirements, rewards, or progression",
  "Interaction identifiers, routes, form actions or methods, submitted field names, or submitted values",
  "Database models, migrations, catalogs, services, engines, or transaction boundaries",
  "New dependencies, JavaScript frameworks, architecture, or client-rendered conversion",
  "Invented NPC roles, descriptions, facts, or mechanical states",
  "Unrelated UI refactors or changes outside the allowed areas",
  "Completion consisting only of tests, reports, logs, or automation-file updates"
]

STOP CONDITIONS:
[
  "The current templates do not expose an existing role or equivalent presentation fact for an NPC, and satisfying the role requirement would require inventing data or changing gameplay/catalog code.",
  "Primary versus secondary interaction status cannot be determined from existing presentation data or semantics without a new product or gameplay decision.",
  "Preserving unavailable-interaction accessibility would require changing availability rules, services, routes, or form behavior.",
  "The work requires a migration, new dependency, architecture change, deployment change, or edits outside the allowed areas.",
  "The implementation would require more than 25 changed files.",
  "Focused or full-suite failures reveal a required gameplay-rule change or an unrelated issue that cannot be resolved within scope."
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
