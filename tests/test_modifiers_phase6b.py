"""Phase 6b: Modifier Framework — registry validation and deterministic aggregate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.modifiers import (
    EffectBundle,
    EffectBundleCatalog,
    EffectInstance,
    EffectSpec,
    EffectTypeRegistry,
    ModifierContext,
    aggregate,
    clear_modifier_catalog_caches,
    load_effect_bundle_catalog,
    load_effect_type_registry,
    validate_bundle_against_registry,
    validate_effect_spec,
)


@pytest.fixture(autouse=True)
def _clear_modifier_caches() -> None:
    clear_modifier_catalog_caches()
    yield
    clear_modifier_catalog_caches()


@pytest.fixture
def registry() -> EffectTypeRegistry:
    return load_effect_type_registry()


@pytest.fixture
def bundles(registry: EffectTypeRegistry) -> EffectBundleCatalog:
    return load_effect_bundle_catalog(type_registry=registry)


def test_load_default_effect_type_registry(registry: EffectTypeRegistry) -> None:
    ids = {item.id for item in registry.effect_types}
    assert "session_progress_mult" in ids
    assert "flag" in ids
    progress = registry.get("session_progress_mult")
    assert progress.value_type == "number"
    assert progress.aggregation == "multiply"
    assert progress.cap_max == 1.25
    assert progress.allowed_contexts == ["cultivate_session"]


def test_load_default_bundles_validate(bundles: EffectBundleCatalog) -> None:
    assert bundles.get("bundle_fixture_quiet_breath").id == "bundle_fixture_quiet_breath"


def test_unknown_effect_type_fails_bundle_validation(registry: EffectTypeRegistry) -> None:
    bundle = EffectBundle(
        id="bad",
        schema_version=1,
        effects=[
            EffectSpec(
                type="not_a_real_type",
                params={"mult": 1.1},
                applies_to=["cultivate_session"],
            )
        ],
    )
    with pytest.raises(EngineValidationError, match="Unknown effect type"):
        validate_bundle_against_registry(bundle, registry)


def test_applies_to_outside_allowed_contexts_fails(registry: EffectTypeRegistry) -> None:
    spec = EffectSpec(
        type="session_progress_mult",
        params={"mult": 1.05},
        applies_to=["combat"],
    )
    with pytest.raises(EngineValidationError, match="allowed_contexts"):
        validate_effect_spec(spec, registry.get("session_progress_mult"))


def test_wrong_param_key_fails(registry: EffectTypeRegistry) -> None:
    spec = EffectSpec(
        type="session_progress_mult",
        params={"flat": 2},
        applies_to=["cultivate_session"],
    )
    with pytest.raises(EngineValidationError, match="requires params.mult"):
        validate_effect_spec(spec, registry.get("session_progress_mult"))


def test_sum_flats_and_multiply_mults(
    registry: EffectTypeRegistry,
    bundles: EffectBundleCatalog,
) -> None:
    actor = "actor-1"
    instances = [
        EffectInstance(
            source_kind="test_fixture",
            source_id="a",
            actor_id=actor,
            inline_effects=[
                EffectSpec(
                    type="session_stability_flat",
                    params={"flat": 2},
                    applies_to=["cultivate_session"],
                ),
                EffectSpec(
                    type="session_progress_mult",
                    params={"mult": 1.1},
                    applies_to=["cultivate_session"],
                ),
            ],
        ),
        EffectInstance(
            source_kind="test_fixture",
            source_id="b",
            actor_id=actor,
            inline_effects=[
                EffectSpec(
                    type="session_stability_flat",
                    params={"flat": 1},
                    applies_to=["cultivate_session"],
                ),
                EffectSpec(
                    type="session_progress_mult",
                    params={"mult": 1.1},
                    applies_to=["cultivate_session"],
                ),
            ],
        ),
    ]
    snap = aggregate(
        instances,
        ModifierContext(actor_id=actor, world_day=1, activity="cultivate_session"),
        type_registry=registry,
        bundles=bundles,
    )
    assert snap.number("session_stability_flat") == pytest.approx(3.0)
    assert snap.number("session_progress_mult") == pytest.approx(1.21)


def test_caps_clamp_results(
    registry: EffectTypeRegistry,
    bundles: EffectBundleCatalog,
) -> None:
    actor = "actor-1"
    instances = [
        EffectInstance(
            source_kind="test_fixture",
            source_id="overcap",
            actor_id=actor,
            inline_effects=[
                EffectSpec(
                    type="session_progress_mult",
                    params={"mult": 1.2},
                    applies_to=["cultivate_session"],
                ),
                EffectSpec(
                    type="session_stability_flat",
                    params={"flat": 10},
                    applies_to=["cultivate_session"],
                ),
            ],
        ),
        EffectInstance(
            source_kind="test_fixture",
            source_id="overcap2",
            actor_id=actor,
            inline_effects=[
                EffectSpec(
                    type="session_progress_mult",
                    params={"mult": 1.2},
                    applies_to=["cultivate_session"],
                ),
            ],
        ),
    ]
    snap = aggregate(
        instances,
        ModifierContext(actor_id=actor, world_day=1, activity="cultivate_session"),
        type_registry=registry,
        bundles=bundles,
    )
    assert snap.number("session_progress_mult") == pytest.approx(1.25)
    assert snap.number("session_stability_flat") == pytest.approx(5.0)


def test_flags_or_across_sources(
    registry: EffectTypeRegistry,
    bundles: EffectBundleCatalog,
) -> None:
    actor = "actor-1"
    instances = [
        EffectInstance(
            source_kind="test_fixture",
            source_id="f1",
            actor_id=actor,
            inline_effects=[
                EffectSpec(
                    type="flag",
                    params={"flag": "can_sense_qi_flow"},
                    applies_to=["cultivate_session"],
                )
            ],
        ),
        EffectInstance(
            source_kind="test_fixture",
            source_id="f2",
            actor_id=actor,
            inline_effects=[
                EffectSpec(
                    type="flag",
                    params={"flag": "steady_breath"},
                    applies_to=["cultivate_session"],
                )
            ],
        ),
    ]
    snap = aggregate(
        instances,
        ModifierContext(actor_id=actor, world_day=1, activity="cultivate_session"),
        type_registry=registry,
        bundles=bundles,
    )
    assert snap.has_flag("can_sense_qi_flow")
    assert snap.has_flag("steady_breath")
    assert not snap.has_flag("missing_flag")


def test_context_filter_ignores_other_activities(
    registry: EffectTypeRegistry,
    bundles: EffectBundleCatalog,
) -> None:
    actor = "actor-1"
    instances = [
        EffectInstance(
            source_kind="test_fixture",
            source_id="session_only",
            actor_id=actor,
            inline_effects=[
                EffectSpec(
                    type="session_progress_mult",
                    params={"mult": 1.1},
                    applies_to=["cultivate_session"],
                )
            ],
        ),
        EffectInstance(
            source_kind="test_fixture",
            source_id="bt",
            actor_id=actor,
            inline_effects=[
                EffectSpec(
                    type="breakthrough_chance_flat",
                    params={"flat": 0.03},
                    applies_to=["breakthrough"],
                )
            ],
        ),
    ]
    session_snap = aggregate(
        instances,
        ModifierContext(actor_id=actor, world_day=1, activity="cultivate_session"),
        type_registry=registry,
        bundles=bundles,
    )
    assert "session_progress_mult" in session_snap.numbers
    assert "breakthrough_chance_flat" not in session_snap.numbers

    bt_snap = aggregate(
        instances,
        ModifierContext(actor_id=actor, world_day=1, activity="breakthrough"),
        type_registry=registry,
        bundles=bundles,
    )
    assert "breakthrough_chance_flat" in bt_snap.numbers
    assert "session_progress_mult" not in bt_snap.numbers


def test_expiration_excludes_instances(
    registry: EffectTypeRegistry,
    bundles: EffectBundleCatalog,
) -> None:
    actor = "actor-1"
    instances = [
        EffectInstance(
            source_kind="temporary_status",
            source_id="expired",
            actor_id=actor,
            expires_world_day=10,
            inline_effects=[
                EffectSpec(
                    type="session_stability_flat",
                    params={"flat": 3},
                    applies_to=["cultivate_session"],
                )
            ],
        ),
        EffectInstance(
            source_kind="temporary_status",
            source_id="active",
            actor_id=actor,
            expires_world_day=20,
            inline_effects=[
                EffectSpec(
                    type="session_stability_flat",
                    params={"flat": 1},
                    applies_to=["cultivate_session"],
                )
            ],
        ),
    ]
    snap = aggregate(
        instances,
        ModifierContext(actor_id=actor, world_day=10, activity="cultivate_session"),
        type_registry=registry,
        bundles=bundles,
    )
    assert snap.number("session_stability_flat") == pytest.approx(1.0)


def test_actor_filter(
    registry: EffectTypeRegistry,
    bundles: EffectBundleCatalog,
) -> None:
    instances = [
        EffectInstance(
            source_kind="test_fixture",
            source_id="other",
            actor_id="other-actor",
            inline_effects=[
                EffectSpec(
                    type="session_stability_flat",
                    params={"flat": 4},
                    applies_to=["cultivate_session"],
                )
            ],
        )
    ]
    snap = aggregate(
        instances,
        ModifierContext(actor_id="actor-1", world_day=1, activity="cultivate_session"),
        type_registry=registry,
        bundles=bundles,
    )
    assert snap.numbers == {}
    assert snap.flags == frozenset()


def test_bundle_resolution(
    registry: EffectTypeRegistry,
    bundles: EffectBundleCatalog,
) -> None:
    snap = aggregate(
        [
            EffectInstance(
                source_kind="technique_mastery",
                source_id="tech_quiet_breath",
                actor_id="actor-1",
                bundle_id="bundle_fixture_quiet_breath",
            )
        ],
        ModifierContext(actor_id="actor-1", world_day=1, activity="cultivate_session"),
        type_registry=registry,
        bundles=bundles,
    )
    assert snap.number("session_progress_mult") == pytest.approx(1.05)
    assert snap.number("comprehension_gain_mult") == pytest.approx(1.05)


def test_magnitude_scale_on_mult_and_flat(
    registry: EffectTypeRegistry,
    bundles: EffectBundleCatalog,
) -> None:
    actor = "actor-1"
    instances = [
        EffectInstance(
            source_kind="test_fixture",
            source_id="scaled",
            actor_id=actor,
            magnitude_scale=0.5,
            inline_effects=[
                EffectSpec(
                    type="session_progress_mult",
                    params={"mult": 1.10},
                    applies_to=["cultivate_session"],
                ),
                EffectSpec(
                    type="session_stability_flat",
                    params={"flat": 4},
                    applies_to=["cultivate_session"],
                ),
            ],
        )
    ]
    snap = aggregate(
        instances,
        ModifierContext(actor_id=actor, world_day=1, activity="cultivate_session"),
        type_registry=registry,
        bundles=bundles,
    )
    assert snap.number("session_progress_mult") == pytest.approx(1.05)
    assert snap.number("session_stability_flat") == pytest.approx(2.0)


def test_aggregate_is_deterministic(
    registry: EffectTypeRegistry,
    bundles: EffectBundleCatalog,
) -> None:
    instances = [
        EffectInstance(
            source_kind="technique_mastery",
            source_id="tech_quiet_breath",
            actor_id="actor-1",
            bundle_id="bundle_fixture_quiet_breath",
        ),
        EffectInstance(
            source_kind="test_fixture",
            source_id="extra",
            actor_id="actor-1",
            inline_effects=[
                EffectSpec(
                    type="flag",
                    params={"flag": "steady_breath"},
                    applies_to=["cultivate_session"],
                )
            ],
        ),
    ]
    context = ModifierContext(actor_id="actor-1", world_day=3, activity="cultivate_session")
    a = aggregate(instances, context, type_registry=registry, bundles=bundles)
    b = aggregate(instances, context, type_registry=registry, bundles=bundles)
    assert a.numbers == b.numbers
    assert a.flags == b.flags
    assert a.contributions == b.contributions


def test_audit_trail_explains_contributions(
    registry: EffectTypeRegistry,
    bundles: EffectBundleCatalog,
) -> None:
    snap = aggregate(
        [
            EffectInstance(
                source_kind="technique_mastery",
                source_id="tech_quiet_breath",
                actor_id="actor-1",
                bundle_id="bundle_fixture_quiet_breath",
            )
        ],
        ModifierContext(actor_id="actor-1", world_day=1, activity="cultivate_session"),
        type_registry=registry,
        bundles=bundles,
    )
    assert len(snap.contributions) == 2
    sources = {(c.source_kind, c.source_id, c.effect_type) for c in snap.contributions}
    assert ("technique_mastery", "tech_quiet_breath", "session_progress_mult") in sources
    assert ("technique_mastery", "tech_quiet_breath", "comprehension_gain_mult") in sources


def test_corrupt_registry_file_fails(tmp_path: Path) -> None:
    path = tmp_path / "bad_types.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(EngineValidationError, match="Corrupted effect type registry"):
        load_effect_type_registry(str(path))


def test_invalid_registry_inconsistent_rules(tmp_path: Path) -> None:
    path = tmp_path / "bad_rules.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "effect_types": [
                    {
                        "id": "broken",
                        "value_type": "number",
                        "aggregation": "or",
                        "param_key": "flag",
                        "identity": False,
                        "allowed_contexts": ["cultivate_session"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(EngineValidationError, match="Invalid effect type registry"):
        load_effect_type_registry(str(path))


def test_instance_requires_exactly_one_effect_source() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        EffectInstance(
            source_kind="test_fixture",
            source_id="x",
            actor_id="a",
            bundle_id="bundle_fixture_quiet_breath",
            inline_effects=[
                EffectSpec(
                    type="session_progress_mult",
                    params={"mult": 1.05},
                    applies_to=["cultivate_session"],
                )
            ],
        )
