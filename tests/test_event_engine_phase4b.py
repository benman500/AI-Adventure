"""Phase 4b: live cultivation-session event hook, persistence, seeds."""

from __future__ import annotations

import json
from pathlib import Path
from random import Random

import pytest

from ai_adventure.engine.constants import (
    EVENT_TYPE_WORLD_EVENT_RESOLVED,
    PATH_STATUS_CONFIRMED_ORDINARY,
    PATH_STATUS_PROVISIONAL,
)
from ai_adventure.engine.events import clear_event_catalog_cache, load_event_catalog
from ai_adventure.repositories.events import EventCooldownRepository
from ai_adventure.repositories.saves import EventLogRepository, SaveRepository
from ai_adventure.services.cultivation import CultivationService
from ai_adventure.services.events import EventService
from tests.conftest_helpers import (
    build_breakthrough_readiness,
    create_test_save,
)


def _reach_confirmed_ordinary(service: object, save_id: str) -> None:
    build_breakthrough_readiness(service, save_id)
    service.submit_story_action(save_id, "attempt_breakthrough")
    service.submit_story_action(save_id, "report")
    service.submit_story_action(save_id, "continue")
    service.submit_story_action(save_id, "continue")
    service.submit_story_action(save_id, "continue")
    service.submit_story_action(save_id, "go")
    service.submit_story_action(save_id, "continue")
    scene = service.submit_story_action(save_id, "choose_ordinary")
    assert scene.cultivation["path_status"] == PATH_STATUS_CONFIRMED_ORDINARY
    service.submit_story_action(save_id, "continue")


def test_seed_catalog_shape() -> None:
    clear_event_catalog_cache()
    catalog = load_event_catalog()
    by_id = {e.id: e for e in catalog.events}
    assert "evt_quiet_breath_insight" in by_id
    assert "evt_meridian_warmth" in by_id
    assert "evt_sect_courtyard_focus" in by_id
    assert "evt_distracted_circulation" in by_id
    assert "evt_dawn_qi_clarity" in by_id
    assert "evt_discovery_jade_chip" in by_id
    stub = by_id["evt_exploration_stub_ridge_path"]
    assert stub.trigger.kinds == ["after_story_travel"]
    assert stub.ai_prompt_key == "evt_exploration_stub_ridge_path"
    assert stub.context.location_tags == ["jade_ridge"]
    for event in catalog.events:
        assert event.context is not None
        assert hasattr(event, "ai_prompt_key")


def test_provisional_session_does_not_fire_seed_events(tmp_path: Path) -> None:
    service = create_test_save(tmp_path)
    save_id = service.list_saves()[0].save_id
    from tests.conftest_helpers import advance_to_cultivation_hall

    advance_to_cultivation_hall(service, save_id)
    scene = service.get_play_scene(save_id)
    assert scene.cultivation["path_status"] == PATH_STATUS_PROVISIONAL

    before = service.list_events_for_save(save_id)
    service.submit_story_action(save_id, "cautious")
    after = service.list_events_for_save(save_id)
    before_world = [
        e for e in before if e["event_type"] == EVENT_TYPE_WORLD_EVENT_RESOLVED
    ]
    after_world = [
        e for e in after if e["event_type"] == EVENT_TYPE_WORLD_EVENT_RESOLVED
    ]
    # Provisional path must not add session seed events (travel may already
    # have logged unrelated world_event_resolved rows during the opening).
    assert len(after_world) == len(before_world)
    # RNG counter still advances on evaluation attempt.
    with service._session_factory() as session:  # noqa: SLF001
        save = SaveRepository(session).get_with_player(save_id)
        assert save is not None
        assert save.world_rng_counter >= 1
    assert len(after) >= len(before)


