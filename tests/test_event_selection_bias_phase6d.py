"""Phase 6d: Event Selection Bias — ModifierSnapshot consumer + generic bias types."""

from __future__ import annotations

from random import Random

import pytest

from ai_adventure.engine.actors import ActorRef
from ai_adventure.engine.constants import (
    PATH_STATUS_CONFIRMED_ORDINARY,
    STARTING_BODY,
    STARTING_CULTIVATION_PATH,
    STARTING_DAO,
    STARTING_FOUNDATION_QUALITY,
    STARTING_FOUNDATION_STABILITY,
    STARTING_QI,
    STARTING_REALM_COMPREHENSION,
    STARTING_REALM_ID,
    STARTING_SOUL,
    STARTING_STAGE_ID,
)
from ai_adventure.engine.cultivation_state import CultivationState
from ai_adventure.engine.events import (
    EVENT_SUPPORTED_EFFECT_TYPES,
    EventCatalog,
    EventContext,
    EventTemplate,
    effective_activation_chance,
    effective_event_weight,
    evaluate_trigger,
    is_template_eligible,
    select_weighted_template,
)
from ai_adventure.engine.modifiers import (
    EffectBundleCatalog,
    EffectInstance,
    EffectSpec,
    ModifierContext,
    ModifierSnapshot,
    aggregate,
    clear_modifier_catalog_caches,
    consumer_number,
    ignored_snapshot_effect_types,
    load_effect_type_registry,
)


@pytest.fixture(autouse=True)
def _clear_modifier_caches() -> None:
    clear_modifier_catalog_caches()
    yield
    clear_modifier_catalog_caches()


def _base_state(**overrides: object) -> CultivationState:
    data = {
        "cultivation_path": STARTING_CULTIVATION_PATH,
        "path_status": PATH_STATUS_CONFIRMED_ORDINARY,
        "realm_id": STARTING_REALM_ID,
        "stage_id": STARTING_STAGE_ID,
        "body": STARTING_BODY,
        "qi": STARTING_QI,
        "soul": STARTING_SOUL,
        "dao": STARTING_DAO,
        "foundation_quality": STARTING_FOUNDATION_QUALITY,
        "qi_reserve_current": 5,
        "qi_reserve_max": 10,
        "cultivation_progress": 40,
        "realm_comprehension": STARTING_REALM_COMPREHENSION,
        "foundation_stability": STARTING_FOUNDATION_STABILITY,
        "practice_sessions": 0,
        "anomaly_state": "none",
        "breakthrough_readiness": "not_ready",
        "breakthrough_attempts_current_stage": 0,
    }
    data.update(overrides)
    return CultivationState(**data)  # type: ignore[arg-type]


def _context(**overrides: object) -> EventContext:
    data = {
        "save_id": "save-1",
        "subject": ActorRef(actor_id="actor-1", kind="player"),
        "world_day": 10,
        "location_id": "loc_a",
        "story_flags": {},
        "cultivation": _base_state(),
        "money_copper": 100,
        "trigger_kind": "after_cultivation_session",
        "cooldowns": (),
    }
    data.update(overrides)
    return EventContext(**data)  # type: ignore[arg-type]


def _template(
    *,
    event_id: str,
    category: str,
    weight: int,
    chance: float = 1.0,
    modifier_flags_all: list[str] | None = None,
) -> EventTemplate:
    return EventTemplate.model_validate(
        {
            "id": event_id,
            "category": category,
            "label": event_id,
            "enabled": True,
            "weight": weight,
            "cooldown_days": 0,
            "max_fires_per_save": None,
            "trigger": {"kinds": ["after_cultivation_session"], "chance": chance},
            "requirements": {
                "path_status_in": ["confirmed_ordinary", "confirmed_boundless"],
                "modifier_flags_all": modifier_flags_all or [],
                "subject_must_be_player": True,
            },
            "effects": [{"type": "noop", "payload": {}}],
            "presentation": {"placeholder_text": "test"},
        }
    )


def test_registry_includes_generic_bias_types() -> None:
    registry = load_effect_type_registry()
    weight = registry.get("weight_mult")
    chance = registry.get("chance_flat")
    assert weight.aggregation == "multiply"
    assert weight.allowed_contexts == ["world_event"]
    assert chance.aggregation == "sum"
    assert "world_event" in registry.get("flag").allowed_contexts


def test_aggregate_buckets_by_category() -> None:
    registry = load_effect_type_registry()
    snap = aggregate(
        [
            EffectInstance(
                source_kind="test_fixture",
                source_id="a",
                actor_id="actor-1",
                inline_effects=[
                    EffectSpec(
                        type="weight_mult",
                        params={"mult": 1.15},
                        applies_to=["world_event"],
                        category="cultivation",
                    ),
                    EffectSpec(
                        type="weight_mult",
                        params={"mult": 1.10},
                        applies_to=["world_event"],
                    ),
                ],
            )
        ],
        ModifierContext(actor_id="actor-1", world_day=1, activity="world_event"),
        type_registry=registry,
        bundles=EffectBundleCatalog(schema_version=1, bundles=[]),
    )
    assert snap.number("weight_mult") == pytest.approx(1.10)
    assert snap.number("weight_mult", category="cultivation") == pytest.approx(1.15)
    assert snap.number("weight_mult", category="discovery") == 0.0


def test_effective_weight_composes_global_and_category() -> None:
    template = _template(event_id="e1", category="cultivation", weight=10)
    snap = ModifierSnapshot(
        numbers={"weight_mult": 1.10},
        categorized_numbers={"weight_mult": {"cultivation": 1.15}},
        flags=frozenset(),
        contributions=(),
    )
    assert effective_event_weight(template, snap) == pytest.approx(10 * 1.10 * 1.15)
    assert effective_event_weight(template, None) == pytest.approx(10.0)


