"""HTTP route smoke tests."""

from pathlib import Path

import pytest
from httpx2 import ASGITransport, AsyncClient

from ai_adventure.api import create_app
from ai_adventure.config import Settings


@pytest.mark.asyncio
async def test_health_and_home(tmp_path: Path) -> None:
    """Routes call services; JSON and HTML both expose engine-backed data."""

    db_path = tmp_path / "http.db"
    settings = Settings(database_url=f"sqlite:///{db_path.as_posix()}")
    app = create_app(settings)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        health = await client.get("/api/health")
        assert health.status_code == 200
        payload = health.json()
        assert payload["status"] == "ok"
        assert payload["schema_marker"] == "ok"

        home = await client.get("/")
        assert home.status_code == 200
        assert b"Scaffold status" in home.content
        assert b"New Game" in home.content
        assert b"Narration" in home.content or b"Engine ready" in home.content
