"""HTTP route smoke tests."""

from pathlib import Path

from fastapi.testclient import TestClient

from ai_adventure.api import create_app
from ai_adventure.config import Settings


def test_health_and_home(tmp_path: Path) -> None:
    """Routes call services; JSON and HTML both expose engine-backed data."""

    db_path = tmp_path / "http.db"
    settings = Settings(database_url=f"sqlite:///{db_path.as_posix()}")
    app = create_app(settings)
    client = TestClient(app)

    health = client.get("/api/health")
    assert health.status_code == 200
    payload = health.json()
    assert payload["status"] == "ok"
    assert payload["schema_marker"] == "ok"

    home = client.get("/")
    assert home.status_code == 200
    assert b"Engine outcome" in home.content
    assert b"Narration" in home.content
