"""Presentation checks for the story-first play layout (UI-only)."""

from __future__ import annotations

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


def test_play_scene_template_keeps_working_toward_visible() -> None:
    """Working Toward stays outside collapsible details; secondary stacks after story."""

    template = PLAY_SCENE_TEMPLATE.read_text(encoding="utf-8")
    css = PLAY_CSS.read_text(encoding="utf-8")

    toward_idx = template.index("Working Toward")
    aspiration_section = template[
        template.index('class="aspiration-side"') : template.index(
            "</section>", template.index('class="aspiration-side"')
        )
    ]
    assert "<details" not in aspiration_section
    assert toward_idx < template.index('<details class="side-panel" open>')

    assert 'class="play-main"' in template
    assert "play-secondary" in template
    assert template.index('class="play-main"') < template.index("play-secondary")

    assert "@media (max-width: 960px)" in css
    assert "order: 1" in css
    assert "order: 2" in css


@pytest.mark.asyncio
async def test_play_scene_uses_story_first_layout(tmp_path: Path) -> None:
    """Play HTML keeps story/location primary and character details collapsible."""

    app = make_test_app(tmp_path, filename="play_layout_ui.db")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=False,
    ) as client:
        create = await client.post(
            "/new",
            data={
                "character_name": "Layout Hero",
                "background_id": "hunter",
                **_answer_form_fields(),
            },
        )
        save_id = create.headers["location"].rsplit("/", 1)[-1]

        play = await client.get(f"/play/{save_id}")
        assert play.status_code == 200
        html = play.text

        assert 'class="play-layout"' in html
        assert 'class="play-main"' in html
        assert "play-secondary" in html
        assert 'class="story-header"' in html
        assert 'class="location-kicker"' in html
        assert 'class="story-stage"' in html
        assert 'id="narration"' in html

        main_idx = html.index('class="play-main"')
        side_idx = html.index("play-secondary")
        story_idx = html.index('id="narration"')
        assert main_idx < story_idx < side_idx

        assert "<summary>Identity</summary>" in html
        assert '<details class="side-panel" open>' in html
        assert "<summary>Cultivation</summary>" in html
        assert "<summary>Inventory</summary>" in html

        assert 'method="post" action="/play/' in html
        assert f'action="/play/{save_id}/action"' in html

        assert "Working Toward" not in html
        assert 'class="aspiration-side"' not in html
