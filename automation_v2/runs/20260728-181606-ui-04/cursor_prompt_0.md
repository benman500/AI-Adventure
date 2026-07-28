
Read AGENTS.md, PROJECT_CONTEXT.md, and CURRENT_MILESTONE.md first.

Implement exactly this approved task:

TITLE:
Modernize travel destination presentation

IMPLEMENTATION BRIEF:
Read the required project documentation, then inspect the current travel/location templates, shared CSS, view-model data, and presentation tests. Identify concrete readability, hierarchy, and responsive-layout deficiencies in the existing travel interface. Update at least one allowed template or static implementation file so existing travel options render as clear destination cards or rows using only descriptive context already supplied by the view model. Visually distinguish the current location from available destinations, make the existing primary travel controls obvious, and ensure the layout remains usable at desktop and mobile widths. Preserve all route URLs, form methods/actions, location IDs, submitted field names and values, requirements, costs, and travel behavior exactly. Do not display or infer unavailable destinations when they are not supplied by the existing view model. Add or update focused presentation tests for the rendered travel structure and preserved form contracts, then update automation/AGENT_REPORT.md with files changed, tests run, results, risks, and review items.

ALLOWED AREAS:
[
  "src/ai_adventure/presentation/templates",
  "src/ai_adventure/presentation/static",
  "tests",
  "automation/AGENT_REPORT.md"
]

ACCEPTANCE CRITERIA:
[
  "Travel options are presented as readable destination cards or destination rows.",
  "Each destination clearly displays its existing name and descriptive context without inventing new content.",
  "The current location and available destinations are visually distinguishable; unavailable destinations are neither inferred nor added when absent from the existing view model.",
  "Primary travel actions are easy to identify and use.",
  "Existing location IDs, route URLs, form methods/actions, submitted field names and values, requirements, costs, and travel behavior remain unchanged.",
  "The travel presentation is usable at desktop and mobile widths without obscured controls or horizontal overflow.",
  "Focused presentation tests and the full test suite pass.",
  "At least one travel-related template or static stylesheet is meaningfully changed; report-only or test-only changes are insufficient."
]

FORBIDDEN CHANGES:
[
  "Gameplay rules, travel calculations, requirements, costs, availability, or progression",
  "Location IDs, route definitions, form contracts, or submitted values",
  "Backend services, engines, persistence, catalogs, or view-model architecture",
  "Inferring or implementing unavailable destinations not supplied by the existing view model",
  "Database migrations or save-format changes",
  "New dependencies, frameworks, systems, or client-side application architecture",
  "Deployment, secrets, or environment files",
  "Unrelated UI refactors"
]

STOP CONDITIONS:
[
  "The requested presentation cannot be implemented without changing travel mechanics, routes, form contracts, backend services, or view-model architecture.",
  "Existing descriptive context or current-location state is ambiguous or unavailable and would need to be invented.",
  "A database migration, new dependency, architecture change, catalog change, or gameplay-rule decision appears necessary.",
  "The required work would exceed the allowed areas or become a large unrelated refactor.",
  "Focused tests reveal an existing product-behavior ambiguity that cannot be resolved from current templates, implementation, tests, and documentation."
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
