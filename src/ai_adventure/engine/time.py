"""Minimal centralized world clock (simulation day).

Playtime seconds remain separate player telemetry and must not be treated as a
second simulation clock. All new systems should advance ``world_day`` through
this module rather than mutating save rows ad hoc.
"""

from __future__ import annotations

from ai_adventure.engine.errors import EngineValidationError


def current_world_day(world_day: int) -> int:
    """Return the current world day (validated)."""

    if world_day < 1:
        raise EngineValidationError("world_day must be >= 1")
    return world_day


def advance_world_days(world_day: int, days: int) -> int:
    """Return the new world day after advancing ``days`` (non-negative).

    Pure function: does not touch persistence. Callers apply the result via
    repositories inside a transaction.
    """

    if days < 0:
        raise EngineValidationError("Cannot advance world clock by negative days")
    return current_world_day(world_day) + days
