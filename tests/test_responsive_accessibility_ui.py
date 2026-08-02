"""Presentation checks for responsive layout and accessibility (UI-only)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from httpx2 import ASGITransport, AsyncClient

from tests.conftest_helpers import VALID_IDENTITY_ANSWERS, make_test_app

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAY_CSS = (
    REPO_ROOT / "src" / "ai_adventure" / "presentation" / "static" / "css" / "main.css"
)
PLAY_JS = (
    REPO_ROOT / "src" / "ai_adventure" / "presentation" / "static" / "js" / "main.js"
)
PLAY_SCENE_TEMPLATE = (
    REPO_ROOT
    / "src"
    / "ai_adventure"
    / "presentation"
    / "templates"
    / "play_scene.html"
)
PLAY_STATUS_TEMPLATE = (
    REPO_ROOT
    / "src"
    / "ai_adventure"
    / "presentation"
    / "templates"
    / "play_status.html"
)
NEW_GAME_TEMPLATE = (
    REPO_ROOT
    / "src"
    / "ai_adventure"
    / "presentation"
    / "templates"
    / "new_game.html"
)


def _answer_form_fields() -> dict[str, str]:
    return {f"answer_{key}": value for key, value in VALID_IDENTITY_ANSWERS.items()}


def test_responsive_breakpoints_and_overflow_guards() -> None:
    """Narrow, tablet, and desktop rules guard overflow without clipping focus rings."""

    css = PLAY_CSS.read_text(encoding="utf-8")

    assert "@media (max-width: 960px)" in css
    assert "@media (max-width: 768px)" in css
    assert "@media (max-width: 560px)" in css
    assert "overflow-x: clip" in css
    assert "overflow-wrap: anywhere" in css
    assert re.search(
        r"\.play-chrome \.place\s*\{[^}]*overflow-wrap:\s*anywhere",
        css,
        re.DOTALL,
    )
    assert re.search(
        r"\.side-panel\s*\{[^}]*overflow:\s*visible",
        css,
        re.DOTALL,
    )
    assert re.search(
        r"@media \(max-width: 768px\)[\s\S]*\.travel-destination-header\s*\{"
        r"[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\)",
        css,
    )


def test_keyboard_focus_and_clickable_card_access() -> None:
    """Interactive controls and choice cards expose visible keyboard focus."""

    css = PLAY_CSS.read_text(encoding="utf-8")
    template = NEW_GAME_TEMPLATE.read_text(encoding="utf-8")

    assert "a:focus-visible" in css
    assert ".button:focus-visible" in css
    assert ".side-panel > summary:focus-visible" in css
    assert ".drawer > summary:focus-visible" in css
    assert ".bg-card:has(input:focus-visible)" in css
    assert ".answer-card:has(input:focus-visible)" in css
    assert "outline-offset: 3px" in css
    assert "clip-path: inset(50%)" in css
    assert 'for="{{ bg_input_id }}"' in template
    assert 'for="{{ answer_input_id }}"' in template
    assert 'type="radio"' in template
    assert 'name="background_id"' in template
    assert 'name="answer_{{ question.id }}"' in template


def test_collapsible_disclosure_semantics() -> None:
    """Collapsed panels use native details plus clear labels and open/close glyphs."""

    css = PLAY_CSS.read_text(encoding="utf-8")
    play = PLAY_SCENE_TEMPLATE.read_text(encoding="utf-8")
    status = PLAY_STATUS_TEMPLATE.read_text(encoding="utf-8")

    assert 'class="disclosure-label">Identity</span>' in play
    assert 'class="disclosure-label">Cultivation</span>' in play
    assert 'class="disclosure-label">Inventory</span>' in play
    assert 'class="disclosure-label">Character</span>' in status
    assert "<details class=\"side-panel\"" in play or "<details class='side-panel'" in play
    assert "<details class=\"drawer\"" in status or 'class="drawer"' in status
    assert re.search(
        r"\.side-panel > summary::after\s*\{[^}]*content:\s*\"\+\"",
        css,
        re.DOTALL,
    )
    assert re.search(
        r"\.side-panel\[open\] > summary::after\s*\{[^}]*content:\s*\"−\"",
        css,
        re.DOTALL,
    )
    assert re.search(
        r"\.drawer > summary::after\s*\{[^}]*content:\s*\"\+\"",
        css,
        re.DOTALL,
    )


def test_reduced_motion_disables_nonessential_motion() -> None:
    """prefers-reduced-motion turns off transitions, animations, and hover transforms."""

    css = PLAY_CSS.read_text(encoding="utf-8")

    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "animation: none !important" in css
    assert "transition: none !important" in css
    assert "scroll-behavior: auto" in css
    assert ".story-text" in css
    assert ".vn-step" in css
    assert re.search(
        r"@media \(prefers-reduced-motion: reduce\)[\s\S]*transform:\s*none !important",
        css,
    )


def test_creation_wizard_announces_steps() -> None:
    """Character creation exposes a polite live region for step changes."""

    template = NEW_GAME_TEMPLATE.read_text(encoding="utf-8")
    js = PLAY_JS.read_text(encoding="utf-8")

    assert 'id="vn-step-status"' in template
    assert 'aria-live="polite"' in template
    assert "visually-hidden" in template
    assert 'id="vn-step-status"' in js or "vn-step-status" in js
    assert "Step ${index + 1} of ${steps.length}" in js
    assert "aria-hidden" in js
    assert "is-active" in js
    assert "step.hidden" not in js


@pytest.mark.asyncio
async def test_play_and_creation_markup_contracts(tmp_path: Path) -> None:
    """Rendered pages keep routes/fields and include disclosure/live-region markup."""

    app = make_test_app(tmp_path, filename="responsive_a11y_ui.db")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=False,
    ) as client:
        new_page = await client.get("/new")
        assert new_page.status_code == 200
        new_html = new_page.text
        assert 'id="vn-step-status"' in new_html
        assert 'aria-live="polite"' in new_html
        assert 'action="/new"' in new_html
        assert 'name="character_name"' in new_html
        assert 'name="background_id"' in new_html

        create = await client.post(
            "/new",
            data={
                "character_name": "A11y Hero",
                "background_id": "hunter",
                **_answer_form_fields(),
            },
        )
        save_id = create.headers["location"].rsplit("/", 1)[-1]

        play = await client.get(f"/play/{save_id}")
        assert play.status_code == 200
        html = play.text
        assert 'class="disclosure-label">Identity</span>' in html
        assert 'class="disclosure-label">Cultivation</span>' in html
        assert 'class="disclosure-label">Inventory</span>' in html
        assert f'action="/play/{save_id}/action"' in html

        status = await client.get(f"/play/{save_id}/status")
        assert status.status_code == 200
        status_html = status.text
        assert 'class="disclosure-label">Character</span>' in status_html
        assert 'class="disclosure-label">Inventory</span>' in status_html
        assert 'class="disclosure-label">Identity</span>' in status_html
