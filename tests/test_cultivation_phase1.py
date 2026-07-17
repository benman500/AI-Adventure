"""Phase 1 cultivation framework tests."""

from pathlib import Path

import pytest

from ai_adventure.engine import (
    EngineValidationError,
    attempt_realm_breakthrough,
    clear_realm_catalog_cache,
    get_realm,
    list_realms,
    list_stages,
    load_realm_catalog,
)
from ai_adventure.engine.constants import (
    CULTIVATION_METHOD_ABSORB_QI,
    CULTIVATION_METHOD_STABILIZE_FOUNDATION,
    CULTIVATION_PATH_ORDINARY,
    PATH_STATUS_PROVISIONAL,
    STARTING_REALM_ID,
    STARTING_STAGE_ID,
)
from ai_adventure.engine.cultivation import (
    CultivationState,
    apply_cultivation_method,
    cultivation_view,
)
from ai_adventure.engine.realms import normalize_stage_id


def _fresh_state() -> CultivationState:
    return CultivationState(
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
        anomaly_state="none",
        breakthrough_readiness="not_ready",
    )


def test_realm_catalog_loads_playable_and_placeholders() -> None:
    """Catalog includes Body Tempering and Qi Gathering as playable."""

    clear_realm_catalog_cache()
    catalog = load_realm_catalog()
    playable = {r.id for r in catalog.realms if r.status == "playable"}
    placeholders = {r.id for r in catalog.realms if r.status == "placeholder"}
    assert playable == {"body_tempering", "qi_gathering"}
    assert "foundation_establishment" in placeholders
    assert "core_formation" in placeholders
    assert [s.id for s in list_stages()] == ["early", "middle", "late", "peak"]


def test_normalize_legacy_mid_stage() -> None:
    """Legacy mid stage maps to middle."""

    assert normalize_stage_id("mid") == "middle"
    assert normalize_stage_id("middle") == "middle"


def test_methods_raise_comprehension_and_stability() -> None:
    """Phase 1 meters change via cultivation methods."""

    state = _fresh_state()
    absorb = apply_cultivation_method(state, CULTIVATION_METHOD_ABSORB_QI)
    assert absorb.state.realm_comprehension == 2
    assert absorb.state.foundation_stability == 50

    stabilize = apply_cultivation_method(absorb.state, CULTIVATION_METHOD_STABILIZE_FOUNDATION)
    assert stabilize.state.foundation_stability == 53
    assert stabilize.state.realm_comprehension == 3


def test_realm_breakthrough_requires_peak_and_readiness() -> None:
    """Realm breakthrough is Phase 3 Peak→next; early stage is rejected."""

    with pytest.raises(EngineValidationError, match="Peak"):
        attempt_realm_breakthrough(_fresh_state())


def test_cultivation_view_exposes_phase1_fields() -> None:
    """UI view model includes the Phase 1 cultivation panel fields."""

    view = cultivation_view(_fresh_state())
    assert view["realm_name"] == "Body Tempering"
    assert view["stage_name"] == "Early"
    assert view["qi_current"] == 0
    assert view["qi_max"] == 10
    assert view["realm_comprehension"] == 0
    assert view["foundation_stability"] == 50
    assert get_realm("qi_gathering").display_name == "Qi Gathering"
    assert len(list_realms(playable_only=True)) == 2
