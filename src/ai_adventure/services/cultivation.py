"""Active cultivation sessions and related persistence orchestration."""

from __future__ import annotations

import json
from random import Random
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from ai_adventure.engine.cultivation_sessions import (
    CultivationSessionResult,
    cultivation_availability,
    list_session_methods,
    run_cultivation_session,
    session_result_to_dict,
)
from ai_adventure.engine.cultivation_state import cultivation_state_from_player
from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.story import get_story_node, node_allows_cultivation
from ai_adventure.repositories import SaveRepository


class CultivationService:
    """Application service for active cultivation sessions.

    Routes and GameAppService call this instead of embedding cultivation math.
    Story-hall cultivation still goes through ``apply_story_action``; this
    service is the reusable persistence path for session-centric callers.
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_methods_for_ui(self) -> list[dict[str, Any]]:
        """Return method cards for the cultivation panel."""

        return [
            {
                "id": method.id,
                "label": method.label,
                "description": method.description,
                "risk_level": method.risk_level,
                "time_cost_days": method.time_cost_days,
            }
            for method in list_session_methods()
        ]

    def availability_for_save(self, save_id: str) -> tuple[bool, str | None]:
        """Whether the save may cultivate right now (state gates only)."""

        with self._session_factory() as session:
            save = SaveRepository(session).get_with_player(save_id)
            if save is None or save.player is None:
                raise EngineValidationError("Save not found")
            state = cultivation_state_from_player(save.player)
            return cultivation_availability(state)

    def cultivate(
        self,
        save_id: str,
        method_id: str,
        *,
        rng: Random | None = None,
        require_story_hall: bool = True,
    ) -> CultivationSessionResult:
        """Run one cultivation session, persist meters/time/result, return outcome."""

        with self._session_factory() as session:
            save_repo = SaveRepository(session)
            save = save_repo.get_with_player(save_id)
            if save is None or save.player is None:
                raise EngineValidationError("Save not found")
            if save.story_progress is None:
                raise EngineValidationError("Story progress not initialized")

            if require_story_hall:
                node = get_story_node(save.story_progress.current_node_id)
                if not node_allows_cultivation(node):
                    raise EngineValidationError("Cultivation is not available at this story beat")

            player = save.player
            state = cultivation_state_from_player(player)

            if rng is None:
                counter = getattr(player, "cultivation_rng_counter", 0) or 0
                seed = (hash(save_id) & 0xFFFFFFFF) ^ (counter * 2654435761)
                rng = Random(seed)

            from ai_adventure.services.techniques import build_cultivate_session_snapshot

            modifiers = build_cultivate_session_snapshot(
                session,
                save_id=save.id,
                actor_id=player.actor_id,
                world_day=save.world_day,
            )
            result = run_cultivation_session(state, method_id, rng=rng, modifiers=modifiers)
            if result.outcome_type == "blocked":
                session.commit()
                return result

            save_repo.apply_player_cultivation(player, result.state)
            player.cultivation_rng_counter = (getattr(player, "cultivation_rng_counter", 0) or 0) + 1
            player.last_cultivation_result_json = json.dumps(
                session_result_to_dict(result),
                sort_keys=True,
            )
            if result.time_consumed_days:
                save_repo.advance_world_day(save, result.time_consumed_days)
            if result.playtime_seconds:
                save_repo.add_playtime(save, result.playtime_seconds)

            for event in result.events:
                save_repo.append_event(
                    save.id,
                    event_type=event.event_type,
                    payload=dict(event.payload),
                )

            from ai_adventure.services.events import EventService

            EventService(session).run_after_cultivation_session(
                save=save,
                player=player,
                progress=save.story_progress,
                cultivation=result.state,
            )

            save_repo.touch_last_played(save)
            session.commit()
            return result

    def attempt_breakthrough(
        self,
        save_id: str,
        *,
        rng: Random | None = None,
    ):
        """Attempt a breakthrough through the story hall gate + engine."""

        from ai_adventure.engine.cultivation_path import attempt_breakthrough as path_attempt
        from ai_adventure.engine.breakthroughs import (
            breakthrough_result_to_dict,
            run_breakthrough_attempt,
        )
        from ai_adventure.engine.constants import PATH_STATUS_PROVISIONAL
        from ai_adventure.engine.story import get_story_node, node_allows_cultivation

        with self._session_factory() as session:
            save_repo = SaveRepository(session)
            save = save_repo.get_with_player(save_id)
            if save is None or save.player is None:
                raise EngineValidationError("Save not found")
            if save.story_progress is None:
                raise EngineValidationError("Story progress not initialized")

            node = get_story_node(save.story_progress.current_node_id)
            if not node_allows_cultivation(node):
                raise EngineValidationError("Breakthrough cannot be attempted here")

            player = save.player
            state = cultivation_state_from_player(player)

            if state.path_status == PATH_STATUS_PROVISIONAL:
                path_result = path_attempt(state)
                save_repo.apply_player_cultivation(player, path_result.state)
                player.last_breakthrough_result_json = json.dumps(
                    {
                        "outcome_type": "opening_anomaly",
                        "success": False,
                        "summary": path_result.summary,
                    },
                    sort_keys=True,
                )
                for event in path_result.events:
                    save_repo.append_event(
                        save.id,
                        event_type=event.event_type,
                        payload=dict(event.payload),
                    )
                save_repo.touch_last_played(save)
                session.commit()
                return path_result

            if rng is None:
                counter = getattr(player, "breakthrough_attempts_current_stage", 0) or 0
                seed = (hash(save_id) & 0xFFFFFFFF) ^ (counter * 2654435761)
                rng = Random(seed)

            from ai_adventure.services.techniques import build_breakthrough_snapshot

            modifiers = build_breakthrough_snapshot(
                session,
                save_id=save.id,
                actor_id=player.actor_id,
                world_day=save.world_day,
            )
            result = run_breakthrough_attempt(state, rng=rng, modifiers=modifiers)
            if result.outcome_type == "blocked":
                raise EngineValidationError(result.blocked_reason or "Breakthrough blocked")

            save_repo.apply_player_cultivation(player, result.state)
            player.last_breakthrough_result_json = json.dumps(
                breakthrough_result_to_dict(result),
                sort_keys=True,
            )
            for event in result.events:
                save_repo.append_event(
                    save.id,
                    event_type=event.event_type,
                    payload=dict(event.payload),
                )
            save_repo.touch_last_played(save)
            session.commit()
            return result