def test_confirmed_session_can_fire_and_persist_event(tmp_path: Path) -> None:
    service = create_test_save(tmp_path)
    save_id = service.list_saves()[0].save_id
    _reach_confirmed_ordinary(service, save_id)

    # Force a hit via EventService with chance-guaranteed RNG + production catalog
    # filtered by using Random that always activates (random() -> 0.0).
    class AlwaysActivate(Random):
        def random(self) -> float:  # noqa: A003
            return 0.0

    with service._session_factory() as session:  # noqa: SLF001
        save = SaveRepository(session).get_with_player(save_id)
        assert save is not None and save.player is not None
        comprehension_before = int(save.player.realm_comprehension)
        progress_before = int(save.player.cultivation_progress)
        stability_before = int(save.player.foundation_stability)
        qi_before = int(save.player.qi_reserve_current)
        counter_before = save.world_rng_counter
        cool_before = {
            row.event_template_id: int(row.fire_count)
            for row in EventCooldownRepository(session).list_for_save(save_id)
        }
        world_events_before = {
            e.id
            for e in EventLogRepository(session).list_for_save(save_id)
            if e.event_type == EVENT_TYPE_WORLD_EVENT_RESOLVED
        }
        outcome = EventService(session).run_after_cultivation_session(
            save=save,
            player=save.player,
            progress=save.story_progress,
            rng=AlwaysActivate(1),
        )
        session.commit()
        assert outcome.fired is True
        assert outcome.presentation_message
        assert (
            save.player.realm_comprehension != comprehension_before
            or save.player.cultivation_progress != progress_before
            or save.player.foundation_stability != stability_before
            or save.player.qi_reserve_current != qi_before
        )
        assert save.world_rng_counter == counter_before + 1

        cool = EventCooldownRepository(session).list_for_save(save_id)
        cool_after = {row.event_template_id: int(row.fire_count) for row in cool}
        assert len(cool_after) >= len(cool_before) + 1 or any(
            cool_after.get(k, 0) > cool_before.get(k, 0) for k in cool_after
        )

        logs = EventLogRepository(session).list_for_save(save_id)
        world_events = [e for e in logs if e.event_type == EVENT_TYPE_WORLD_EVENT_RESOLVED]
        new_world_events = [e for e in world_events if e.id not in world_events_before]
        assert len(new_world_events) == 1
        payload = json.loads(new_world_events[0].payload_json)
        assert payload["event_template_id"]
        assert payload["presentation_authoritative"] is False
        assert "effects_applied" in payload
        assert "ai_prompt_key" in payload
        assert "context" in payload


def test_story_cultivation_hook_appends_message_when_event_fires(tmp_path: Path) -> None:
    service = create_test_save(tmp_path)
    save_id = service.list_saves()[0].save_id
    _reach_confirmed_ordinary(service, save_id)

    # Monkeypatch EventService to force a known presentation message.
    from ai_adventure.services import events as events_mod
    from ai_adventure.engine.events import EventTriggerBatch, EventSlotOutcome, NoEventResult
    from ai_adventure.services.events import PersistedTriggerResult

    original = events_mod.EventService.run_after_cultivation_session

    def forced(self, **kwargs):  # noqa: ANN001
        return PersistedTriggerResult(
            batch=EventTriggerBatch(
                trigger_kind="after_cultivation_session",
                max_events=1,
                slots=(
                    EventSlotOutcome(
                        kind="no_event",
                        no_event=NoEventResult(
                            reason="chance_missed",
                            trigger_kind="after_cultivation_session",
                        ),
                    ),
                ),
            ),
            presentation_message="FORCED_EVENT_TEXT",
            fired=True,
        )

    events_mod.EventService.run_after_cultivation_session = forced  # type: ignore[method-assign]
    try:
        scene = service.submit_story_action(save_id, "cautious")
        assert scene.message is not None
        assert "FORCED_EVENT_TEXT" in scene.message
    finally:
        events_mod.EventService.run_after_cultivation_session = original  # type: ignore[method-assign]


