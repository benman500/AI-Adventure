"""Phase 2 active cultivation sessions and related cleanup."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from random import Random

from fastapi.testclient import TestClient

from ai_adventure.engine.constants import (
    ANOMALY_STATE_NONE,
    ANOMALY_STATE_TRIGGERED,
    BREAKTHROUGH_NOT_READY,
    CULTIVATION_PATH_ORDINARY,
    CULTIVATION_PROGRESS_MAX,
    PATH_STATUS_PROVISIONAL,
    STARTING_REALM_ID,
    STARTING_STAGE_ID,
)
from ai_adventure.engine.cultivation_sessions import (
    cultivation_availability,
    list_session_methods,
    run_cultivation_session,
)
from ai_adventure.engine.cultivation_state import CultivationState, cultivation_view
from ai_adventure.engine.foundation import quality_tier_from_stability, sync_foundation_quality
from ai_adventure.engine.realms import get_realm, normalize_realm_id
from ai_adventure.repositories import SaveRepository
from ai_adventure.services.cultivation import CultivationService
from tests.conftest_helpers import (
    VALID_IDENTITY_ANSWERS,
    advance_to_cultivation_hall,
    create_test_save,
    make_test_app,
)


def _state(**overrides: object) -> CultivationState:
    base = CultivationState(
        cultivation_path=CULTIVATION_PATH_ORDINARY,
        path_status=PATH_STATUS_PROVISIONAL,
        realm_id=STARTING_REALM_ID,
        stage_id=STARTING_STAGE_ID,
        body=1,
        qi=1,
        soul=1,
        dao=1,
        foundation_quality=1,
        qi_reserve_current=0,
        qi_reserve_max=10,
        cultivation_progress=0,
        realm_comprehension=0,
        foundation_stability=50,
        practice_sessions=0,
        anomaly_state=ANOMALY_STATE_NONE,
        breakthrough_readiness=BREAKTHROUGH_NOT_READY,
    )
    return replace(base, **overrides)  # type: ignore[arg-type]


def test_session_methods_are_data_driven() -> None:
    methods = list_session_methods()
    assert [m.id for m in methods] == ["cautious", "balanced", "aggressive"]
    assert all(m.description for m in methods)


def test_cautious_session_gains_and_no_setback() -> None:
    result = run_cultivation_session(_state(), "cautious", rng=Random(0))
    assert result.outcome_type == "success"
    assert result.setback is False
    assert result.qi_after == 2
    assert result.progress_after == 12
    assert result.comprehension_after == 2
    assert result.stability_after >= 51
    assert result.time_consumed_days == 1


def test_balanced_session_moderate_gains() -> None:
    result = run_cultivation_session(_state(), "balanced", rng=Random(0))
    assert result.outcome_type == "success"
    assert result.qi_after == 4
    assert result.progress_after == 25
    assert result.comprehension_after == 3
    assert result.stability_after == 50


def test_aggressive_session_high_gains_and_stability_dip() -> None:
    result = run_cultivation_session(_state(), "aggressive", rng=Random(0))
    assert result.outcome_type == "success"
    assert result.qi_after == 6
    assert result.progress_after == 35
    assert result.stability_after == 48


def test_deterministic_setback_behavior() -> None:
    result = run_cultivation_session(_state(), "aggressive", rng=Random(1))
    assert result.outcome_type == "setback"
    assert result.setback is True
    assert result.setback_description is not None
    assert result.qi_after == 3
    assert result.progress_after == 25
    assert result.stability_after == 45


def test_meter_clamping_and_qi_max() -> None:
    state = _state(
        qi_reserve_current=9,
        qi_reserve_max=10,
        cultivation_progress=98,
        realm_comprehension=99,
        foundation_stability=2,
    )
    result = run_cultivation_session(state, "aggressive", rng=Random(0))
    assert result.qi_after == 10
    assert result.progress_after == CULTIVATION_PROGRESS_MAX
    assert result.comprehension_after == 100
    assert result.stability_after == 0


def test_progress_capped_at_100_still_gains_qi() -> None:
    state = _state(cultivation_progress=100, qi_reserve_current=1)
    result = run_cultivation_session(state, "balanced", rng=Random(0))
    assert result.progress_after == 100
    assert result.qi_after == 5
    assert result.comprehension_after == 3
    assert result.state.stage_id == STARTING_STAGE_ID
    assert result.state.realm_id == STARTING_REALM_ID


def test_blocked_when_anomaly_triggered() -> None:
    state = _state(anomaly_state=ANOMALY_STATE_TRIGGERED)
    allowed, reason = cultivation_availability(state)
    assert allowed is False
    assert reason is not None
    result = run_cultivation_session(state, "cautious", rng=Random(0))
    assert result.outcome_type == "blocked"
    assert result.time_consumed_days == 0
    assert result.qi_after == 0


def test_foundation_quality_derived_from_stability_without_dropping_boundless() -> None:
    assert quality_tier_from_stability(50) == 3
    assert sync_foundation_quality(50, current_quality=5) == 5
    assert sync_foundation_quality(95, current_quality=1) == 6


def test_qi_gathering_alias_and_qi_max_from_catalog() -> None:
    assert normalize_realm_id("qi_condensation") == "qi_gathering"
    assert get_realm("qi_gathering").display_name == "Qi Gathering"
    view = cultivation_view(_state(qi_reserve_max=5))
    assert view["qi_max"] == 10


def test_cultivation_service_persists_time_and_result(tmp_path: Path) -> None:
    service = create_test_save(tmp_path, character_name="Session Tester")
    save_id = service.list_saves()[0].save_id
    advance_to_cultivation_hall(service, save_id)

    before = service.get_play_scene(save_id)
    cult = CultivationService(service._session_factory)
    result = cult.cultivate(save_id, "cautious", rng=Random(0))
    assert result.outcome_type == "success"

    after = service.get_play_scene(save_id)
    assert after.world_day == before.world_day + 1
    assert after.last_cultivation_result is not None
    assert after.last_cultivation_result["method_id"] == "cautious"
    assert after.cultivation["qi_current"] == result.qi_after
    assert after.cultivation["cultivation_progress"] == result.progress_after

    reloaded = service.get_play_scene(save_id)
    assert reloaded.cultivation["qi_current"] == result.qi_after
    assert reloaded.last_cultivation_result["method_id"] == "cautious"


def test_cultivation_ui_methods_and_disabled_states(tmp_path: Path) -> None:
    app = make_test_app(tmp_path, filename="cult_ui.db")
    client = TestClient(app)
    created = client.post(
        "/new",
        data={
            "character_name": "UI Cultivator",
            "background_id": "hunter",
            **{f"answer_{k}": v for k, v in VALID_IDENTITY_ANSWERS.items()},
        },
        follow_redirects=False,
    )
    assert created.status_code == 303
    save_id = created.headers["location"].rsplit("/", 1)[-1]

    early = client.get(f"/play/{save_id}")
    assert early.status_code == 200
    assert b'class="disclosure-label">Cultivation</span>' in early.content
    assert b'value="cautious"' not in early.content
    assert b"Cautious" not in early.content

    # Walk to hall via service sharing the same DB URL is awkward; use story actions.
    client.post(f"/play/{save_id}/action", data={"action_id": "check_snares"})
    client.post(f"/play/{save_id}/action", data={"action_id": "report_only"})
    client.post(f"/play/{save_id}/action", data={"action_id": "leave_home"})
    client.post(f"/play/{save_id}/action", data={"action_id": "continue"})
    client.post(f"/play/{save_id}/action", data={"action_id": "continue"})
    client.post(f"/play/{save_id}/action", data={"action_id": "travel_together"})
    client.post(f"/play/{save_id}/action", data={"action_id": "continue"})
    client.post(f"/play/{save_id}/action", data={"action_id": "enter"})
    client.post(f"/play/{save_id}/action", data={"action_id": "continue"})
    client.post(f"/play/{save_id}/action", data={"action_id": "continue"})
    client.post(f"/play/{save_id}/action", data={"action_id": "continue"})
    client.post(f"/play/{save_id}/action", data={"action_id": "continue"})

    hall = client.get(f"/play/{save_id}")
    assert hall.status_code == 200
    assert b'class="disclosure-label">Cultivation</span>' in hall.content
    assert b"Cautious" in hall.content
    assert b"Balanced" in hall.content
    assert b"Aggressive" in hall.content
    assert b'name="action_id"\n          value="cautious"' in hall.content or b'value="cautious"' in hall.content

    # Cultivate once and see last session block
    practiced = client.post(f"/play/{save_id}/action", data={"action_id": "cautious"})
    assert practiced.status_code == 200
    assert b"Last session" in practiced.content


def test_story_action_consumes_world_day(tmp_path: Path) -> None:
    service = create_test_save(tmp_path, character_name="Day Cost")
    save_id = service.list_saves()[0].save_id
    advance_to_cultivation_hall(service, save_id)
    before = service.get_play_scene(save_id)
    after = service.submit_story_action(save_id, "balanced")
    assert after.world_day == before.world_day + 1
    assert after.message is not None
    assert after.last_cultivation_result is not None


def test_existing_save_compatibility_legacy_realm_alias(tmp_path: Path) -> None:
    service = create_test_save(tmp_path, background_id="merchant_family", character_name="Compat")
    save_id = service.list_saves()[0].save_id
    with service._session_factory() as session:
        save = SaveRepository(session).get_with_player(save_id)
        assert save is not None and save.player is not None
        assert save.player.cultivation_rng_counter == 0
        assert save.player.last_cultivation_result_json is None
        assert save.player.qi_reserve_max == get_realm(STARTING_REALM_ID).base_qi_max
        save.player.realm_id = "qi_condensation"
        save.player.qi_reserve_max = 5
        session.commit()

    scene = service.get_play_scene(save_id)
    assert scene.cultivation["realm_id"] == "qi_gathering"
    assert scene.cultivation["qi_max"] >= get_realm("qi_gathering").base_qi_max
