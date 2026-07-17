"""Alchemy application service (Phase 8)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from ai_adventure.engine.alchemy import (
    get_alchemy_recipe,
    validate_alchemy_recipe_catalog_against_bundles,
)
from ai_adventure.engine.constants import EVENT_TYPE_ALCHEMY_RECIPE_AWAKENED
from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.repositories import AlchemyRecipeOwnershipRepository
from ai_adventure.repositories.saves import SaveRepository


class AlchemyService:
    """Application service for alchemy ownership and snapshot inputs."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def list_recipe_cards(self, save_id: str) -> list[dict[str, Any]]:
        """Return the alchemy recipe catalog + awakened flags (UI/debug)."""

        from ai_adventure.engine.alchemy import list_alchemy_recipes, load_alchemy_recipe_catalog

        with self._session_factory() as session:
            save = SaveRepository(session).get_with_player(save_id)
            if save is None or save.player is None:
                raise EngineValidationError("Save not found")
            validate_alchemy_recipe_catalog_against_bundles()
            rows = AlchemyRecipeOwnershipRepository(session).list_for_actor(
                save_id=save.id,
                actor_id=save.player.actor_id,
            )
            awakened = {row.recipe_id: bool(row.awakened) for row in rows}

            cards: list[dict[str, Any]] = []
            for recipe in list_alchemy_recipes():
                cards.append(
                    {
                        "id": recipe.id,
                        "display_name": recipe.display_name,
                        "grade_rank": recipe.grade_rank,
                        "effect_bundle_id": recipe.effect_bundle_id,
                        "description": recipe.description,
                        "awakened": awakened.get(recipe.id, False),
                    }
                )
            return cards

    def awaken_recipe(
        self,
        save_id: str,
        recipe_id: str,
        *,
        grade_rank: int | None = None,
    ) -> dict[str, Any]:
        """Awaken one alchemy recipe for the actor (persistent ownership).

        Caller commits the SQLAlchemy transaction when the service is used in
        the request pipeline.
        """

        with self._session_factory() as session:
            save_repo = SaveRepository(session)
            ownership_repo = AlchemyRecipeOwnershipRepository(session)
            save = save_repo.get_with_player(save_id)
            if save is None or save.player is None:
                raise EngineValidationError("Save not found")

            recipe = get_alchemy_recipe(recipe_id)
            validate_alchemy_recipe_catalog_against_bundles()

            final_grade = grade_rank if grade_rank is not None else recipe.grade_rank

            ownership_repo.upsert_awakened(
                save_id=save.id,
                actor_id=save.player.actor_id,
                recipe_id=recipe.id,
                world_day=int(save.world_day),
                grade_rank=int(final_grade),
            )

            save_repo.append_event(
                save.id,
                event_type=EVENT_TYPE_ALCHEMY_RECIPE_AWAKENED,
                payload={
                    "recipe_id": recipe.id,
                    "actor_id": save.player.actor_id,
                    "grade_rank": int(final_grade),
                    "world_day": int(save.world_day),
                    "starter": False,
                },
            )
            session.commit()

            return {
                "recipe_id": recipe.id,
                "actor_id": save.player.actor_id,
                "grade_rank": int(final_grade),
                "world_day": int(save.world_day),
            }

