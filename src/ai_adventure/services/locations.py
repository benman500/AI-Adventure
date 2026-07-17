"""Application service for location changes, travel, and WorldClock advances.

All location mutations and simulation-day deltas from play actions should go
through this service so story travel and free travel cannot diverge.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from ai_adventure.db.models import GameSave, Player, StoryProgress
from ai_adventure.engine.constants import EVENT_TYPE_LOCATION_ACTION, EVENT_TYPE_TRAVEL_RESOLVED
from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.location_actions import (
    AvailableLocationAction,
    LocationActionResolution,
    list_available_location_actions,
    plan_location_action,
)
from ai_adventure.engine.locations import (
    TravelResolution,
    plan_travel,
    resolve_location_display_name,
)
from ai_adventure.repositories.locations import LocationPresenceRepository
from ai_adventure.repositories.saves import SaveRepository


@dataclass(frozen=True, slots=True)
class LocationChangeResult:
    """Persisted location / clock outcome inside an open transaction."""

    resolution: TravelResolution
    presentation_message: str | None
    event_message: str | None
    world_day: int
    location_id: str
    location_name: str


@dataclass(frozen=True, slots=True)
class LocationActionResult:
    """Persisted location-action outcome inside an open transaction."""

    resolution: LocationActionResolution
    presentation_message: str | None
    event_message: str | None
    world_day: int
    location_id: str
    action_id: str


class LocationService:
    """Orchestrates travel, location actions, and WorldClock advances (no HTTP, no AI).

    Must be used inside an open SQLAlchemy session that the caller commits or
    rolls back. Failed validation raises before mutating state. Event hook
    failures abort the same transaction when the caller does not catch them.
    """

    def __init__(self, session: Session) -> None:
        self._session = session
        self._saves = SaveRepository(session)
        self._presence = LocationPresenceRepository(session)

    def list_actions_for_player(self, player: Player) -> list[AvailableLocationAction]:
        """Return actions offered at the player's current location."""

        return list_available_location_actions(str(player.current_location_id))

    def perform_action(
        self,
        *,
        save: GameSave,
        player: Player,
        progress: StoryProgress | None,
        action_id: str,
    ) -> LocationActionResult:
        """Run a location action: validate → clock → events → persist facts."""

        resolution = plan_location_action(
            location_id=str(player.current_location_id),
            action_id=action_id,
            world_day=int(save.world_day),
        )
        if resolution.outcome_type == "blocked" or resolution.plan is None:
            raise EngineValidationError(
                resolution.summary
                if resolution.blocked_reason is None
                else f"{resolution.summary} ({resolution.blocked_reason})"
            )

        plan = resolution.plan
        if plan.duration_days:
            self.advance_world_days(save, plan.duration_days)

        payload = dict(resolution.event_payload or {})
        payload["world_day"] = int(save.world_day)
        self._saves.append_event(
            save.id,
            event_type=EVENT_TYPE_LOCATION_ACTION,
            payload=payload,
        )

        event_message: str | None = None
        if plan.trigger_kind == "after_explore":
            from ai_adventure.services.events import EventService

            event_message = EventService(self._session).run_after_explore(
                save=save,
                player=player,
                progress=progress,
            ).presentation_message
        elif plan.trigger_kind == "after_inspect":
            from ai_adventure.services.events import EventService

            event_message = EventService(self._session).run_after_inspect(
                save=save,
                player=player,
                progress=progress,
            ).presentation_message
        elif plan.trigger_kind is not None:
            from ai_adventure.services.events import EventService

            event_message = EventService(self._session).run_trigger(
                save=save,
                player=player,
                progress=progress,
                trigger_kind=plan.trigger_kind,
                action_id=plan.action_id,
            ).presentation_message

        return LocationActionResult(
            resolution=resolution,
            presentation_message=resolution.summary,
            event_message=event_message,
            world_day=int(save.world_day),
            location_id=str(player.current_location_id),
            action_id=plan.action_id,
        )

    def advance_world_days(self, save: GameSave, days: int) -> int:
        """Advance the simulation clock via WorldClock helpers only."""

        if days == 0:
            return int(save.world_day)
        return self._saves.advance_world_day(save, days)

    def establish_starting_presence(
        self,
        save: GameSave,
        player: Player,
        location_id: str,
    ) -> None:
        """Record initial presence for character creation (no travel event)."""

        name = resolve_location_display_name(location_id)
        self._saves.update_locations(
            save,
            player,
            location_id=location_id,
            location_name=name,
        )
        self._presence.record_visit(save.id, location_id, int(save.world_day))

    def apply_story_transition(
        self,
        *,
        save: GameSave,
        player: Player,
        progress: StoryProgress | None,
        result_location_id: str | None,
        result_world_day: int,
    ) -> LocationChangeResult | None:
        """Apply story-authored location and/or day changes through this service.

        Returns ``None`` when the story transition did not touch location or day.
        """

        current_day = int(save.world_day)
        current_location = str(player.current_location_id)
        target_day = int(result_world_day)
        if target_day < current_day:
            raise EngineValidationError("Story cannot reverse the world clock")

        day_delta = target_day - current_day
        if result_location_id:
            if result_location_id == current_location:
                if day_delta:
                    new_day = self.advance_world_days(save, day_delta)
                    return LocationChangeResult(
                        resolution=TravelResolution(
                            outcome_type="success",
                            plan=None,
                            summary=f"Advanced {day_delta} world day(s).",
                        ),
                        presentation_message=None,
                        event_message=None,
                        world_day=new_day,
                        location_id=current_location,
                        location_name=str(player.current_location_name),
                    )
                return None
            return self.relocate(
                save=save,
                player=player,
                progress=progress,
                to_location_id=result_location_id,
                mode="story",
                days_override=day_delta,
            )

        if day_delta:
            new_day = self.advance_world_days(save, day_delta)
            return LocationChangeResult(
                resolution=TravelResolution(
                    outcome_type="success",
                    plan=None,
                    summary=f"Advanced {day_delta} world day(s).",
                ),
                presentation_message=None,
                event_message=None,
                world_day=new_day,
                location_id=current_location,
                location_name=str(player.current_location_name),
            )
        return None

    def travel(
        self,
        *,
        save: GameSave,
        player: Player,
        progress: StoryProgress | None,
        to_location_id: str,
        days_override: int | None = None,
    ) -> LocationChangeResult:
        """First-class free travel intent (requires catalog edge)."""

        return self.relocate(
            save=save,
            player=player,
            progress=progress,
            to_location_id=to_location_id,
            mode="travel",
            days_override=days_override,
        )

    def relocate(
        self,
        *,
        save: GameSave,
        player: Player,
        progress: StoryProgress | None,
        to_location_id: str,
        mode: str,
        days_override: int | None = None,
        fire_events: bool | None = None,
    ) -> LocationChangeResult:
        """Validate, advance time, update presence, optionally fire travel events."""

        if mode not in {"travel", "story"}:
            raise EngineValidationError(f"Unknown travel mode: {mode}")

        resolution = plan_travel(
            from_location_id=str(player.current_location_id),
            to_location_id=to_location_id,
            world_day=int(save.world_day),
            mode=mode,  # type: ignore[arg-type]
            days_override=days_override,
        )
        if resolution.outcome_type == "blocked":
            raise EngineValidationError(
                resolution.summary
                if resolution.blocked_reason is None
                else f"{resolution.summary} ({resolution.blocked_reason})"
            )
        if resolution.outcome_type == "noop" or resolution.plan is None:
            return LocationChangeResult(
                resolution=resolution,
                presentation_message=resolution.summary,
                event_message=None,
                world_day=int(save.world_day),
                location_id=str(player.current_location_id),
                location_name=str(player.current_location_name),
            )

        plan = resolution.plan
        if plan.days:
            self.advance_world_days(save, plan.days)
        elif int(save.world_day) != plan.world_day_after:
            # Absolute sync only when pure planner already computed via WorldClock.
            self._saves.set_world_day(save, plan.world_day_after)

        self._saves.update_locations(
            save,
            player,
            location_id=plan.to_location_id,
            location_name=plan.to_display_name,
        )
        self._presence.record_visit(save.id, plan.to_location_id, int(save.world_day))

        payload = dict(resolution.event_payload or {})
        payload["world_day"] = int(save.world_day)
        self._saves.append_event(
            save.id,
            event_type=EVENT_TYPE_TRAVEL_RESOLVED,
            payload=payload,
        )

        should_fire = plan.fire_travel_events if fire_events is None else fire_events
        event_message: str | None = None
        if should_fire:
            from ai_adventure.services.events import EventService

            event_outcome = EventService(self._session).run_after_story_travel(
                save=save,
                player=player,
                progress=progress,
            )
            event_message = event_outcome.presentation_message

        return LocationChangeResult(
            resolution=resolution,
            presentation_message=resolution.summary,
            event_message=event_message,
            world_day=int(save.world_day),
            location_id=plan.to_location_id,
            location_name=plan.to_display_name,
        )

    def travel_for_save(
        self,
        save_id: str,
        to_location_id: str,
    ) -> dict[str, Any]:
        """Convenience API for callers that own the session commit boundary."""

        save = self._saves.get_with_player(save_id)
        if save is None or save.player is None:
            raise EngineValidationError("Save not found")
        result = self.travel(
            save=save,
            player=save.player,
            progress=save.story_progress,
            to_location_id=to_location_id,
        )
        return {
            "outcome_type": result.resolution.outcome_type,
            "summary": result.resolution.summary,
            "world_day": result.world_day,
            "location_id": result.location_id,
            "location_name": result.location_name,
            "event_message": result.event_message,
        }
