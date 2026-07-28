"""Presentation checks for the story-first play layout (UI-only)."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx2 import ASGITransport, AsyncClient

from tests.conftest_helpers import VALID_IDENTITY_ANSWERS, make_test_app


def _answer_form_fields() -> dict[str, str]:
    return {f"answer_{key}": value for key, value in VALID_IDENTITY_ANSWERS.items()}


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

        assert 'method="post" action="/play/' in html
        assert f'action="/play/{save_id}/action"' in html

        assert "Working Toward" not in html
