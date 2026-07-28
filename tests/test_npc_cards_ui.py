"""Presentation checks for NPC interaction cards (UI-only)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from httpx2 import ASGITransport, AsyncClient

from ai_adventure.config import Settings
from ai_adventure.db import create_db_engine, create_session_factory
from ai_adventure.services import GameAppService
from tests.conftest_helpers import (
    VALID_IDENTITY_ANSWERS,
    advance_to_cultivation_hall,
    make_test_app,
)

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


def test_npc_card_template_hierarchy_and_form_contracts() -> None:
    """Template keeps name/role/description hierarchy and NPC form contracts."""

    template = PLAY_SCENE_TEMPLATE.read_text(encoding="utf-8")
    css = PLAY_CSS.read_text(encoding="utf-8")

    assert 'class="npc-card"' in template
    assert 'class="npc-card-header"' in template
    assert 'class="npc-name"' in template
    assert 'class="npc-role"' in template
    assert 'class="npc-blurb"' in template
    assert 'class="npc-actions"' in template
    assert "npc-action-primary" in template
    assert "npc-action-secondary" in template

    assert 'method="post" action="/play/{{ scene.save_id }}/npcs/interact"' in template
    assert 'name="npc_id" value="{{ npc.npc_id }}"' in template
    assert 'name="action_id"' in template
    assert 'value="{{ action.id }}"' in template
    assert 'method="post" action="/play/{{ scene.save_id }}/npcs/greet"' in template

    # Primary vs secondary uses existing duration_days presentation fact only.
    assert "action.duration_days" in template
    assert "npc-action-primary" in template.split("action.duration_days", 1)[1]

    assert ".npc-card-header" in css
    assert ".npc-action-primary" in css
    assert ".npc-action-secondary" in css
    assert "@media (max-width: 560px)" in css
    assert re.search(r"@media \(max-width: 560px\)[\s\S]*\.npc-card\s*\{", css)


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
        assert "1d" in guidance_window

        # Interactions remain nested inside this NPC's article.
        assert pei_card.count("/npcs/interact") >= 3
        assert pei_card.index("npc-actions") < pei_card.index('value="inspect"')
