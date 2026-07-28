
Read AGENTS.md, PROJECT_CONTEXT.md, and CURRENT_MILESTONE.md first.

Implement exactly this approved task:

TITLE:
Modernize travel destination presentation

IMPLEMENTATION BRIEF:
Read the required project documentation, then inspect the existing travel/location templates, shared CSS or static assets, and relevant presentation tests. Identify concrete readability, hierarchy, state-distinction, and responsive-layout deficiencies. Make meaningful changes to at least one existing template or static implementation file so travel options appear as destination cards or structured rows using only descriptive context and availability state already supplied by the application. Clearly distinguish the current location, available destinations, and unavailable destinations; emphasize primary travel controls; and provide usable desktop and mobile layouts consistent with the existing visual system. Preserve every location ID, route, form action, submitted value, requirement, cost, and travel behavior exactly. Add or update bounded presentation tests for stable rendering and form-contract details where appropriate. Do not alter backend mechanics to obtain additional presentation data. Run focused tests and the full suite, then update automation/AGENT_REPORT.md with the required completion report.

ALLOWED AREAS:
[
  "src/ai_adventure/presentation/templates",
  "src/ai_adventure/presentation/static",
  "tests",
  "automation/AGENT_REPORT.md"
]

ACCEPTANCE CRITERIA:
[
  "Travel options are presented as readable destination cards or structured destination rows.",
  "Each destination clearly displays its existing name and descriptive context without introducing new gameplay facts.",
  "The current location, available destinations, and unavailable destinations are visually distinguishable.",
  "Primary travel actions are easy to identify while unavailable actions are clearly represented.",
  "Existing location IDs, routes, form actions, submitted values, requirements, costs, and travel behavior remain unchanged.",
  "The travel presentation remains usable at desktop and mobile widths.",
  "At least one allowed template or static implementation file receives a meaningful presentation change; report-only or test-only changes are insufficient.",
  "Focused presentation tests and the full test suite pass."
]

FORBIDDEN CHANGES:
[
  "Changing travel rules, destination availability, requirements, costs, progression, or any other gameplay behavior.",
  "Changing location IDs, route definitions, form actions, field names, or submitted values.",
  "Adding backend-derived presentation data or modifying files outside the allowed areas.",
  "Adding catalogs, authored destinations, gameplay systems, migrations, dependencies, or architecture.",
  "Introducing a JavaScript framework or converting away from server-rendered templates.",
  "Weakening, deleting, or skipping existing tests.",
  "Large unrelated visual refactors or changes spanning more than 25 files."
]

STOP CONDITIONS:
[
  "The required visual states or descriptive context are not available to the existing templates and exposing them would require backend or service changes.",
  "Preserving existing IDs, routes, form actions, submitted values, requirements, costs, or behavior is not possible within the allowed areas.",
  "The current implementation makes the intended distinction between current, available, and unavailable destinations ambiguous as a product decision.",
  "The work would require a migration, new dependency, architecture change, gameplay-rule change, deployment change, or edits outside the allowed areas.",
  "The bounded task would require changing more than 25 files.",
  "Focused or full-suite failures indicate a behavioral regression that cannot be resolved without widening scope."
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


REVIEW REPAIRS REQUIRED:
- Fix failing tests without weakening or deleting them.
- Re-run focused tests and the full suite.

ORIGINAL ACCEPTANCE CRITERIA:
- Travel options are presented as readable destination cards or structured destination rows.
- Each destination clearly displays its existing name and descriptive context without introducing new gameplay facts.
- The current location, available destinations, and unavailable destinations are visually distinguishable.
- Primary travel actions are easy to identify while unavailable actions are clearly represented.
- Existing location IDs, routes, form actions, submitted values, requirements, costs, and travel behavior remain unchanged.
- The travel presentation remains usable at desktop and mobile widths.
- At least one allowed template or static implementation file receives a meaningful presentation change; report-only or test-only changes are insufficient.
- Focused presentation tests and the full test suite pass.

CHANGED FILES FROM PREVIOUS ATTEMPT:
- src/ai_adventure/presentation/static/css/main.css
- src/ai_adventure/presentation/templates/play_scene.html
- tests/test_travel_destinations_ui.py

TEST OUTPUT FROM PREVIOUS ATTEMPT:
stdout:
........................................................................ [ 22%]
........................................................................ [ 45%]
........................................................................ [ 68%]
........................................................................ [ 91%]
........................F.                                               [100%]
================================== FAILURES ===================================
________ test_travel_destination_template_hierarchy_and_form_contracts ________

    def test_travel_destination_template_hierarchy_and_form_contracts() -> None:
        """Template keeps destination hierarchy and travel form contracts."""
    
        template = PLAY_SCENE_TEMPLATE.read_text(encoding="utf-8")
        css = PLAY_CSS.read_text(encoding="utf-8")
    
        assert 'class="travel-list"' in template
        assert "travel-destination--current" in template
        assert "travel-destination--available" in template
        assert 'class="travel-destination-header"' in template
        assert 'class="travel-name"' in template
        assert 'class="travel-blurb"' in template
        assert 'class="travel-status"' in template
        assert "travel-action-primary" in template
    
>       assert 'method="post" action="/play/{{ scene.save_id }}/travel"' in template
E       assert 'method="post" action="/play/{{ scene.save_id }}/travel"' in '<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="utf-8">\n  <meta name="viewport" content="width=device-wi...etails>\n      </aside>\n    </div>\n  </main>\n  <script src="/static/js/main.js?v=ui2"></script>\n</body>\n</html>\n'

tests\test_travel_destinations_ui.py:53: AssertionError
============================== warnings summary ===============================
tests/test_alchemy_phase8.py: 1 warning
tests/test_alembic_migrations.py: 3 warnings
tests/test_event_engine_phase4a.py: 1 warning
tests/test_locations_phase5a.py: 1 warning
tests/test_npcs_phase9b.py: 1 warning
tests/test_sects_phase9d.py: 1 warning
tests/test_spiritual_roots_phase7.py: 1 warning
tests/test_techniques_phase6c.py: 1 warning
  C:\Users\benjamyn\Desktop\ai-projects\AI- Adventure\.venv\Lib\site-packages\alembic\config.py:612: DeprecationWarning: No path_separator found in configuration; falling back to legacy splitting on spaces, commas, and colons for prepend_sys_path.  Consider adding path_separator=os to Alembic config.
    util.warn_deprecated(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED tests/test_travel_destinations_ui.py::test_travel_destination_template_hierarchy_and_form_contracts
1 failed, 313 passed, 10 warnings in 33.51s


stderr:
Focused tests failed.


--- full suite ---


Repair the implementation rather than merely rewriting the report. Make meaningful changes to at least one allowed implementation file unless every acceptance criterion is already satisfied with specific criterion-by-criterion evidence.
The PowerShell/batch/shell/Python script ban and run-directory diagnostic-file limit above still apply during repair.