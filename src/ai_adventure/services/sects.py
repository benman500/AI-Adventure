"""Sect application service (Phase 9d membership + institutional standing).

Canonical join entry: ``join(...)``. Standing deltas from NPC actions are applied
via ``apply_standing``.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from ai_adventure.engine.constants import EVENT_TYPE_SECT_JOINED
from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.sects import (
    assert_sect_catalog_valid,
    get_sect,
    plan_sect_join,
)
from ai_adventure.repositories.saves import SaveRepository
from ai_adventure.repositories.sects import SectRepository, SectStandingRepository


class SectService:
    """Orchestrates sect catalog cards, join lifecycle, and standing persistence."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def membership_card(self, session: Session, save_id: str) -> dict[str, Any] | None:
        """Return membership + standing presentation facts, or ``None``."""

        assert_sect_catalog_valid()
        membership = SectRepository(session).get_for_save(save_id)
        if membership is None:
            return None
        sect = get_sect(membership.sect_id)
        rank = sect.ranks_by_id.get(membership.rank_id)
        standing_row = SectStandingRepository(session).get(save_id, membership.sect_id)
        return {
            "sect_id": sect.sect_id,
            "display_name": sect.display_name,
            "rank_id": membership.rank_id,
            "rank_display_name": rank.display_name if rank is not None else membership.rank_id,
            "standing_score": int(standing_row.standing_score) if standing_row else 0,
            "description": sect.description,
        }

    def get_standing_score(self, session: Session, save_id: str, sect_id: str) -> int | None:
        """Return standing score for a sect, or ``None`` if no row."""

        row = SectStandingRepository(session).get(save_id, sect_id)
        if row is None:
            return None
        return int(row.standing_score)

    def join(
        self,
        session: Session,
        *,
        save_id: str,
        sect_id: str,
        rank_id: str,
        world_day: int,
        waive_standing_gate: bool = False,
        append_event: bool = True,
    ) -> dict[str, Any]:
        """Join or update primary sect membership; seed standing when absent."""

        assert_sect_catalog_valid()
        save_repo = SaveRepository(session)
        save = save_repo.get_with_player(save_id)
        if save is None:
            raise EngineValidationError("Save not found")

        membership_repo = SectRepository(session)
        standing_repo = SectStandingRepository(session)
        existing = membership_repo.get_for_save(save_id)
        standing_row = standing_repo.get(save_id, sect_id)
        plan = plan_sect_join(
            sect_id=sect_id,
            rank_id=rank_id,
            current_membership_sect_id=None if existing is None else existing.sect_id,
            current_membership_rank_id=None if existing is None else existing.rank_id,
            current_standing=(
                None if standing_row is None else int(standing_row.standing_score)
            ),
            waive_standing_gate=waive_standing_gate,
        )
        membership_repo.upsert(
            save_id=save_id,
            sect_id=plan.sect_id,
            rank_id=plan.rank_id,
        )
        standing_repo.upsert_score(
            save_id=save_id,
            sect_id=plan.sect_id,
            standing_score=plan.standing_score,
            world_day=world_day,
        )
        if append_event:
            save_repo.append_event(
                save_id,
                event_type=EVENT_TYPE_SECT_JOINED,
                payload={
                    "sect_id": plan.sect_id,
                    "rank_id": plan.rank_id,
                    "standing_score": plan.standing_score,
                    "seeded_standing": plan.seeded_standing,
                    "is_rank_change": plan.is_rank_change,
                    "world_day": world_day,
                    "waive_standing_gate": waive_standing_gate,
                },
            )
        sect = get_sect(plan.sect_id)
        rank = sect.ranks_by_id[plan.rank_id]
        return {
            "sect_id": plan.sect_id,
            "display_name": sect.display_name,
            "rank_id": plan.rank_id,
            "rank_display_name": rank.display_name,
            "standing_score": plan.standing_score,
            "seeded_standing": plan.seeded_standing,
            "is_rank_change": plan.is_rank_change,
        }

    def apply_standing(
        self,
        session: Session,
        *,
        save_id: str,
        sect_id: str,
        standing_score: int,
        world_day: int,
    ) -> int:
        """Persist a validated standing score for ``sect_id``."""

        assert_sect_catalog_valid()
        get_sect(sect_id)
        row = SectStandingRepository(session).upsert_score(
            save_id=save_id,
            sect_id=sect_id,
            standing_score=standing_score,
            world_day=world_day,
        )
        return int(row.standing_score)
