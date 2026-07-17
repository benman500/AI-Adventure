"""Aspiration presentation — read-only over durable facts (Phase 11a)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from ai_adventure.engine.aspirations import (
    AspirationFactSnapshot,
    assert_aspiration_catalog_valid,
    evaluate_all_aspirations,
    evaluation_to_card,
    realm_order_for_id,
    select_next_primary_preview,
    select_primary_aspiration,
)
from ai_adventure.engine.story import parse_flags
from ai_adventure.repositories.locations import LocationPresenceRepository
from ai_adventure.repositories.npc_world_state import NpcWorldStateRepository
from ai_adventure.repositories.saves import SaveRepository
from ai_adventure.repositories.sects import SectRepository, SectStandingRepository
from ai_adventure.repositories.story import StoryRepository
from ai_adventure.repositories.techniques import TechniqueMasteryRepository


class AspirationService:
    """Assembles aspiration cards from existing save facts. Never mutates."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def build_play_panel(self, session: Session, save_id: str) -> dict[str, Any] | None:
        """Return Working Toward / Gaps panel data, or None if not yet relevant."""

        assert_aspiration_catalog_valid()
        facts = self._fact_snapshot(session, save_id)
        if facts is None:
            return None
        if facts.path_status not in {"confirmed_ordinary", "confirmed_boundless"}:
            return None

        evaluations = evaluate_all_aspirations(facts)
        primary = select_primary_aspiration(evaluations)
        if primary is None:
            fulfilled_primaries = [
                item
                for item in evaluations
                if item.kind == "primary" and item.fulfilled and item.available
            ]
            if not fulfilled_primaries:
                return None
            latest = max(fulfilled_primaries, key=lambda item: item.sort_order)
            return {
                "visible": True,
                "all_primary_complete": True,
                "working_toward": evaluation_to_card(latest),
                "current_gaps": [],
                "possible_paths": [],
                "fulfilled_previous": None,
                "next_preview": None,
            }

        next_preview = select_next_primary_preview(evaluations, current=primary)
        card = evaluation_to_card(primary)
        fulfilled_previous = [
            evaluation_to_card(item)
            for item in evaluations
            if item.kind == "primary"
            and item.fulfilled
            and item.sort_order < primary.sort_order
        ]
        return {
            "visible": True,
            "all_primary_complete": False,
            "working_toward": card,
            "current_gaps": card["gaps"],
            "possible_paths": card.get("possible_paths", []),
            "fulfilled_previous": fulfilled_previous[-1] if fulfilled_previous else None,
            "next_preview": (
                {
                    "id": next_preview.aspiration_id,
                    "display_name": next_preview.display_name,
                    "summary": next_preview.summary,
                }
                if next_preview is not None
                else None
            ),
        }

    def _fact_snapshot(self, session: Session, save_id: str) -> AspirationFactSnapshot | None:
        save = SaveRepository(session).get_with_player(save_id)
        if save is None or save.player is None:
            return None
        player = save.player
        progress = StoryRepository(session).get_for_save(save_id)
        flags = parse_flags(progress.flags_json if progress else None).values

        membership = SectRepository(session).get_for_save(save_id)
        sect_id = str(membership.sect_id) if membership is not None else None
        standing = 0
        if sect_id:
            row = SectStandingRepository(session).get(save_id, sect_id)
            standing = int(row.standing_score) if row is not None else 0

        relationships: dict[str, int] = {}
        for npc_row in NpcWorldStateRepository(session).list_for_save(save_id):
            relationships[str(npc_row.npc_id)] = int(npc_row.relationship_score)

        technique_ids = frozenset(
            str(row.technique_id)
            for row in TechniqueMasteryRepository(session).list_for_actor(
                save_id, str(player.actor_id)
            )
        )
        discovered = frozenset(
            str(row.location_id)
            for row in LocationPresenceRepository(session).list_for_save(save_id)
        )

        return AspirationFactSnapshot(
            path_status=str(player.path_status),
            story_flags=dict(flags),
            sect_id=sect_id,
            sect_standing=standing,
            npc_relationships=relationships,
            known_technique_ids=technique_ids,
            foundation_stability=int(player.foundation_stability),
            realm_order=realm_order_for_id(str(player.realm_id)),
            discovered_location_ids=discovered,
        )
