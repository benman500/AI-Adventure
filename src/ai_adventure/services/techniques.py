"""Technique learning / mastery orchestration (Phase 6c).

Also hosts the shared actor ``ModifierSnapshot`` builder that combines all
current modifier sources (techniques + spiritual roots) before aggregation.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from ai_adventure.engine.constants import EVENT_TYPE_TECHNIQUE_LEARNED
from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.modifiers import (
    ModifierContext,
    ModifierSnapshot,
    aggregate,
)
from ai_adventure.engine.spiritual_roots import (
    spiritual_root_ownership_to_effect_instances,
    validate_spiritual_root_catalog_against_bundles,
)
from ai_adventure.engine.alchemy import (
    alchemy_ownership_to_effect_instances,
    validate_alchemy_recipe_catalog_against_bundles,
)
from ai_adventure.engine.techniques import (
    can_learn_technique,
    get_technique,
    list_techniques,
    technique_mastery_to_effect_instances,
    validate_technique_catalog_against_bundles,
)
from ai_adventure.repositories import (
    SaveRepository,
    TechniqueMasteryRepository,
    AlchemyRecipeOwnershipRepository,
)
from ai_adventure.repositories.spiritual_roots import SpiritualRootOwnershipRepository


def build_actor_modifier_snapshot(
    session: Session,
    *,
    save_id: str,
    actor_id: str,
    world_day: int,
    activity: str,
) -> ModifierSnapshot:
    """Aggregate all active modifier sources into a snapshot for ``activity``.

    Current sources: equipped technique mastery + awakened spiritual roots + awakened
    alchemy recipes.
    Consumers receive this snapshot only — they must not load technique,
    root, mastery, or bundle tables themselves.
    """

    validate_technique_catalog_against_bundles()
    validate_spiritual_root_catalog_against_bundles()
    validate_alchemy_recipe_catalog_against_bundles()

    tech_rows = TechniqueMasteryRepository(session).list_for_actor(save_id, actor_id)
    tech_records = TechniqueMasteryRepository.to_engine_records(tech_rows)
    tech_instances = technique_mastery_to_effect_instances(tech_records)

    root_rows = SpiritualRootOwnershipRepository(session).list_for_actor(save_id, actor_id)
    root_records = SpiritualRootOwnershipRepository.to_engine_records(root_rows)
    root_instances = spiritual_root_ownership_to_effect_instances(root_records)

    alchemy_rows = AlchemyRecipeOwnershipRepository(session).list_for_actor(save_id, actor_id)
    alchemy_records = AlchemyRecipeOwnershipRepository.to_engine_records(alchemy_rows)
    alchemy_instances = alchemy_ownership_to_effect_instances(alchemy_records)

    return aggregate(
        [*tech_instances, *root_instances, *alchemy_instances],
        ModifierContext(
            actor_id=actor_id,
            world_day=world_day,
            activity=activity,
        ),
    )


def build_cultivate_session_snapshot(
    session: Session,
    *,
    save_id: str,
    actor_id: str,
    world_day: int,
) -> ModifierSnapshot:
    """Aggregate equipped technique mastery into a cultivate_session snapshot."""

    return build_actor_modifier_snapshot(
        session,
        save_id=save_id,
        actor_id=actor_id,
        world_day=world_day,
        activity="cultivate_session",
    )


def build_breakthrough_snapshot(
    session: Session,
    *,
    save_id: str,
    actor_id: str,
    world_day: int,
) -> ModifierSnapshot:
    """Aggregate equipped technique mastery into a breakthrough snapshot."""

    return build_actor_modifier_snapshot(
        session,
        save_id=save_id,
        actor_id=actor_id,
        world_day=world_day,
        activity="breakthrough",
    )


def build_world_event_snapshot(
    session: Session,
    *,
    save_id: str,
    actor_id: str,
    world_day: int,
) -> ModifierSnapshot:
    """Aggregate equipped technique mastery into a world_event snapshot."""

    return build_actor_modifier_snapshot(
        session,
        save_id=save_id,
        actor_id=actor_id,
        world_day=world_day,
        activity="world_event",
    )


class TechniqueService:
    """Application service for technique catalog + mastery.

    Builds cultivate-session ``ModifierSnapshot`` values for other services.
    Cultivation session math never calls this for private technique tables —
    it only receives the snapshot.
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_catalog(self) -> list[dict[str, Any]]:
        """Return technique catalog cards for UI / API."""

        validate_technique_catalog_against_bundles()
        return [
            {
                "id": tech.id,
                "display_name": tech.display_name,
                "primary_category": tech.primary_category,
                "grade_rank": tech.grade_rank,
                "min_realm_order": tech.min_realm_order,
                "description": tech.description,
                "effect_bundle_id": tech.effect_bundle_id,
            }
            for tech in list_techniques()
        ]

    def list_mastery_for_save(self, save_id: str) -> list[dict[str, Any]]:
        """Return catalog techniques annotated with mastery for the player actor."""

        with self._session_factory() as session:
            save = SaveRepository(session).get_with_player(save_id)
            if save is None or save.player is None:
                raise EngineValidationError("Save not found")
            rows = TechniqueMasteryRepository(session).list_for_actor(
                save.id,
                save.player.actor_id,
            )
            by_id = {row.technique_id: row for row in rows}
            cards: list[dict[str, Any]] = []
            for tech in list_techniques():
                row = by_id.get(tech.id)
                cards.append(
                    {
                        "id": tech.id,
                        "display_name": tech.display_name,
                        "description": tech.description,
                        "known": bool(row.known) if row else False,
                        "equipped": bool(row.equipped) if row else False,
                        "mastery_rank": row.mastery_rank if row else 0,
                        "learnable": can_learn_technique(
                            tech,
                            realm_id=save.player.realm_id,
                        )[0],
                    }
                )
            return cards

    def learn(
        self,
        save_id: str,
        technique_id: str,
        *,
        equipped: bool = True,
    ) -> dict[str, Any]:
        """Learn a technique (known + optionally equipped)."""

        with self._session_factory() as session:
            save_repo = SaveRepository(session)
            mastery_repo = TechniqueMasteryRepository(session)
            save = save_repo.get_with_player(save_id)
            if save is None or save.player is None:
                raise EngineValidationError("Save not found")

            technique = get_technique(technique_id)
            allowed, reason = can_learn_technique(
                technique,
                realm_id=save.player.realm_id,
            )
            if not allowed:
                raise EngineValidationError(reason or "Cannot learn technique")

            existing = mastery_repo.get(save.id, save.player.actor_id, technique_id)
            if existing is not None and existing.known:
                raise EngineValidationError("Technique already known")

            row = mastery_repo.upsert_learned(
                save_id=save.id,
                actor_id=save.player.actor_id,
                technique_id=technique_id,
                world_day=save.world_day,
                equipped=equipped,
            )
            save_repo.append_event(
                save.id,
                event_type=EVENT_TYPE_TECHNIQUE_LEARNED,
                payload={
                    "technique_id": technique_id,
                    "actor_id": save.player.actor_id,
                    "equipped": bool(row.equipped),
                    "mastery_rank": row.mastery_rank,
                    "world_day": save.world_day,
                },
            )
            save_repo.touch_last_played(save)
            session.commit()
            return {
                "technique_id": technique_id,
                "display_name": technique.display_name,
                "known": True,
                "equipped": bool(row.equipped),
                "mastery_rank": row.mastery_rank,
            }