def test_effective_chance_composes_and_clamps() -> None:
    template = _template(event_id="e1", category="cultivation", weight=10, chance=0.9)
    snap = ModifierSnapshot(
        numbers={"chance_flat": 0.05},
        categorized_numbers={"chance_flat": {"cultivation": 0.05}},
        flags=frozenset(),
        contributions=(),
    )
    # 0.9 + 0.05 + 0.05 = 1.0 clamped
    assert effective_activation_chance(template, snap) == pytest.approx(1.0)
    assert effective_activation_chance(template, None) == pytest.approx(0.9)


def test_consumer_allowlist_ignores_foreign_types() -> None:
    snap = ModifierSnapshot(
        numbers={"session_progress_mult": 1.25, "weight_mult": 1.2},
        flags=frozenset(),
        contributions=(),
    )
    assert (
        consumer_number(
            snap,
            "weight_mult",
            supported=EVENT_SUPPORTED_EFFECT_TYPES,
            default=1.0,
        )
        == pytest.approx(1.2)
    )
    assert (
        consumer_number(
            snap,
            "session_progress_mult",
            supported=EVENT_SUPPORTED_EFFECT_TYPES,
            default=1.0,
        )
        == pytest.approx(1.0)
    )
    assert ignored_snapshot_effect_types(
        snap, supported=EVENT_SUPPORTED_EFFECT_TYPES
    ) == frozenset({"session_progress_mult"})


def test_weight_bias_shifts_weighted_selection() -> None:
    cultivation = _template(event_id="cult", category="cultivation", weight=10)
    discovery = _template(event_id="disc", category="discovery", weight=10)
    snap = ModifierSnapshot(
        numbers={},
        categorized_numbers={"weight_mult": {"cultivation": 1.25}},
        flags=frozenset(),
        contributions=(),
    )
    picks = [
        select_weighted_template(
            [cultivation, discovery],
            Random(i),
            modifiers=snap,
        ).id
        for i in range(200)
    ]
    assert picks.count("cult") > picks.count("disc")


def test_modifiers_none_preserves_catalog_behavior() -> None:
    catalog = EventCatalog(
        events=[
            _template(event_id="a", category="cultivation", weight=1, chance=1.0),
        ]
    )
    batch = evaluate_trigger(
        _context(),
        rng=Random(1),
        catalog=catalog,
        modifiers=None,
    )
    assert batch.first_resolution is not None
    assert batch.first_resolution.template_id == "a"


def test_modifier_flags_all_soft_gate() -> None:
    template = _template(
        event_id="locked",
        category="cultivation",
        weight=10,
        modifier_flags_all=["unlock_rare_insight"],
    )
    ctx = _context()
    assert is_template_eligible(template, ctx, modifiers=None) is False
    assert (
        is_template_eligible(
            template,
            ctx,
            modifiers=ModifierSnapshot(
                numbers={},
                flags=frozenset(),
                contributions=(),
            ),
        )
        is False
    )
    assert (
        is_template_eligible(
            template,
            ctx,
            modifiers=ModifierSnapshot(
                numbers={},
                flags=frozenset({"unlock_rare_insight"}),
                contributions=(),
            ),
        )
        is True
    )


def test_evaluate_trigger_applies_chance_flat() -> None:
    catalog = EventCatalog(
        events=[
            _template(event_id="rare", category="cultivation", weight=1, chance=0.0),
        ]
    )
    # Without bias: chance 0 → never fires
    miss = evaluate_trigger(
        _context(),
        rng=Random(1),
        catalog=catalog,
        modifiers=None,
    )
    assert miss.first_resolution is None

    # Registry caps chance_flat at 0.05; 0.96 + 0.05 = 1.0
    catalog_near = EventCatalog(
        events=[
            _template(event_id="near", category="cultivation", weight=1, chance=0.96),
        ]
    )
    snap = ModifierSnapshot(
        numbers={},
        categorized_numbers={"chance_flat": {"cultivation": 0.05}},
        flags=frozenset(),
        contributions=(),
    )
    hit = evaluate_trigger(
        _context(),
        rng=Random(1),
        catalog=catalog_near,
        modifiers=snap,
    )
    assert hit.first_resolution is not None


def test_proving_technique_bundle_biases_cultivation_events() -> None:
    """Technique → bundle → aggregate(world_event) → Event selection bias."""

    from ai_adventure.engine.techniques import (
        TechniqueMasteryRecord,
        get_technique,
        technique_mastery_to_effect_instances,
    )

    tech = get_technique("tech_omen_attunement")
    assert tech.effect_bundle_id == "bundle_tech_omen_attunement"

    actor_id = "actor-1"
    records = [
        TechniqueMasteryRecord(
            actor_id=actor_id,
            technique_id=tech.id,
            known=True,
            equipped=True,
            mastery_rank=1,
            mastery_progress=0,
        )
    ]
    instances = technique_mastery_to_effect_instances(records)
    snap = aggregate(
        instances,
        ModifierContext(actor_id=actor_id, world_day=1, activity="world_event"),
    )
    assert snap.number("weight_mult", category="cultivation") == pytest.approx(1.15)
    assert snap.number("chance_flat", category="cultivation") == pytest.approx(0.03)

    cultivation = _template(event_id="cult", category="cultivation", weight=10, chance=0.5)
    discovery = _template(event_id="disc", category="discovery", weight=10, chance=0.5)
    assert effective_event_weight(cultivation, snap) > effective_event_weight(
        discovery, snap
    )
    assert effective_activation_chance(cultivation, snap) == pytest.approx(0.53)
    assert effective_activation_chance(discovery, snap) == pytest.approx(0.5)
