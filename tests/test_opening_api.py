"""HTTP tests for Milestone 3 play routes."""

from pathlib import Path

import pytest
from httpx2 import ASGITransport, AsyncClient

from tests.conftest_helpers import VALID_IDENTITY_ANSWERS, make_test_app


def _answer_form_fields() -> dict[str, str]:
    return {f"answer_{key}": value for key, value in VALID_IDENTITY_ANSWERS.items()}


@pytest.mark.asyncio
async def test_play_scene_after_create(tmp_path: Path) -> None:
    """Create game lands on opening story scene."""

    app = make_test_app(tmp_path, filename="http_m3.db")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        follow_redirects=False,
    ) as client:
        create = await client.post(
            "/new",
            data={
                "character_name": "Route Hero",
                "background_id": "hunter",
                **_answer_form_fields(),
            },
        )
        save_id = create.headers["location"].rsplit("/", 1)[-1]

        play = await client.get(f"/play/{save_id}")
        assert play.status_code == 200
        assert b"Wild Edge Dawn" in play.content
        assert b"Absorb Qi" not in play.content

        action = await client.post(
            f"/play/{save_id}/action",
            data={"action_id": "check_snares"},
        )
        assert action.status_code == 200
        assert b"Warden Shi" in action.content


@pytest.mark.asyncio
async def test_invalid_action_returns_400(tmp_path: Path) -> None:
    """Illegal actions do not bypass engine validation."""

    app = make_test_app(tmp_path, filename="http_bad_action.db")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        create = await client.post(
            "/new",
            data={
                "character_name": "Tester",
                "background_id": "hunter",
                **_answer_form_fields(),
            },
            follow_redirects=True,
        )
        assert create.status_code == 200
        save_id = str(create.url).rsplit("/", 1)[-1]

        bad = await client.post(
            f"/play/{save_id}/action",
            data={"action_id": "absorb_qi"},
        )
        assert bad.status_code == 400
