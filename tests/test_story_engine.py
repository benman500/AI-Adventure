"""Story engine graph and transition tests."""

import pytest

from ai_adventure.engine import (
    EngineValidationError,
    StoryContext,
    StoryFlags,
    apply_story_action,
    clear_story_cache,
    entry_node_for_background,
    load_story_registry,
)
from ai_adventure.engine.constants import (
    ANOMALY_STATE_NONE,
    BREAKTHROUGH_NOT_READY,
    CULTIVATION_PATH_ORDINARY,
    PATH_STATUS_PROVISIONAL,
    STARTING_REALM_ID,
    STARTING_STAGE_ID,
)
from dataclasses import replace

from ai_adventure.engine.cultivation import CultivationState


def _base_cultivation(**overrides: object) -> CultivationState:
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
    return replace(base, **overrides)


def test_story_registry_loads() -> None:
    """All story JSON files validate and cross-reference."""

    clear_story_cache()
    registry = load_story_registry()
    assert "shared_cultivation_01" in registry
    assert "shared_revelation_01" in registry
    assert len(registry) >= 20


def test_background_entry_nodes() -> None:
    """Each Milestone 2 background has an opening entry."""

    assert entry_node_for_background("merchant_family") == "merchant_opening_01"
    assert entry_node_for_background("alchemists_apprentice") == "alchemist_opening_01"
    assert entry_node_for_background("hunter") == "hunter_opening_01"


def test_invalid_story_action_rejected() -> None:
    """Unknown actions fail engine validation."""

    context = StoryContext(
        background_id="hunter",
        current_node_id="hunter_opening_01",
        flags=StoryFlags(),
        cultivation=_base_cultivation(),
        world_day=1,
    )
    with pytest.raises(EngineValidationError, match="Unknown action"):
        apply_story_action(context, "teleport")


def test_merchant_opening_transitions() -> None:
    """Merchant background opening chain reaches shared pipeline."""

    context = StoryContext(
        background_id="merchant_family",
        current_node_id="merchant_opening_01",
        flags=StoryFlags(),
        cultivation=_base_cultivation(),
        world_day=1,
    )
    result = apply_story_action(context, "finish_tally")
    assert result.next_node_id == "merchant_opening_02"
    context = StoryContext(
        background_id="merchant_family",
        current_node_id=result.next_node_id,
        flags=result.flags,
        cultivation=result.cultivation,
        world_day=result.world_day,
    )
    result = apply_story_action(context, "listen_quietly")
    context = StoryContext(
        background_id="merchant_family",
        current_node_id=result.next_node_id,
        flags=result.flags,
        cultivation=result.cultivation,
        world_day=result.world_day,
    )
    result = apply_story_action(context, "leave_home")
    assert result.next_node_id == "shared_leave_home_01"


def test_cultivation_methods_only_in_cultivation_hall() -> None:
    """Cultivation methods are rejected outside allowed nodes."""

    context = StoryContext(
        background_id="hunter",
        current_node_id="hunter_opening_01",
        flags=StoryFlags(),
        cultivation=_base_cultivation(),
        world_day=1,
    )
    with pytest.raises(EngineValidationError, match="not available"):
        apply_story_action(context, "absorb_qi")
