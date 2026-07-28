"""Presentation checks for travel destination cards (UI-only)."""

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


def test_travel_destination_template_hierarchy_and_form_contracts() -> None:
    """Template keeps destination hierarchy and travel form contracts."""

    template = PLAY_SCENE_TEMPLATE.read_text(encoding="utf-8")
    css = PLAY_CSS.read_text(encoding="utf-8")

    assert 'class="travel-list"' in template
    assert "travel-destination--current" in template
    assert "travel-destination--available" in template
    assert "travel-destination--unavailable" not in template
    assert 'class="travel-destination-header"' in template
    assert 'class="travel-name"' in template
    assert 'class="travel-blurb"' in template
    assert 'class="travel-status"' in template
    assert 'class="travel-meta"' in template
    assert "{{ dest.days }}d" in template
    assert "travel-action-primary" in template
    assert 'class="travel-action-label"' in template
    assert 'class="travel-action-meta"' in template

    assert 'method="post" action="/play/{{ scene.save_id }}/travel"' in template
    assert 'name="to_location_id"' in template
    assert 'value="{{ dest.location_id }}"' in template

    # Descriptive context uses supplied fields only (no invented flavor strings).
    assert "dest.ambience" in template
    assert "dest.environment_tags" in template
    assert "dest.tags" in template
    assert "dest.kind" in template
    assert "Current location" not in template
    assert "Medicinal herbs and quiet paths." not in template
    assert "The heart of instruction." not in template

    assert ".travel-destination--current" in css
    assert ".travel-destination--available" in css
    assert ".travel-destination--unavailable" not in css
    assert ".travel-action-primary" in css
    assert ".travel-action-label" in css
    assert ".travel-actions" in css
    assert "@media (max-width: 560px)" in css
    assert re.search(
        r"@media \(max-width: 560px\)[\s\S]*\.travel-destination\s*\{",
        css,
    )
    assert re.search(
        r"@media \(max-width: 560px\)[\s\S]*\.travel-action-primary\s*\{",
        css,
    )


@pytest.mark.asyncio
async def test_travel_destinations_render_current_and_available_cards(
    tmp_path: Path,
) -> None:
    """Rendered travel list distinguishes current location from open routes."""

    app = make_test_app(tmp_path, filename="travel_destinations_ui.db")
    db_path = tmp_path / "travel_destinations_ui.db"
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
                "character_name": "Travel Card Hero",
                "background_id": "merchant_family",
                **_answer_form_fields(),
            },
        )
        assert create.status_code == 303
        save_id = create.headers["location"].rsplit("/", 1)[-1]

        advance_to_cultivation_hall(service, save_id)
        scene = service.get_play_scene(save_id)
        assert scene.travel_destinations

        play = await client.get(f"/play/{save_id}")
        assert play.status_code == 200
        html = play.text

        assert 'aria-label="Travel"' in html
        assert 'class="travel-list"' in html
        assert "travel-destination--current" in html
        assert 'aria-current="location"' in html
        assert "You are here" in html
        assert scene.current_location_name in html
        assert "travel-destination--unavailable" not in html

        assert "travel-destination--available" in html
        assert "Open route" in html
        assert "travel-action-primary" in html
        assert "travel-action-label" in html
        assert f'action="/play/{save_id}/travel"' in html
        assert 'name="to_location_id"' in html

        first = scene.travel_destinations[0]
        assert f'data-location-id="{first["location_id"]}"' in html
        assert f'value="{first["location_id"]}"' in html
        assert first["display_name"] in html
        assert f'{first["days"]}d' in html

        # Descriptive context comes only from view-model fields already supplied.
        if first.get("ambience"):
            assert str(first["ambience"]) in html
        elif first.get("environment_tags"):
            for tag in first["environment_tags"]:
                assert tag.replace("_", " ") in html

        # Each available destination keeps an independent travel submit control.
        assert html.count('name="to_location_id"') == len(scene.travel_destinations)
        assert html.count("travel-action-primary") == len(scene.travel_destinations)

        current_idx = html.index("travel-destination--current")
        available_idx = html.index("travel-destination--available")
        assert current_idx < available_idx
