"""Opaque actor references for simulation subjects.

Phase 4a: the player has an ``actor_id`` column (backfilled from ``players.id``).
The event engine treats actor ids as opaque strings and must not assume all
future actors come from the players table. NPCs already use UUID primary keys
that can serve as actor ids later.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ai_adventure.engine.errors import EngineValidationError

ActorKind = Literal["player", "npc", "unknown"]


@dataclass(frozen=True, slots=True)
class ActorRef:
    """Opaque reference to a simulation subject."""

    actor_id: str
    kind: ActorKind = "unknown"

    def __post_init__(self) -> None:
        if not self.actor_id or not str(self.actor_id).strip():
            raise EngineValidationError("actor_id is required")


def actor_ref_from_player(player: object) -> ActorRef:
    """Build an ActorRef from a player ORM row (compatibility layer)."""

    actor_id = getattr(player, "actor_id", None) or getattr(player, "id", None)
    if not actor_id:
        raise EngineValidationError("Player is missing actor_id")
    return ActorRef(actor_id=str(actor_id), kind="player")


def actor_ref_from_npc(npc: object) -> ActorRef:
    """Build an ActorRef from an NPC ORM row (future use)."""

    actor_id = getattr(npc, "id", None)
    if not actor_id:
        raise EngineValidationError("NPC is missing id")
    return ActorRef(actor_id=str(actor_id), kind="npc")
