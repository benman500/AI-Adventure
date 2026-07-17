"""Debug-only HTTP inspection for ModifierSnapshot contributions.

Enabled when settings.debug is true.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.modifiers import ModifierSnapshot
from ai_adventure.repositories.saves import SaveRepository
from ai_adventure.services.techniques import build_actor_modifier_snapshot

debug_router = APIRouter(prefix="/debug/modifiers", tags=["debug-modifiers"])


def _snapshot_to_dict(snapshot: ModifierSnapshot) -> dict[str, Any]:
    """Convert snapshot + audit trail to a JSON-friendly shape."""

    return {
        "numbers": dict(snapshot.numbers),
        "categorized_numbers": {
            type_id: dict(by_cat) for type_id, by_cat in snapshot.categorized_numbers.items()
        },
        "flags": sorted(list(snapshot.flags)),
        "contributions": [
            {
                "source_kind": c.source_kind,
                "source_id": c.source_id,
                "effect_type": c.effect_type,
                "category": c.category,
                "detail": c.detail,
                "raw": c.raw,
                "applied": c.applied,
            }
            for c in snapshot.contributions
        ],
    }


@debug_router.get("/snapshot")
def debug_snapshot(
    request: Request,
    save_id: str,
    activity: str = Query(default="cultivate_session"),
    actor_id: str | None = Query(default=None),
) -> dict[str, Any]:
    """Return a recomputed ModifierSnapshot audit trail (developer view only)."""

    session_factory = request.app.state.session_factory
    try:
        with session_factory() as session:
            save = SaveRepository(session).get_with_player(save_id)
            if save is None or save.player is None:
                raise HTTPException(status_code=404, detail="Save not found")

            resolved_actor_id = actor_id or str(save.player.actor_id)
            snapshot = build_actor_modifier_snapshot(
                session,
                save_id=save_id,
                actor_id=resolved_actor_id,
                world_day=int(save.world_day),
                activity=activity,
            )

            return {
                "context": {
                    "save_id": save_id,
                    "actor_id": resolved_actor_id,
                    "activity": activity,
                    "world_day": int(save.world_day),
                },
                "snapshot": _snapshot_to_dict(snapshot),
            }
    except EngineValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