def test_event_failure_rolls_back_with_session(tmp_path: Path) -> None:
    service = create_test_save(tmp_path)
    save_id = service.list_saves()[0].save_id
    _reach_confirmed_ordinary(service, save_id)

    class Boom(Random):
        def random(self) -> float:  # noqa: A003
            return 0.0

    with service._session_factory() as session:  # noqa: SLF001
        save = SaveRepository(session).get_with_player(save_id)
        assert save is not None and save.player is not None
        day_before = save.world_day
        qi_before = save.player.qi_reserve_current
        counter_before = save.world_rng_counter
        cool_before = {
            (row.event_template_id, row.subject_actor_id, row.fire_count, row.last_fired_world_day)
            for row in EventCooldownRepository(session).list_for_save(save_id)
        }
        world_events_before = {
            e.id
            for e in EventLogRepository(session).list_for_save(save_id)
            if e.event_type == EVENT_TYPE_WORLD_EVENT_RESOLVED
        }

        svc = EventService(session)
        original = svc._persist_resolution

        def explode(*args, **kwargs):  # noqa: ANN002, ANN003
            raise RuntimeError("simulated event persist failure")

        svc._persist_resolution = explode  # type: ignore[method-assign]
        with pytest.raises(RuntimeError, match="simulated"):
            # Force fire then fail during persist — bump already happened.
            # Rebuild: call evaluate path manually.
            from ai_adventure.engine.actors import actor_ref_from_player
            from ai_adventure.engine.cultivation_state import cultivation_state_from_player
            from ai_adventure.engine.events import EventContext, evaluate_trigger
            from ai_adventure.engine.story import parse_flags

            context = EventContext(
                save_id=save.id,
                subject=actor_ref_from_player(save.player),
                world_day=int(save.world_day),
                location_id=str(save.player.current_location_id),
                story_flags=parse_flags(save.story_progress.flags_json).values,
                cultivation=cultivation_state_from_player(save.player),
                money_copper=int(save.player.money_copper),
                trigger_kind="after_cultivation_session",
                cooldowns=(),
            )
            batch = evaluate_trigger(context, rng=Boom(1))
            assert batch.fired
            SaveRepository(session).bump_world_rng_counter(save)
            svc._persist_resolution(  # type: ignore[misc]
                save=save,
                player=save.player,
                progress=save.story_progress,
                resolution=batch.first_resolution,
            )
        session.rollback()

    with service._session_factory() as session:  # noqa: SLF001
        save = SaveRepository(session).get_with_player(save_id)
        assert save is not None and save.player is not None
        assert save.world_day == day_before
        assert save.player.qi_reserve_current == qi_before
        assert save.world_rng_counter == counter_before
        cool_after = {
            (row.event_template_id, row.subject_actor_id, row.fire_count, row.last_fired_world_day)
            for row in EventCooldownRepository(session).list_for_save(save_id)
        }
        assert cool_after == cool_before
        logs = EventLogRepository(session).list_for_save(save_id)
        world_events_after = {
            e.id
            for e in logs
            if e.event_type == EVENT_TYPE_WORLD_EVENT_RESOLVED
        }
        assert world_events_after == world_events_before


def test_cultivation_service_hook_runs_in_same_transaction(tmp_path: Path) -> None:
    service = create_test_save(tmp_path)
    save_id = service.list_saves()[0].save_id
    _reach_confirmed_ordinary(service, save_id)

    class AlwaysActivate(Random):
        def random(self) -> float:  # noqa: A003
            return 0.0

    cult = CultivationService(service._session_factory)  # noqa: SLF001
    # Patch EventService RNG path by wrapping run_after to inject AlwaysActivate.
    from ai_adventure.services import events as events_mod

    original = events_mod.EventService.run_after_cultivation_session

    def with_rng(self, **kwargs):  # noqa: ANN001
        kwargs["rng"] = AlwaysActivate(7)
        return original(self, **kwargs)

    events_mod.EventService.run_after_cultivation_session = with_rng  # type: ignore[method-assign]
    try:
        result = cult.cultivate(save_id, "balanced", rng=Random(0))
        assert result.outcome_type == "success"
    finally:
        events_mod.EventService.run_after_cultivation_session = original  # type: ignore[method-assign]

    events = service.list_events_for_save(save_id)
    assert any(e["event_type"] == EVENT_TYPE_WORLD_EVENT_RESOLVED for e in events)
