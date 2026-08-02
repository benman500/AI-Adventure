"""Presentation checks for gameplay action visual hierarchy (UI-only)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from httpx2 import ASGITransport, AsyncClient

from tests.conftest_helpers import VALID_IDENTITY_ANSWERS, make_test_app

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAY_SCENE_TEMPLATE = (
    REPO_ROOT
    / "src"
    / "ai_adventure"
    / "presentation"
    / "templates"
    / "play_scene.html"
)
PLAY_CSS = (
    REPO_ROOT / "src" / "ai_adventure" / "presentation" / "static" / "css" / "main.css"
)


def _answer_form_fields() -> dict[str, str]:
    return {f"answer_{key}": value for key, value in VALID_IDENTITY_ANSWERS.items()}


def test_action_hierarchy_classes_and_interactive_states() -> None:
    """Primary, secondary, and utility controls stay distinct with clear states."""

    template = PLAY_SCENE_TEMPLATE.read_text(encoding="utf-8")
    css = PLAY_CSS.read_text(encoding="utf-8")

    # Story continue stays primary; utility chrome stays utility.
    assert 'class="button primary btn-primary"' in template
    assert 'class="button utility btn-utility"' in template
    assert 'class="moment-block action-primary"' in template

    # Location and cultivation methods join secondary hierarchy without form changes.
    assert "here-action-secondary" in template
    assert "btn-secondary" in template
    assert 'class="moment-block action-secondary"' in template
    assert 'name="action_id"' in template
    assert 'value="{{ action.id }}"' in template
    assert 'method="post" action="/play/{{ scene.save_id }}/location-action"' in template
    assert "method-action-secondary" in template
    assert 'value="{{ method.id }}"' in template

    assert ".btn-primary" in css
    assert ".btn-secondary" in css
    assert ".btn-utility" in css
    assert ".action-primary h2" in css
    assert re.search(
        r"\.action-primary h2\s*\{[^}]*color:\s*var\(--gold\)",
        css,
        re.DOTALL,
    )
    # Primary / secondary decision zones are framed, not bare heading stacks.
    assert re.search(
        r"\.action-primary\s*\{[^}]*border-left:\s*3px solid var\(--gold\)",
        css,
        re.DOTALL,
    )
    assert ".action-secondary" in css
    assert ".action-secondary h2" in css
    assert re.search(
        r"\.action-secondary h2\s*\{[^}]*color:\s*var\(--jade\)",
        css,
        re.DOTALL,
    )
    assert re.search(
        r"\.action-secondary\s*\{[^}]*border-left:\s*3px solid var\(--jade\)",
        css,
        re.DOTALL,
    )
    assert ".travel-section h2" in css
    assert ".people-section h2" in css
    assert 'class="moment-block people-section"' in template

    assert ".btn-primary:hover:not(:disabled)" in css
    assert ".btn-primary:active:not(:disabled)" in css
    assert ".btn-secondary:hover:not(:disabled)" in css
    assert ".btn-secondary:active:not(:disabled)" in css
    assert ".btn-utility:hover:not(:disabled)" in css
    assert ".btn-utility:active:not(:disabled)" in css

    assert ".button:focus-visible" in css
    assert "button:focus-visible" in css
    assert ".btn-primary:focus-visible" in css
    assert ".btn-secondary:focus-visible" in css
    assert ".btn-utility:focus-visible" in css
    assert ".button:disabled" in css
    assert ".btn-primary:disabled" in css
    assert ".btn-secondary:disabled" in css
    assert ".btn-utility:disabled" in css

    assert ".here-action-secondary" in css
    assert ".method-action-secondary" in css
    # Secondary tier (shared + Here/method/NPC) uses jade left accent, not gold fill.
    assert re.search(
        r"\.btn-secondary\s*,\s*\.button\.secondary\s*\{[^}]*border-left:\s*3px solid var\(--jade\)",
        css,
        re.DOTALL,
    )
    assert re.search(
        r"\.here-action-secondary\s*\{[^}]*border-left:\s*3px solid var\(--jade\)",
        css,
        re.DOTALL,
    )
    assert re.search(
        r"\.method-action-secondary\s*\{[^}]*border-left:\s*3px solid var\(--jade\)",
        css,
        re.DOTALL,
    )
    assert re.search(
        r"\.npc-actions\s+\.npc-action-secondary\s*\{[^}]*border-left:\s*3px solid var\(--jade\)",
        css,
        re.DOTALL,
    )
    assert ".npc-actions .npc-action-secondary:active:not(:disabled)" in css
    assert ".npc-actions .npc-action-secondary:focus-visible" in css
    assert ".npc-actions .npc-action-secondary:disabled" in css
    assert ".method-list .method-action-secondary:disabled" in css
    assert ".btn-utility:disabled" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "transition: none !important" in css
    assert "transform: none !important" in css
    assert "travel-action-primary:hover:not(:disabled)" in css
    assert (
        ".method-list .method-action-secondary:hover:not(:disabled)" in css
        or ".method-list .method-action-secondary:active:not(:disabled)" in css
    )

    assert "@media (max-width: 560px)" in css
    assert re.search(
        r"@media \(max-width: 560px\)[\s\S]*\.here-action-secondary\s*\{",
        css,
    )
    assert re.search(
        r"@media \(max-width: 560px\)[\s\S]*\.method-action-secondary\s*\{",
        css,
    )
    assert re.search(
        r"@media \(max-width: 560px\)[\s\S]*\.action-primary\s*,\s*\.action-secondary\s*\{",
        css,
    )


@pytest.mark.asyncio
async def test_play_scene_preserves_action_contracts_with_hierarchy(
    tmp_path: Path,
) -> None:
    """Rendered play scene keeps form contracts while exposing hierarchy classes."""

    app = make_test_app(tmp_path, filename="action_hierarchy_ui.db")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=False,
    ) as client:
        create = await client.post(
            "/new",
            data={
                "character_name": "Hierarchy Hero",
                "background_id": "hunter",
                **_answer_form_fields(),
            },
        )
        assert create.status_code == 303
        save_id = create.headers["location"].rsplit("/", 1)[-1]

        play = await client.get(f"/play/{save_id}")
        assert play.status_code == 200
        html = play.text

        assert "btn-primary" in html
        assert "btn-utility" in html
        assert f'action="/play/{save_id}/action"' in html
        assert 'name="action_id"' in html
        assert 'method="post"' in html

        # Utility chrome order and destinations unchanged.
        assert f'href="/play/{save_id}/status"' in html
        assert 'href="/saves"' in html
        html.index('btn-utility')  # present
        assert html.index(f'href="/play/{save_id}/status"') < html.index(
            'href="/saves"'
        )
