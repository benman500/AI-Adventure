"""Application service for world event evaluation and atomic persistence."""

from __future__ import annotations

from dataclasses import dataclass
from random import Random

from uuid import uuid4

from sqlalchemy.orm import Session

from ai_adventure.db.models import GameSave, InventoryItem, Player, StoryProgress
from ai_adventure.engine.actors import actor_ref_from_player
from ai_adventure.engine.constants import EVENT_TYPE_WORLD_EVENT_RESOLVED
from ai_adventure.engine.cultivation_state import CultivationState, cultivation_state_from_player
from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.events import (
    EventContext,
    EventResolution,
    EventTriggerBatch,
    evaluate_trigger,
    resolution_to_event_log_payload,
)
from ai_adventure.engine.story import flags_to_json, parse_flags
from ai_adventure.repositories.events import EventCooldownRepository
from ai_adventure.repositories.saves import SaveRepository
from ai_adventure.services.techniques import build_world_event_snapshot


@dataclass(frozen=True, slots=True)
class PersistedTriggerResult:
    """Outcome of evaluating a trigger inside an open DB transaction."""

    batch: EventTriggerBatch
    presentation_message: str | None
    fired: bool


class EventService:
    """Orchestrates event evaluation and persistence (no HTTP, no AI).

    Must be used inside an open SQLAlchemy session that the caller commits or
    rolls back. Raises leave no partial event effects when the caller aborts
    the transaction.
    """

    def __init__(self, session: Session) -> None:
        self._session = session
        self._saves = SaveRepository(session)
        self._cooldowns = EventCooldownRepository(session)

    def run_after_cultivation_session(
        self,
        *,
        save: GameSave,
        player: Player,
        progress: StoryProgress | None,
        cultivation: CultivationState | None = None,
        rng: Random | None = None,
    ) -> PersistedTriggerResult:
        """Evaluate ``after_cultivation_session`` and persist any resolution."""

        return self.run_trigger(
            save=save,
            player=player,
            progress=progress,
            trigger_kind="after_cultivation_session",
            cultivation=cultivation,
            rng=rng,
        )

    def run_after_story_travel(
        self,
        *,
        save: GameSave,
        player: Player,
        progress: StoryProgress | None,
        cultivation: CultivationState | None = None,
        rng: Random | None = None,
    ) -> PersistedTriggerResult:
        """Evaluate ``after_story_travel`` and persist any resolution."""

        return self.run_trigger(
            save=save,
            player=player,
            progress=progress,
            trigger_kind="after_story_travel",
            cultivation=cultivation,
            rng=rng,
        )

    def run_after_explore(
        self,
        *,
        save: GameSave,
        player: Player,
        progress: StoryProgress | None,
        cultivation: CultivationState | None = None,
        rng: Random | None = None,
    ) -> PersistedTriggerResult:
        """Evaluate ``after_explore`` and persist any resolution."""

        return self.run_trigger(
            save=save,
            player=player,
            progress=progress,
            trigger_kind="after_explore",
            cultivation=cultivation,
            rng=rng,
            action_id="explore",
        )

    def run_after_inspect(
        self,
        *,
        save: GameSave,
        player: Player,
        progress: StoryProgress | None,
        cultivation: CultivationState | None = None,
        rng: Random | None = None,
    ) -> PersistedTriggerResult:
        """Evaluate ``after_inspect`` and persist any resolution."""

        return self.run_trigger(
            save=save,
            player=player,
            progress=progress,
            trigger_kind="after_inspect",
            cultivation=cultivation,
            rng=rng,
            action_id="inspect",
        )

    def run_after_npc_interact(
        self,
        *,
        save: GameSave,
        player: Player,
        progress: StoryProgress | None,
        action_id: str,
        cultivation: CultivationState | None = None,
        rng: Random | None = None,
    ) -> PersistedTriggerResult:
        """Evaluate ``after_npc_interact`` and persist any resolution."""

        return self.run_trigger(
            save=save,
            player=player,
            progress=progress,
            trigger_kind="after_npc_interact",
            cultivation=cultivation,
            rng=rng,
            action_id=action_id,
        )

    def run_trigger(
        self,
        *,
        save: GameSave,
        player: Player,
        progress: StoryProgress | None,
        trigger_kind: str,
        cultivation: CultivationState | None = None,
        rng: Random | None = None,
        catalog: object | None = None,
        events_dir: str | None = None,
        action_id: str | None = None,
    ) -> PersistedTriggerResult:
        """Evaluate a trigger against current save state; persist if an event fires.

        Always advances ``world_rng_counter`` so successive evaluations remain
        deterministic and independent of cultivation RNG.
        """

        if player is None:
            raise EngineValidationError("Player required for event trigger")

        state = cultivation if cultivation is not None else cultivation_state_from_player(player)
        flags = parse_flags(progress.flags_json).values if progress is not None else {}
        subject = actor_ref_from_player(player)
        cooldowns = self._cooldowns.cooldown_states_for_save(save.id)

        counter = int(getattr(save, "world_rng_counter", 0) or 0)
        if rng is None:
            seed = (hash(save.id) & 0xFFFFFFFF) ^ (counter * 2654435761)
            rng = Random(seed)

        context = EventContext(
            save_id=save.id,
            subject=subject,
            world_day=int(save.world_day),
            location_id=str(player.current_location_id),
            story_flags=dict(flags),
            cultivation=state,
            money_copper=int(player.money_copper),
            trigger_kind=trigger_kind,
            cooldowns=cooldowns,
            action_id=action_id,
        )
        modifiers = build_world_event_snapshot(
            self._session,
            save_id=save.id,
            actor_id=subject.actor_id,
            world_day=int(save.world_day),
        )
        batch = evaluate_trigger(
            context,
            rng=rng,
            catalog=catalog,  # type: ignore[arg-type]
            events_dir=events_dir,
            modifiers=modifiers,
        )

        # Consume RNG counter for this evaluation attempt (hit or miss).
        self._saves.bump_world_rng_counter(save)

        resolution = batch.first_resolution
        if resolution is None:
            return PersistedTriggerResult(
                batch=batch,
                presentation_message=None,
                fired=False,
            )

        self._persist_resolution(
            save=save,
            player=player,
            progress=progress,
            resolution=resolution,
        )
        return PersistedTriggerResult(
            batch=batch,
            presentation_message=resolution.presentation_placeholder,
            fired=True,
        )

    def _persist_resolution(
        self,
        *,
        save: GameSave,
        player: Player,
        progress: StoryProgress | None,
        resolution: EventResolution,
    ) -> None:
        """Apply all mechanical effects for one fired event (caller commits)."""

        self._saves.apply_player_cultivation(player, resolution.cultivation)
        player.money_copper = resolution.money_copper
        self._session.add(player)

        if resolution.world_day_after != int(save.world_day):
            delta = int(resolution.world_day_after) - int(save.world_day)
            if delta < 0:
                raise EngineValidationError("Event effects cannot reverse the world clock")
            if delta > 0:
                self._saves.advance_world_day(save, delta)

        for item in resolution.granted_items:
            self._grant_item(
                save=save,
                player=player,
                item_code=str(item["item_code"]),
                display_name=str(item["display_name"]),
                quantity=int(item["quantity"]),
            )

        if progress is not None and resolution.flags_set:
            current = parse_flags(progress.flags_json)
            for flag, value in resolution.flags_set.items():
                current = current.set(flag, value)
            progress.flags_json = flags_to_json(current)
            self._session.add(progress)

        self._cooldowns.record_fire(
            save_id=save.id,
            event_template_id=resolution.template_id,
            subject_actor_id=resolution.subject_actor_id,
            world_day=resolution.world_day_after,
        )

        payload = resolution_to_event_log_payload(resolution)
        self._saves.append_event(
            save.id,
            event_type=EVENT_TYPE_WORLD_EVENT_RESOLVED,
            payload=payload,
        )

    def _grant_item(
        self,
        *,
        save: GameSave,
        player: Player,
        item_code: str,
        display_name: str,
        quantity: int,
    ) -> None:
        """Add or stack an inventory item for the player."""

        existing = None
        for row in list(getattr(player, "inventory_items", []) or []):
            if row.item_code == item_code:
                existing = row
                break
        if existing is not None:
            existing.quantity = int(existing.quantity) + quantity
            self._session.add(existing)
            return
        self._session.add(
            InventoryItem(
                id=str(uuid4()),
                save_id=save.id,
                player_id=player.id,
                item_code=item_code,
                display_name=display_name,
                quantity=quantity,
            )
        )
