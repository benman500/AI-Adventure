"""HTTP route smoke tests."""

from pathlib import Path

import pytest
from httpx2 import ASGITransport, AsyncClient

from tests.conftest_helpers import make_test_app


@pytest.mark.asyncio
async def test_health_and_home(tmp_path: Path) -> None:
    """Routes call services; JSON and HTML both expose engine-backed data."""

    app = make_test_app(tmp_path, filename="http.db")

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
        assert b"New Game" in home.content
        assert b"Load Saves" in home.content
        assert b"cultivation" in home.content.lower()
