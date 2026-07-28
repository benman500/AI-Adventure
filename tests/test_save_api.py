"""HTTP tests for character creation and save routes."""

from pathlib import Path

import pytest
from httpx2 import ASGITransport, AsyncClient

from ai_adventure.engine.constants import DELETE_CONFIRMATION_VALUE
from tests.conftest_helpers import VALID_IDENTITY_ANSWERS, make_test_app


def _answer_form_fields() -> dict[str, str]:
    return {f"answer_{key}": value for key, value in VALID_IDENTITY_ANSWERS.items()}


@pytest.mark.asyncio
async def test_new_game_load_delete_flow(tmp_path: Path) -> None:
    """Routes create, list, load, and delete saves with confirmation."""

    app = make_test_app(tmp_path, filename="http_m2.db")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=False,
    ) as client:
        form_page = await client.get("/new")
        assert form_page.status_code == 200
        assert b"Merchant Family" in form_page.content
        assert b"Boundless Foundation" in form_page.content

        create = await client.post(
            "/new",
            data={
                "character_name": "Route Hero",
                "background_id": "hunter",
                **_answer_form_fields(),
            },
        )
        assert create.status_code == 303
        location = create.headers["location"]
        assert location.startswith("/play/")

        saves = await client.get("/saves")
        assert saves.status_code == 200
        assert b"Route Hero" in saves.content

        save_id = location.rsplit("/", 1)[-1]
        loaded = await client.post(f"/saves/{save_id}/load")
        assert loaded.status_code == 303

        play = await client.get(f"/play/{save_id}")
        assert play.status_code == 200
        assert b"Route Hero" in play.content
        assert b"ordinary" in play.content

        confirm = await client.get(f"/saves/{save_id}/delete")
        assert confirm.status_code == 200
        assert b"DELETE" in confirm.content

        bad_delete = await client.post(
            f"/saves/{save_id}/delete",
            data={"confirmation": "wrong"},
        )
        assert bad_delete.status_code == 400

        good_delete = await client.post(
            f"/saves/{save_id}/delete",
            data={"confirmation": DELETE_CONFIRMATION_VALUE},
        )
        assert good_delete.status_code == 303

        saves_after = await client.get("/saves")
        assert b"Route Hero" not in saves_after.content


@pytest.mark.asyncio
async def test_invalid_background_via_route(tmp_path: Path) -> None:
    """Invalid background produces a 400 on the creation form."""

    app = make_test_app(tmp_path, filename="http_bad.db")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/new",
            data={
                "character_name": "No Path",
                "background_id": "fake_class",
                **_answer_form_fields(),
            },
        )
        assert response.status_code == 400
        assert b"Unknown background" in response.content
