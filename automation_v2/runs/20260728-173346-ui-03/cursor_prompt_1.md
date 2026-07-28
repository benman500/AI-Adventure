
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


REVIEW REPAIRS REQUIRED:
- Fix failing tests without weakening or deleting them.
- Re-run focused tests and the full suite.

ORIGINAL ACCEPTANCE CRITERIA:
- Each visible NPC presents its existing name, role, and description with a clear readable hierarchy.
- Every NPC interaction is visually grouped with the NPC to which it belongs.
- Primary and secondary interactions are visually distinguishable using existing semantics without changing behavior.
- Interactions already represented as unavailable remain understandable and accessible, without introducing new availability rules.
- Existing interaction IDs, routes, form actions and methods, field names, submitted values, requirements, rewards, and gameplay behavior remain unchanged.
- NPC cards and their actions remain readable and usable at desktop and mobile widths.
- Focused presentation tests cover the relevant NPC rendering and form contracts.
- The focused tests and the complete pytest suite pass.
- automation/AGENT_REPORT.md records files changed, tests run, results, remaining risks, and any human-review needs.

CHANGED FILES FROM PREVIOUS ATTEMPT:
- src/ai_adventure/presentation/static/css/main.css
- src/ai_adventure/presentation/templates/play_scene.html
- tests/test_npc_cards_ui.py

TEST OUTPUT FROM PREVIOUS ATTEMPT:
stdout:
........................................................................ [ 23%]
........................................................................ [ 46%]
........................................................................ [ 69%]
..............F......................................................... [ 92%]
........................                                                 [100%]
================================== FAILURES ===================================
_____________ test_npc_cards_render_grouped_actions_and_emphasis ______________

tmp_path = WindowsPath('C:/Users/benjamyn/AppData/Local/Temp/pytest-of-benjamyn/pytest-140/test_npc_cards_render_grouped_0')

    @pytest.mark.asyncio
    async def test_npc_cards_render_grouped_actions_and_emphasis(tmp_path: Path) -> None:
        """Rendered NPC cards group actions and distinguish duration-cost verbs."""
    
        app = make_test_app(tmp_path, filename="npc_cards_ui.db")
        db_path = tmp_path / "npc_cards_ui.db"
        settings = Settings(
            database_url=f"sqlite:///{db_path.as_posix()}",
            narrator_backend="stub",
        )
        engine = create_db_engine(settings)
        service = GameAppService(
            settings=settings,
            session_factory=create_session_factory(settings, engine=engine),
        )
    
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
        ) as client:
            create = await client.post(
                "/new",
                data={
                    "character_name": "Npc Card Hero",
                    "background_id": "merchant_family",
                    **_answer_form_fields(),
                },
            )
            assert create.status_code == 303
            save_id = create.headers["location"].rsplit("/", 1)[-1]
    
            advance_to_cultivation_hall(service, save_id)
    
            play = await client.get(f"/play/{save_id}")
            assert play.status_code == 200
            html = play.text
    
            assert 'aria-label="People here"' in html
            assert 'class="npc-card"' in html
            assert 'class="npc-card-header"' in html
            assert 'class="npc-name"' in html
            assert 'class="npc-role"' in html
            assert 'class="npc-blurb"' in html
    
            pei_marker = 'data-npc-id="npc_instructor_001"'
            assert pei_marker in html
            pei_start = html.index(pei_marker)
            pei_end = html.index("</article>", pei_start)
            pei_card = html[pei_start:pei_end]
    
            assert "Instructor Pei" in pei_card
            assert 'class="npc-role"' in pei_card
            assert 'class="npc-blurb"' in pei_card
            assert 'role="group"' in pei_card
            assert "Interactions with Instructor Pei" in pei_card
    
            assert f'action="/play/{save_id}/npcs/interact"' in pei_card
            assert 'name="npc_id"' in pei_card
            assert 'value="npc_instructor_001"' in pei_card
            assert 'value="inspect"' in pei_card
            assert 'value="greet"' in pei_card
            assert 'value="ask_guidance"' in pei_card
            assert 'name="action_id"' in pei_card
    
            assert "npc-action-secondary" in pei_card
            assert "npc-action-primary" in pei_card
    
            inspect_idx = pei_card.index('value="inspect"')
            inspect_window = pei_card[inspect_idx : inspect_idx + 220]
            assert "npc-action-secondary" in inspect_window
    
            guidance_idx = pei_card.index('value="ask_guidance"')
            guidance_window = pei_card[guidance_idx : guidance_idx + 280]
            assert "npc-action-primary" in guidance_window
>           assert "1d" in guidance_window
E           assert '1d' in 'value="ask_guidance"\n                      class="button primary btn-primary npc-action-primary"\n                  ...on."\n                    >\n                      <span class="npc-action-label">Ask Guidance</span>\n               '

tests\test_npc_cards_ui.py:145: AssertionError
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
FAILED tests/test_npc_cards_ui.py::test_npc_cards_render_grouped_actions_and_emphasis
1 failed, 311 passed, 10 warnings in 35.37s


stderr:
Focused tests failed.


--- full suite ---


Repair the implementation rather than merely rewriting the report. Make meaningful changes to at least one allowed implementation file unless every acceptance criterion is already satisfied with specific criterion-by-criterion evidence.
The PowerShell/batch/shell/Python script ban and run-directory diagnostic-file limit above still apply during repair.