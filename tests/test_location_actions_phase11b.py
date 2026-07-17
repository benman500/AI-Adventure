"""Phase 11b location-action gates, rewards, and hidden-route unlocks."""

from __future__ import annotations

import pytest

from ai_adventure.engine.location_actions import (
    LocationActionCatalog,
    LocationActionPlayerContext,
    plan_location_action,
)
from ai_adventure.engine.locations import (
    LocationCatalog,
    LocationDefinition,
    TravelEdgeDefinition,
    list_travel_destinations,
    plan_travel,
)


def test_location_action_requirements_and_rewards_are_planned() -> None:
    catalog = LocationActionCatalog.model_validate(
        {
            "schema_version": 1,
            "actions": [
                {
                    "id": "explore",
                    "label": "Duty",
                    "implemented": True,
                    "requirements": {"flags_all": ["cleared"], "min_realm_order": 2},
                    "rewards": [{"type": "grant_money", "copper_delta": 4}],
                    "presentation": {"placeholder_summary": "Done."},
                }
            ],
        }
    )
    blocked = plan_location_action(
        location_id="verdant_gate_cultivation_hall",
        action_id="explore",
        world_day=2,
        player=LocationActionPlayerContext(None, None, {}, 1, "hunter", 0),
        catalog=catalog,
    )
    assert blocked.blocked_reason == "requirements_unmet"

    allowed = plan_location_action(
        location_id="verdant_gate_cultivation_hall",
        action_id="explore",
        world_day=2,
        player=LocationActionPlayerContext(None, None, {"cleared": True}, 2, "hunter", 0),
        catalog=catalog,
    )
    assert allowed.plan is not None
    assert allowed.plan.planned_rewards[0].type == "grant_money"


def test_unknown_location_action_requirement_fails_catalog_validation() -> None:
    with pytest.raises(ValueError, match="unknown_gate"):
        LocationActionCatalog.model_validate(
            {
                "schema_version": 1,
                "actions": [
                    {
                        "id": "duty",
                        "label": "Duty",
                        "requirements": {"unknown_gate": True},
                        "presentation": {"placeholder_summary": "Done."},
                    }
                ],
            }
        )


def test_hidden_travel_route_requires_all_unlock_flags() -> None:
    catalog = LocationCatalog(
        locations=[
            LocationDefinition(
                id="origin",
                kind="site",
                display_name="Origin",
                travel=[
                    TravelEdgeDefinition(
                        to="secret",
                        visibility="hidden",
                        unlock_requirements={"flags_all": ["found_key"]},
                    )
                ],
            ),
            LocationDefinition(id="secret", kind="site", display_name="Secret"),
        ]
    )
    assert not list_travel_destinations("origin", catalog=catalog)
    assert list_travel_destinations(
        "origin", catalog=catalog, story_flags={"found_key": True}
    )
    assert (
        plan_travel(
            from_location_id="origin",
            to_location_id="secret",
            world_day=1,
            mode="travel",
            catalog=catalog,
            story_flags={"found_key": True},
        ).outcome_type
        == "success"
    )
