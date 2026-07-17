"""Debug-only HTTP inspection for the event catalog (enabled when settings.debug)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ai_adventure.engine.event_devtools import (
    inspect_event,
    list_event_summaries,
    report_to_dict,
    simulate_trigger,
    simulation_to_dict,
    stats_to_dict,
    collect_event_stats,
    validate_event_catalog,
)
from ai_adventure.engine.errors import EngineValidationError

debug_router = APIRouter(prefix="/debug/events", tags=["debug-events"])


@debug_router.get("/validate")
def debug_validate_events() -> dict:
    """Return catalog validation report."""

    return report_to_dict(validate_event_catalog())


@debug_router.get("/stats")
def debug_event_stats() -> dict:
    """Return catalog statistics."""

    try:
        return stats_to_dict(collect_event_stats())
    except EngineValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@debug_router.get("/list")
def debug_list_events(
    category: str | None = None,
    trigger: str | None = None,
    enabled_only: bool = False,
) -> list[dict]:
    """List event summaries."""

    try:
        return list_event_summaries(
            category=category,
            trigger_kind=trigger,
            enabled_only=enabled_only,
        )
    except EngineValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@debug_router.get("/inspect/{event_id}")
def debug_inspect_event(event_id: str) -> dict:
    """Inspect one event template."""

    try:
        return inspect_event(event_id)
    except EngineValidationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@debug_router.get("/simulate/{trigger_kind}")
def debug_simulate_trigger(
    trigger_kind: str,
    trials: int = Query(default=200, ge=1, le=10000),
    seed: int = 1,
    path_status: str = "confirmed_ordinary",
    world_day: int = Query(default=10, ge=1),
) -> dict:
    """Dry-run simulate a trigger (no persistence)."""

    try:
        report = simulate_trigger(
            trigger_kind,
            trials=trials,
            seed=seed,
            path_status=path_status,
            world_day=world_day,
        )
        return simulation_to_dict(report)
    except EngineValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
