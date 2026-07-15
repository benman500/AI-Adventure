"""Data-driven authored story nodes and transitions."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from ai_adventure.engine.constants import (
    CULTIVATION_METHOD_ABSORB_QI,
    CULTIVATION_METHOD_CALM_MIND,
    CULTIVATION_METHOD_STABILIZE_FOUNDATION,
    FLAG_ANOMALY_TRIGGERED,
    FLAG_BREAKTHROUGH_READY,
    FLAG_INVESTIGATION_COMPLETE,
    FLAG_LESSON_COMPLETE,
    FLAG_PATH_CONFIRMED,
    FLAG_REVELATION_SEEN,
)
from ai_adventure.engine.cultivation import (
    CultivationState,
    apply_cultivation_method,
    attempt_breakthrough,
    commit_path_choice,
    cultivation_state_from_player,
    is_breakthrough_ready,
    refresh_breakthrough_readiness,
)
from ai_adventure.engine.errors import EngineValidationError

_STORY_DIR = Path(__file__).resolve().parents[1] / "data" / "story"


class StoryRequirements(BaseModel):
    """Requirements to enter a node or choose an action."""

    background_id: str | None = None
    flags_all: list[str] = Field(default_factory=list)
    flags_none: list[str] = Field(default_factory=list)
    min_breakthrough_readiness: str | None = None
    anomaly_state: str | None = None
    path_status: str | None = None


class StoryEffect(BaseModel):
    """Engine effect applied by story transitions."""

    type: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)


class StoryAction(BaseModel):
    """One player-selectable action on a story node."""

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    requirements: StoryRequirements = Field(default_factory=StoryRequirements)
    effects: list[StoryEffect] = Field(default_factory=list)
    next_node: str = Field(min_length=1)


class StoryNode(BaseModel):
    """One authored story beat."""

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    narrative: str = Field(min_length=1)
    requirements: StoryRequirements = Field(default_factory=StoryRequirements)
    on_enter_effects: list[StoryEffect] = Field(default_factory=list)
    actions: list[StoryAction] = Field(min_length=1)
    event_on_enter: dict[str, Any] | None = None

    @field_validator("actions")
    @classmethod
    def _unique_action_ids(cls, value: list[StoryAction]) -> list[StoryAction]:
        ids = [item.id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate action ids on story node")
        return value


class StoryManifest(BaseModel):
    """Registry of story content files and background entry nodes."""

    background_entry_nodes: dict[str, str]
    content_files: list[str]


@dataclass(frozen=True, slots=True)
class StoryFlags:
    """Mutable story flags for one save (engine copy)."""

    values: dict[str, bool] = field(default_factory=dict)

    def has(self, flag: str) -> bool:
        return self.values.get(flag, False)

    def set(self, flag: str, value: bool = True) -> StoryFlags:
        updated = dict(self.values)
        updated[flag] = value
        return StoryFlags(values=updated)


@dataclass(frozen=True, slots=True)
class StoryContext:
    """Inputs required to evaluate story requirements and effects."""

    background_id: str
    current_node_id: str
    flags: StoryFlags
    cultivation: CultivationState
    world_day: int


@dataclass(frozen=True, slots=True)
class StoryTransitionResult:
    """Result of applying a story action."""

    next_node_id: str
    flags: StoryFlags
    cultivation: CultivationState
    world_day: int
    location_id: str | None
    location_name: str | None
    sect_id: str | None
    sect_rank: str | None
    spawned_npcs: tuple[dict[str, str], ...]
    events: tuple[dict[str, Any], ...]
    summary: str


@dataclass(frozen=True, slots=True)
class SceneView:
    """Player-facing scene with available actions."""

    node_id: str
    title: str
    narrative: str
    actions: tuple[dict[str, str], ...]
    cultivation_methods: tuple[dict[str, str], ...]
    flags: StoryFlags


CULTIVATION_METHOD_LABELS: dict[str, str] = {
    CULTIVATION_METHOD_ABSORB_QI: "Absorb Qi",
    CULTIVATION_METHOD_STABILIZE_FOUNDATION: "Stabilize Foundation",
    CULTIVATION_METHOD_CALM_MIND: "Calm the Mind",
}


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EngineValidationError(f"Corrupted story data: {path.name}") from exc


@lru_cache(maxsize=1)
def load_story_manifest(story_dir: str | None = None) -> StoryManifest:
    """Load story manifest."""

    directory = Path(story_dir) if story_dir else _STORY_DIR
    path = directory / "story_manifest.json"
    if not path.is_file():
        raise EngineValidationError(f"Story manifest missing: {path}")
    try:
        return StoryManifest.model_validate(_load_json(path))
    except Exception as exc:  # noqa: BLE001
        raise EngineValidationError(f"Invalid story manifest: {exc}") from exc


@lru_cache(maxsize=1)
def load_story_registry(story_dir: str | None = None) -> dict[str, StoryNode]:
    """Load and validate all story nodes."""

    directory = Path(story_dir) if story_dir else _STORY_DIR
    manifest = load_story_manifest(str(directory))
    registry: dict[str, StoryNode] = {}

    for filename in manifest.content_files:
        path = directory / filename
        if not path.is_file():
            raise EngineValidationError(f"Story content file missing: {filename}")
        raw = _load_json(path)
        nodes_raw = raw.get("nodes", raw) if isinstance(raw, dict) else raw
        if not isinstance(nodes_raw, list):
            raise EngineValidationError(f"Story file {filename} must contain a nodes list")
        for item in nodes_raw:
            try:
                node = StoryNode.model_validate(item)
            except Exception as exc:  # noqa: BLE001
                raise EngineValidationError(f"Invalid node in {filename}: {exc}") from exc
            if node.id in registry:
                raise EngineValidationError(f"Duplicate story node id: {node.id}")
            registry[node.id] = node

    _validate_graph(registry, manifest)
    return registry


def clear_story_cache() -> None:
    """Clear cached story content (tests)."""

    load_story_manifest.cache_clear()
    load_story_registry.cache_clear()


def entry_node_for_background(background_id: str, story_dir: str | None = None) -> str:
    """Return the first story node for a background."""

    manifest = load_story_manifest(story_dir)
    try:
        return manifest.background_entry_nodes[background_id]
    except KeyError as exc:
        raise EngineValidationError(f"No story entry for background: {background_id}") from exc


def get_story_node(node_id: str, story_dir: str | None = None) -> StoryNode:
    """Return a story node by id."""

    registry = load_story_registry(story_dir)
    try:
        return registry[node_id]
    except KeyError as exc:
        raise EngineValidationError(f"Unknown story node: {node_id}") from exc


def parse_flags(raw: str) -> StoryFlags:
    """Parse persisted flags JSON."""

    try:
        data = json.loads(raw) if raw else {}
    except json.JSONDecodeError as exc:
        raise EngineValidationError("Corrupted story flags") from exc
    if not isinstance(data, dict):
        raise EngineValidationError("Story flags must be a JSON object")
    return StoryFlags(values={str(k): bool(v) for k, v in data.items()})


def flags_to_json(flags: StoryFlags) -> str:
    """Serialize flags for persistence."""

    return json.dumps(flags.values, sort_keys=True)


def build_scene_view(
    context: StoryContext,
    *,
    story_dir: str | None = None,
) -> SceneView:
    """Render the current node with legal actions and cultivation methods."""

    node = get_story_node(context.current_node_id, story_dir)
    _assert_requirements(node.requirements, context)

    actions: list[dict[str, str]] = []
    for action in node.actions:
        if _requirements_met(action.requirements, context):
            actions.append({"id": action.id, "label": action.label})

    cultivation_methods: list[dict[str, str]] = []
    if _node_allows_cultivation(node):
        for method_id, label in CULTIVATION_METHOD_LABELS.items():
            cultivation_methods.append({"id": method_id, "label": label})
        if is_breakthrough_ready(context.cultivation) and context.cultivation.breakthrough_readiness != "attempted":
            actions.append({"id": "attempt_breakthrough", "label": "Attempt Breakthrough"})

    return SceneView(
        node_id=node.id,
        title=node.title,
        narrative=node.narrative,
        actions=tuple(actions),
        cultivation_methods=tuple(cultivation_methods),
        flags=context.flags,
    )


def apply_story_action(
    context: StoryContext,
    action_id: str,
    *,
    story_dir: str | None = None,
) -> StoryTransitionResult:
    """Validate and apply a story action or cultivation method."""

    if action_id in CULTIVATION_METHOD_LABELS:
        return _apply_cultivation_method(context, action_id, story_dir=story_dir)
    if action_id == "attempt_breakthrough":
        return _apply_breakthrough_attempt(context, story_dir=story_dir)

    node = get_story_node(context.current_node_id, story_dir)
    action = _find_action(node, action_id)
    if not _requirements_met(action.requirements, context):
        raise EngineValidationError("Action requirements not met")

    return _transition(context, node, action, story_dir=story_dir)


def _apply_cultivation_method(
    context: StoryContext,
    method_id: str,
    *,
    story_dir: str | None = None,
) -> StoryTransitionResult:
    node = get_story_node(context.current_node_id, story_dir)
    if not _node_allows_cultivation(node):
        raise EngineValidationError("Cultivation is not available at this story beat")

    result = apply_cultivation_method(context.cultivation, method_id)
    flags = context.flags
    if is_breakthrough_ready(result.state):
        flags = flags.set(FLAG_BREAKTHROUGH_READY, True)

    events = [{"event_type": e.event_type, "payload": e.payload} for e in result.events]
    return StoryTransitionResult(
        next_node_id=context.current_node_id,
        flags=flags,
        cultivation=result.state,
        world_day=context.world_day,
        location_id=None,
        location_name=None,
        sect_id=None,
        sect_rank=None,
        spawned_npcs=(),
        events=tuple(events),
        summary=result.summary,
    )


def _apply_breakthrough_attempt(
    context: StoryContext,
    *,
    story_dir: str | None = None,
) -> StoryTransitionResult:
    node = get_story_node(context.current_node_id, story_dir)
    if not _node_allows_cultivation(node) and node.id != "shared_breakthrough_ready_01":
        raise EngineValidationError("Breakthrough cannot be attempted here")

    result = attempt_breakthrough(context.cultivation)
    flags = context.flags.set(FLAG_BREAKTHROUGH_READY, True)
    if result.state.anomaly_state == "triggered":
        flags = flags.set(FLAG_ANOMALY_TRIGGERED, True)

    next_node = "shared_anomaly_01" if result.state.anomaly_state == "triggered" else context.current_node_id
    events: list[dict[str, Any]] = [
        {"event_type": e.event_type, "payload": e.payload} for e in result.events
    ]

    location_id: str | None = None
    location_name: str | None = None
    sect_id: str | None = None
    sect_rank: str | None = None
    spawned: list[dict[str, str]] = []
    world_day = context.world_day
    cultivation = result.state

    if next_node != context.current_node_id:
        anomaly_node = get_story_node(next_node, story_dir)
        for effect in anomaly_node.on_enter_effects:
            cultivation, flags, world_day, location_id, location_name, sect_id, sect_rank, spawned, events = (
                _apply_effect(
                    effect,
                    cultivation=cultivation,
                    flags=flags,
                    world_day=world_day,
                    location_id=location_id,
                    location_name=location_name,
                    sect_id=sect_id,
                    sect_rank=sect_rank,
                    spawned=spawned,
                    events=events,
                )
            )
        if anomaly_node.event_on_enter:
            events.append(anomaly_node.event_on_enter)
        events.append(
            {
                "event_type": "story_entered",
                "payload": {"node_id": anomaly_node.id, "title": anomaly_node.title},
            }
        )

    return StoryTransitionResult(
        next_node_id=next_node,
        flags=flags,
        cultivation=cultivation,
        world_day=world_day,
        location_id=location_id,
        location_name=location_name,
        sect_id=sect_id,
        sect_rank=sect_rank,
        spawned_npcs=tuple(spawned),
        events=tuple(events),
        summary=result.summary,
    )


def _transition(
    context: StoryContext,
    node: StoryNode,
    action: StoryAction,
    *,
    story_dir: str | None = None,
) -> StoryTransitionResult:
    cultivation = context.cultivation
    flags = context.flags
    world_day = context.world_day
    location_id: str | None = None
    location_name: str | None = None
    sect_id: str | None = None
    sect_rank: str | None = None
    spawned: list[dict[str, str]] = []
    events: list[dict[str, Any]] = []

    for effect in action.effects:
        cultivation, flags, world_day, location_id, location_name, sect_id, sect_rank, spawned, events = (
            _apply_effect(
                effect,
                cultivation=cultivation,
                flags=flags,
                world_day=world_day,
                location_id=location_id,
                location_name=location_name,
                sect_id=sect_id,
                sect_rank=sect_rank,
                spawned=spawned,
                events=events,
            )
        )

    next_node_id = action.next_node
    next_node = get_story_node(next_node_id, story_dir)

    for effect in next_node.on_enter_effects:
        cultivation, flags, world_day, location_id, location_name, sect_id, sect_rank, spawned, events = (
            _apply_effect(
                effect,
                cultivation=cultivation,
                flags=flags,
                world_day=world_day,
                location_id=location_id,
                location_name=location_name,
                sect_id=sect_id,
                sect_rank=sect_rank,
                spawned=spawned,
                events=events,
            )
        )

    if next_node.event_on_enter:
        events.append(next_node.event_on_enter)

    events.append(
        {
            "event_type": "story_entered",
            "payload": {"node_id": next_node.id, "title": next_node.title},
        }
    )

    events.append(
        {
            "event_type": "story_action",
            "payload": {
                "from_node": node.id,
                "action_id": action.id,
                "to_node": next_node_id,
            },
        }
    )

    return StoryTransitionResult(
        next_node_id=next_node_id,
        flags=flags,
        cultivation=cultivation,
        world_day=world_day,
        location_id=location_id,
        location_name=location_name,
        sect_id=sect_id,
        sect_rank=sect_rank,
        spawned_npcs=tuple(spawned),
        events=tuple(events),
        summary=f"Story action {action.id} applied.",
    )


def apply_on_enter(
    context: StoryContext,
    *,
    story_dir: str | None = None,
) -> StoryTransitionResult:
    """Apply on_enter effects when entering a node."""

    node = get_story_node(context.current_node_id, story_dir)
    cultivation = context.cultivation
    flags = context.flags
    world_day = context.world_day
    location_id: str | None = None
    location_name: str | None = None
    sect_id: str | None = None
    sect_rank: str | None = None
    spawned: list[dict[str, str]] = []
    events: list[dict[str, Any]] = []

    for effect in node.on_enter_effects:
        cultivation, flags, world_day, location_id, location_name, sect_id, sect_rank, spawned, events = (
            _apply_effect(
                effect,
                cultivation=cultivation,
                flags=flags,
                world_day=world_day,
                location_id=location_id,
                location_name=location_name,
                sect_id=sect_id,
                sect_rank=sect_rank,
                spawned=spawned,
                events=events,
            )
        )

    if node.event_on_enter:
        events.append(node.event_on_enter)

    events.append(
        {
            "event_type": "story_entered",
            "payload": {"node_id": node.id, "title": node.title},
        }
    )

    return StoryTransitionResult(
        next_node_id=node.id,
        flags=flags,
        cultivation=cultivation,
        world_day=world_day,
        location_id=location_id,
        location_name=location_name,
        sect_id=sect_id,
        sect_rank=sect_rank,
        spawned_npcs=tuple(spawned),
        events=tuple(events),
        summary=f"Entered {node.title}.",
    )


def _apply_effect(
    effect: StoryEffect,
    *,
    cultivation: CultivationState,
    flags: StoryFlags,
    world_day: int,
    location_id: str | None,
    location_name: str | None,
    sect_id: str | None,
    sect_rank: str | None,
    spawned: list[dict[str, str]],
    events: list[dict[str, Any]],
) -> tuple[
    CultivationState,
    StoryFlags,
    int,
    str | None,
    str | None,
    str | None,
    str | None,
    list[dict[str, str]],
    list[dict[str, Any]],
]:
    payload = effect.payload
    if effect.type == "set_flag":
        flags = flags.set(str(payload["flag"]), bool(payload.get("value", True)))
    elif effect.type == "clear_flag":
        flags = flags.set(str(payload["flag"]), False)
    elif effect.type == "increment_world_day":
        world_day += int(payload.get("amount", 1))
    elif effect.type == "set_location":
        location_id = str(payload["location_id"])
        location_name = str(payload["location_name"])
    elif effect.type == "set_sect_membership":
        sect_id = str(payload["sect_id"])
        sect_rank = str(payload["rank_id"])
    elif effect.type == "spawn_npc":
        spawned.append(
            {
                "template_id": str(payload["template_id"]),
                "display_name": str(payload["display_name"]),
                "role": str(payload["role"]),
            }
        )
    elif effect.type == "commit_path_ordinary":
        result = commit_path_choice(cultivation, choose_boundless=False)
        cultivation = result.state
        flags = flags.set(FLAG_PATH_CONFIRMED, True)
        for event in result.events:
            events.append({"event_type": event.event_type, "payload": event.payload})
    elif effect.type == "commit_path_boundless":
        result = commit_path_choice(cultivation, choose_boundless=True)
        cultivation = result.state
        flags = flags.set(FLAG_PATH_CONFIRMED, True)
        for event in result.events:
            events.append({"event_type": event.event_type, "payload": event.payload})
    elif effect.type == "mark_lesson_complete":
        flags = flags.set(FLAG_LESSON_COMPLETE, True)
    elif effect.type == "mark_investigation_complete":
        flags = flags.set(FLAG_INVESTIGATION_COMPLETE, True)
    elif effect.type == "mark_revelation_seen":
        flags = flags.set(FLAG_REVELATION_SEEN, True)
    else:
        raise EngineValidationError(f"Unknown story effect type: {effect.type}")

    cultivation, readiness_event = refresh_breakthrough_readiness(cultivation)
    if readiness_event is not None:
        events.append({"event_type": readiness_event.event_type, "payload": readiness_event.payload})
        if is_breakthrough_ready(cultivation):
            flags = flags.set(FLAG_BREAKTHROUGH_READY, True)

    return cultivation, flags, world_day, location_id, location_name, sect_id, sect_rank, spawned, events


def _node_allows_cultivation(node: StoryNode) -> bool:
    return node.id in {"shared_cultivation_01", "shared_post_ordinary_02", "shared_post_boundless_02"}


def _find_action(node: StoryNode, action_id: str) -> StoryAction:
    for action in node.actions:
        if action.id == action_id:
            return action
    raise EngineValidationError(f"Unknown action: {action_id}")


def _requirements_met(requirements: StoryRequirements, context: StoryContext) -> bool:
    if requirements.background_id and requirements.background_id != context.background_id:
        return False
    for flag in requirements.flags_all:
        if not context.flags.has(flag):
            return False
    for flag in requirements.flags_none:
        if context.flags.has(flag):
            return False
    if requirements.min_breakthrough_readiness:
        order = ["not_ready", "ready", "attempted"]
        if order.index(context.cultivation.breakthrough_readiness) < order.index(
            requirements.min_breakthrough_readiness
        ):
            return False
    if requirements.anomaly_state and context.cultivation.anomaly_state != requirements.anomaly_state:
        return False
    if requirements.path_status and context.cultivation.path_status != requirements.path_status:
        return False
    return True


def _assert_requirements(requirements: StoryRequirements, context: StoryContext) -> None:
    if not _requirements_met(requirements, context):
        raise EngineValidationError("Story node requirements not met")


def _validate_graph(registry: dict[str, StoryNode], manifest: StoryManifest) -> None:
    for entry in manifest.background_entry_nodes.values():
        if entry not in registry:
            raise EngineValidationError(f"Entry node missing from registry: {entry}")
    for node in registry.values():
        for action in node.actions:
            if action.next_node not in registry:
                raise EngineValidationError(
                    f"Node {node.id} action {action.id} references unknown next_node {action.next_node}"
                )


__all__ = [
    "SceneView",
    "StoryContext",
    "StoryFlags",
    "StoryTransitionResult",
    "apply_on_enter",
    "apply_story_action",
    "build_scene_view",
    "clear_story_cache",
    "cultivation_state_from_player",
    "entry_node_for_background",
    "flags_to_json",
    "get_story_node",
    "load_story_registry",
    "parse_flags",
]
