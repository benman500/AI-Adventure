"""Opening story integration and persistence tests."""

from pathlib import Path

import pytest

from ai_adventure.engine.constants import (
    EVENT_TYPE_CULTIVATION_ANOMALY,
    EVENT_TYPE_PATH_CHOICE_BOUNDLESS,
    EVENT_TYPE_PATH_CHOICE_ORDINARY,
    PATH_STATUS_CONFIRMED_ORDINARY,
)
from ai_adventure.repositories import SaveRepository, StoryRepository
from tests.conftest_helpers import (
    advance_to_cultivation_hall,
    build_breakthrough_readiness,
    create_test_save,
    make_service,
)


def test_load_m2_character_into_opening(tmp_path: Path) -> None:
    """Existing-style save bootstraps into background opening."""

    service = create_test_save(tmp_path, background_id="merchant_family")
    save_id = service.list_saves()[0].save_id
    scene = service.get_play_scene(save_id)
    assert scene.node_id == "merchant_opening_01"
    assert "Willowford" in scene.narrative or "market" in scene.narrative.lower()


@pytest.mark.parametrize("background_id", ["merchant_family", "alchemists_apprentice", "hunter"])
def test_each_background_reaches_cultivation_hall(tmp_path: Path, background_id: str) -> None:
    """All backgrounds converge on the shared cultivation hall."""

    service = create_test_save(tmp_path, background_id=background_id)
    save_id = service.list_saves()[0].save_id
    advance_to_cultivation_hall(service, save_id)
    scene = service.get_play_scene(save_id)
    assert scene.node_id == "shared_cultivation_01"
    assert len(scene.cultivation_methods) == 3


def test_anomaly_after_breakthrough_attempt_not_session_count(tmp_path: Path) -> None:
    """Anomaly follows breakthrough attempt when thresholds are met."""

    service = create_test_save(tmp_path)
    save_id = service.list_saves()[0].save_id
    build_breakthrough_readiness(service, save_id)

    scene = service.submit_story_action(save_id, "attempt_breakthrough")
    assert scene.cultivation["anomaly_state"] == "triggered"
    assert scene.node_id == "shared_anomaly_01"

    events = service.list_events_for_save(save_id)
    types = {e["event_type"] for e in events}
    assert EVENT_TYPE_CULTIVATION_ANOMALY in types


def test_investigation_before_elder_yun(tmp_path: Path) -> None:
    """Investigation scenes occur before revelation."""

    service = create_test_save(tmp_path)
    save_id = service.list_saves()[0].save_id
    build_breakthrough_readiness(service, save_id)
    service.submit_story_action(save_id, "attempt_breakthrough")
    service.submit_story_action(save_id, "report")
    scene = service.get_play_scene(save_id)
    assert scene.node_id == "shared_investigation_01"

    service.submit_story_action(save_id, "continue")
    service.submit_story_action(save_id, "continue")
    service.submit_story_action(save_id, "continue")
    scene = service.get_play_scene(save_id)
    assert scene.node_id == "shared_mystery_01"

    service.submit_story_action(save_id, "go")
    scene = service.get_play_scene(save_id)
    assert scene.node_id == "shared_revelation_01"
    assert "ancient" in scene.narrative.lower()
    assert "abandoned" in scene.narrative.lower()


def test_ordinary_path_selection(tmp_path: Path) -> None:
    """Ordinary path confirms and demonstrates viable progression."""

    service = create_test_save(tmp_path)
    save_id = service.list_saves()[0].save_id
    _reach_choice(service, save_id)
    scene = service.submit_story_action(save_id, "choose_ordinary")
    assert scene.cultivation["path_status"] == PATH_STATUS_CONFIRMED_ORDINARY
    assert scene.cultivation["stage_id"] == "middle"

    events = service.list_events_for_save(save_id)
    assert any(e["event_type"] == EVENT_TYPE_PATH_CHOICE_ORDINARY for e in events)


def test_boundless_path_selection(tmp_path: Path) -> None:
    """Boundless path confirms without immediate overpowered advancement."""

    service = create_test_save(tmp_path)
    save_id = service.list_saves()[0].save_id
    _reach_choice(service, save_id)
    scene = service.submit_story_action(save_id, "choose_boundless")
    assert scene.cultivation["path_status"] == "confirmed_boundless"
    assert scene.cultivation["stage_id"] == "early"

    events = service.list_events_for_save(save_id)
    assert any(e["event_type"] == EVENT_TYPE_PATH_CHOICE_BOUNDLESS for e in events)


def test_path_change_blocked_after_confirmation(tmp_path: Path) -> None:
    """Cannot select a second path after confirmation."""

    service = create_test_save(tmp_path)
    save_id = service.list_saves()[0].save_id
    _reach_choice(service, save_id)
    service.submit_story_action(save_id, "choose_ordinary")
    service.submit_story_action(save_id, "continue")
    scene = service.get_play_scene(save_id)
    assert scene.node_id == "shared_post_ordinary_02"


def test_save_reload_at_checkpoints(tmp_path: Path) -> None:
    """Story node and cultivation state survive reload."""

    service = create_test_save(tmp_path)
    save_id = service.list_saves()[0].save_id
    build_breakthrough_readiness(service, save_id)
    service.submit_story_action(save_id, "attempt_breakthrough")

    reloaded = service.get_play_scene(save_id)
    assert reloaded.node_id == "shared_anomaly_01"
    assert reloaded.cultivation["anomaly_state"] == "triggered"

    factory = service._session_factory  # noqa: SLF001
    with factory() as session:
        progress = StoryRepository(session).get_for_save(save_id)
        assert progress is not None
        assert progress.current_node_id == "shared_anomaly_01"


def test_story_persistence_in_database(tmp_path: Path) -> None:
    """Story progress row stores authoritative node id."""

    service = create_test_save(tmp_path, background_id="hunter")
    save_id = service.list_saves()[0].save_id
    service.get_play_scene(save_id)

    factory = service._session_factory  # noqa: SLF001
    with factory() as session:
        save = SaveRepository(session).get_with_player(save_id)
        assert save is not None
        assert save.story_progress is not None
        assert save.story_progress.current_node_id == "hunter_opening_01"


def _reach_choice(service: object, save_id: str) -> None:
    build_breakthrough_readiness(service, save_id)
    service.submit_story_action(save_id, "attempt_breakthrough")
    service.submit_story_action(save_id, "report")
    service.submit_story_action(save_id, "continue")
    service.submit_story_action(save_id, "continue")
    service.submit_story_action(save_id, "continue")
    service.submit_story_action(save_id, "go")
    service.submit_story_action(save_id, "continue")
