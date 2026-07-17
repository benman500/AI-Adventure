"""Developer tooling for the event catalog: validation, inspection, simulation, stats.

These helpers are engine-side (no HTTP, no DB writes). Persistence simulation is
explicitly dry-run only.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from random import Random
from typing import Any, Literal

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
from ai_adventure.engine.errors import EngineValidationError
from ai_adventure.engine.events import (
    ALLOWED_EFFECT_TYPES,
    ALLOWED_TRIGGER_KINDS,
    EventContext,
    EventFile,
    EventManifest,
    EventTemplate,
    _EVENTS_DIR,
    clear_event_catalog_cache,
    evaluate_trigger,
    load_event_catalog,
)

IssueSeverity = Literal["error", "warning"]

_MODIFY_CULTIVATION_KEYS = frozenset(
    {
        "qi_reserve_delta",
        "cultivation_progress_delta",
        "realm_comprehension_delta",
        "foundation_stability_delta",
    }
)


@dataclass(frozen=True, slots=True)
class CatalogIssue:
    """One validation finding."""

    severity: IssueSeverity
    code: str
    message: str
    event_id: str | None = None
    source_file: str | None = None


@dataclass(frozen=True, slots=True)
class CatalogValidationReport:
    """Result of a full catalog audit."""

    ok: bool
    event_count: int
    file_count: int
    issues: tuple[CatalogIssue, ...]
    events_by_file: dict[str, tuple[str, ...]] = field(default_factory=dict)

    @property
    def errors(self) -> tuple[CatalogIssue, ...]:
        return tuple(i for i in self.issues if i.severity == "error")

    @property
    def warnings(self) -> tuple[CatalogIssue, ...]:
        return tuple(i for i in self.issues if i.severity == "warning")


@dataclass(frozen=True, slots=True)
class EventStats:
    """Aggregate catalog statistics for developer inspection."""

    total_events: int
    enabled_events: int
    disabled_events: int
    by_category: dict[str, int]
    by_trigger_kind: dict[str, int]
    one_time_count: int
    repeatable_count: int
    with_ai_prompt_key: int
    total_weight_by_trigger: dict[str, int]
    files: dict[str, int]


@dataclass(frozen=True, slots=True)
class SimulationTrialResult:
    """One dry-run trigger evaluation."""

    trial: int
    fired: bool
    template_id: str | None
    no_event_reason: str | None
    effects: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class SimulationReport:
    """Aggregate dry-run simulation (no persistence)."""

    trigger_kind: str
    trials: int
    seed: int
    fire_count: int
    miss_count: int
    by_template: dict[str, int]
    by_no_event_reason: dict[str, int]
    fire_rate: float
    trials_detail: tuple[SimulationTrialResult, ...]


def _default_cultivation(*, path_status: str = PATH_STATUS_CONFIRMED_ORDINARY) -> CultivationState:
    return CultivationState(
        cultivation_path=STARTING_CULTIVATION_PATH,
        path_status=path_status,
        realm_id=STARTING_REALM_ID,
        stage_id=STARTING_STAGE_ID,
        body=STARTING_BODY,
        qi=STARTING_QI,
        soul=STARTING_SOUL,
        dao=STARTING_DAO,
        foundation_quality=STARTING_FOUNDATION_QUALITY,
        qi_reserve_current=5,
        qi_reserve_max=10,
        cultivation_progress=40,
        realm_comprehension=STARTING_REALM_COMPREHENSION,
        foundation_stability=STARTING_FOUNDATION_STABILITY,
        practice_sessions=0,
        anomaly_state="none",
        breakthrough_readiness="not_ready",
    )


def _scan_manifest_files(events_dir: Path) -> tuple[EventManifest, list[tuple[str, EventFile]]]:
    """Load manifest + each content file (raises EngineValidationError on hard failures)."""

    manifest_path = events_dir / "event_manifest.json"
    if not manifest_path.is_file():
        raise EngineValidationError(f"Event manifest missing: {manifest_path}")
    try:
        manifest = EventManifest.model_validate(
            json.loads(manifest_path.read_text(encoding="utf-8"))
        )
    except json.JSONDecodeError as exc:
        raise EngineValidationError("Corrupted event manifest") from exc
    except Exception as exc:  # noqa: BLE001
        raise EngineValidationError(f"Invalid event manifest: {exc}") from exc

    loaded: list[tuple[str, EventFile]] = []
    for relative in manifest.content_files:
        path = events_dir / relative
        if not path.is_file():
            raise EngineValidationError(f"Event content file missing: {relative}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            file_model = EventFile.model_validate(raw)
        except json.JSONDecodeError as exc:
            raise EngineValidationError(f"Corrupted event file: {relative}") from exc
        except Exception as exc:  # noqa: BLE001
            raise EngineValidationError(f"Invalid event file {relative}: {exc}") from exc
        loaded.append((relative, file_model))
    return manifest, loaded


def _validate_effect_payloads(template: EventTemplate, source_file: str) -> list[CatalogIssue]:
    issues: list[CatalogIssue] = []
    for index, effect in enumerate(template.effects):
        if effect.type not in ALLOWED_EFFECT_TYPES:
            issues.append(
                CatalogIssue(
                    severity="error",
                    code="unknown_effect_type",
                    message=f"effects[{index}] unknown type {effect.type!r}",
                    event_id=template.id,
                    source_file=source_file,
                )
            )
            continue
        payload = effect.payload
        if effect.type == "modify_cultivation":
            unknown = set(payload) - _MODIFY_CULTIVATION_KEYS
            if unknown:
                issues.append(
                    CatalogIssue(
                        severity="error",
                        code="invalid_effect_payload",
                        message=f"modify_cultivation unknown keys: {sorted(unknown)}",
                        event_id=template.id,
                        source_file=source_file,
                    )
                )
            for key, value in payload.items():
                if key in _MODIFY_CULTIVATION_KEYS and not isinstance(value, int):
                    issues.append(
                        CatalogIssue(
                            severity="error",
                            code="invalid_effect_payload",
                            message=f"modify_cultivation.{key} must be int",
                            event_id=template.id,
                            source_file=source_file,
                        )
                    )
        elif effect.type == "modify_money":
            if "copper_delta" not in payload:
                issues.append(
                    CatalogIssue(
                        severity="error",
                        code="invalid_effect_payload",
                        message="modify_money requires copper_delta",
                        event_id=template.id,
                        source_file=source_file,
                    )
                )
        elif effect.type == "grant_item":
            if not payload.get("item_code") or int(payload.get("quantity", 0)) < 1:
                issues.append(
                    CatalogIssue(
                        severity="error",
                        code="invalid_effect_payload",
                        message="grant_item requires item_code and quantity >= 1",
                        event_id=template.id,
                        source_file=source_file,
                    )
                )
        elif effect.type == "advance_world_days":
            days = payload.get("days", 0)
            if not isinstance(days, int) or days < 0:
                issues.append(
                    CatalogIssue(
                        severity="error",
                        code="invalid_effect_payload",
                        message="advance_world_days.days must be int >= 0",
                        event_id=template.id,
                        source_file=source_file,
                    )
                )
        elif effect.type == "set_flag":
            if not str(payload.get("flag", "")).strip():
                issues.append(
                    CatalogIssue(
                        severity="error",
                        code="invalid_effect_payload",
                        message="set_flag requires non-empty flag",
                        event_id=template.id,
                        source_file=source_file,
                    )
                )
    return issues


def validate_event_catalog(events_dir: str | Path | None = None) -> CatalogValidationReport:
    """Audit the event catalog: schema, duplicates, effect payloads, soft warnings."""

    root = Path(events_dir) if events_dir else _EVENTS_DIR
    issues: list[CatalogIssue] = []
    events_by_file: dict[str, list[str]] = defaultdict(list)
    seen_ids: dict[str, str] = {}
    seen_prompt_keys: dict[str, str] = {}

    try:
        _manifest, loaded = _scan_manifest_files(root)
    except EngineValidationError as exc:
        return CatalogValidationReport(
            ok=False,
            event_count=0,
            file_count=0,
            issues=(
                CatalogIssue(
                    severity="error",
                    code="catalog_load_failed",
                    message=str(exc),
                ),
            ),
        )

    # Orphan JSON files in the directory not listed in the manifest.
    listed = {rel for rel, _ in loaded}
    for path in sorted(root.glob("*.json")):
        if path.name == "event_manifest.json":
            continue
        if path.name not in listed:
            issues.append(
                CatalogIssue(
                    severity="warning",
                    code="orphan_event_file",
                    message=f"JSON file not listed in manifest: {path.name}",
                    source_file=path.name,
                )
            )

    all_templates: list[EventTemplate] = []
    for relative, file_model in loaded:
        for template in file_model.events:
            events_by_file[relative].append(template.id)
            if template.id in seen_ids:
                issues.append(
                    CatalogIssue(
                        severity="error",
                        code="duplicate_event_id",
                        message=(
                            f"Duplicate event id {template.id!r} in {relative} "
                            f"(also defined in {seen_ids[template.id]})"
                        ),
                        event_id=template.id,
                        source_file=relative,
                    )
                )
            else:
                seen_ids[template.id] = relative

            if template.ai_prompt_key:
                prior = seen_prompt_keys.get(template.ai_prompt_key)
                if prior and prior != template.id:
                    issues.append(
                        CatalogIssue(
                            severity="warning",
                            code="duplicate_ai_prompt_key",
                            message=(
                                f"ai_prompt_key {template.ai_prompt_key!r} reused by "
                                f"{template.id} and {prior}"
                            ),
                            event_id=template.id,
                            source_file=relative,
                        )
                    )
                else:
                    seen_prompt_keys[template.ai_prompt_key] = template.id

            if not template.presentation.placeholder_text.strip():
                issues.append(
                    CatalogIssue(
                        severity="error",
                        code="empty_placeholder",
                        message="presentation.placeholder_text is blank",
                        event_id=template.id,
                        source_file=relative,
                    )
                )

            for kind in template.trigger.kinds:
                if kind not in ALLOWED_TRIGGER_KINDS:
                    issues.append(
                        CatalogIssue(
                            severity="error",
                            code="unknown_trigger_kind",
                            message=f"Unknown trigger kind {kind!r}",
                            event_id=template.id,
                            source_file=relative,
                        )
                    )

            issues.extend(_validate_effect_payloads(template, relative))

            if template.weight < 1:
                issues.append(
                    CatalogIssue(
                        severity="error",
                        code="invalid_weight",
                        message="weight must be >= 1",
                        event_id=template.id,
                        source_file=relative,
                    )
                )

            if not template.enabled:
                issues.append(
                    CatalogIssue(
                        severity="warning",
                        code="disabled_event",
                        message="Event is disabled",
                        event_id=template.id,
                        source_file=relative,
                    )
                )

            all_templates.append(template)

    # Ensure merged catalog load still succeeds (Pydantic + unique ids).
    try:
        clear_event_catalog_cache()
        load_event_catalog(str(root))
    except EngineValidationError as exc:
        issues.append(
            CatalogIssue(
                severity="error",
                code="catalog_merge_failed",
                message=str(exc),
            )
        )

    errors = [i for i in issues if i.severity == "error"]
    return CatalogValidationReport(
        ok=len(errors) == 0,
        event_count=len(all_templates),
        file_count=len(loaded),
        issues=tuple(issues),
        events_by_file={k: tuple(v) for k, v in events_by_file.items()},
    )


def assert_event_catalog_valid(events_dir: str | Path | None = None) -> CatalogValidationReport:
    """Validate catalog and raise EngineValidationError if any errors exist."""

    report = validate_event_catalog(events_dir)
    if not report.ok:
        details = "; ".join(f"[{i.code}] {i.message}" for i in report.errors[:8])
        raise EngineValidationError(
            f"Event catalog validation failed ({len(report.errors)} error(s)): {details}"
        )
    return report


def collect_event_stats(events_dir: str | Path | None = None) -> EventStats:
    """Compute aggregate statistics for the catalog."""

    root = Path(events_dir) if events_dir else _EVENTS_DIR
    report = validate_event_catalog(root)
    if not report.ok:
        raise EngineValidationError("Cannot collect stats: catalog has errors")

    clear_event_catalog_cache()
    catalog = load_event_catalog(str(root))
    by_category: Counter[str] = Counter()
    by_trigger: Counter[str] = Counter()
    weight_by_trigger: Counter[str] = Counter()
    one_time = 0
    repeatable = 0
    with_prompt = 0
    enabled = 0
    disabled = 0
    files = {name: len(ids) for name, ids in report.events_by_file.items()}

    for event in catalog.events:
        by_category[event.category] += 1
        if event.enabled:
            enabled += 1
        else:
            disabled += 1
        if event.is_one_time:
            one_time += 1
        else:
            repeatable += 1
        if event.ai_prompt_key:
            with_prompt += 1
        for kind in event.trigger.kinds:
            by_trigger[kind] += 1
            if event.enabled:
                weight_by_trigger[kind] += event.weight

    return EventStats(
        total_events=len(catalog.events),
        enabled_events=enabled,
        disabled_events=disabled,
        by_category=dict(sorted(by_category.items())),
        by_trigger_kind=dict(sorted(by_trigger.items())),
        one_time_count=one_time,
        repeatable_count=repeatable,
        with_ai_prompt_key=with_prompt,
        total_weight_by_trigger=dict(sorted(weight_by_trigger.items())),
        files=dict(sorted(files.items())),
    )


def inspect_event(event_id: str, events_dir: str | Path | None = None) -> dict[str, Any]:
    """Return a structured dump of one event template for debugging."""

    root = Path(events_dir) if events_dir else _EVENTS_DIR
    clear_event_catalog_cache()
    catalog = load_event_catalog(str(root))
    template = catalog.get(event_id)
    source_file = None
    report = validate_event_catalog(root)
    for file_name, ids in report.events_by_file.items():
        if event_id in ids:
            source_file = file_name
            break
    return {
        "source_file": source_file,
        "template": template.model_dump(),
        "is_one_time": template.is_one_time,
        "is_repeatable": template.is_repeatable,
        "trigger_kinds": list(template.trigger.kinds),
        "effect_types": [e.type for e in template.effects],
    }


def list_event_summaries(
    *,
    events_dir: str | Path | None = None,
    category: str | None = None,
    trigger_kind: str | None = None,
    enabled_only: bool = False,
) -> list[dict[str, Any]]:
    """List compact event rows for developer browsing."""

    root = Path(events_dir) if events_dir else _EVENTS_DIR
    clear_event_catalog_cache()
    catalog = load_event_catalog(str(root))
    rows: list[dict[str, Any]] = []
    for event in catalog.events:
        if category and event.category != category:
            continue
        if trigger_kind and trigger_kind not in event.trigger.kinds:
            continue
        if enabled_only and not event.enabled:
            continue
        rows.append(
            {
                "id": event.id,
                "label": event.label,
                "category": event.category,
                "enabled": event.enabled,
                "weight": event.weight,
                "chance": event.trigger.chance,
                "trigger_kinds": list(event.trigger.kinds),
                "cooldown_days": event.cooldown_days,
                "max_fires_per_save": event.max_fires_per_save,
                "ai_prompt_key": event.ai_prompt_key,
            }
        )
    return rows


def simulate_trigger(
    trigger_kind: str,
    *,
    trials: int = 1000,
    seed: int = 1,
    events_dir: str | Path | None = None,
    path_status: str = PATH_STATUS_CONFIRMED_ORDINARY,
    world_day: int = 10,
    include_trial_details: bool = False,
) -> SimulationReport:
    """Dry-run a trigger many times without persistence.

    Uses a fresh eligible pool each trial (no cooldown accumulation) so the
    report reflects base weights/chances for the given context snapshot.
    """

    if trials < 1:
        raise EngineValidationError("trials must be >= 1")
    if trigger_kind not in ALLOWED_TRIGGER_KINDS:
        raise EngineValidationError(f"Unknown trigger kind: {trigger_kind}")

    root = Path(events_dir) if events_dir else _EVENTS_DIR
    assert_event_catalog_valid(root)
    clear_event_catalog_cache()
    catalog = load_event_catalog(str(root))

    context = EventContext(
        save_id="sim-save",
        subject=ActorRef(actor_id="sim-actor", kind="player"),
        world_day=world_day,
        location_id="sim_location",
        story_flags={},
        cultivation=_default_cultivation(path_status=path_status),
        money_copper=100,
        trigger_kind=trigger_kind,
        cooldowns=(),
    )

    rng = Random(seed)
    by_template: Counter[str] = Counter()
    by_reason: Counter[str] = Counter()
    fire_count = 0
    details: list[SimulationTrialResult] = []

    for trial in range(trials):
        batch = evaluate_trigger(context, rng=rng, catalog=catalog)
        resolution = batch.first_resolution
        if resolution is not None:
            fire_count += 1
            by_template[resolution.template_id] += 1
            if include_trial_details:
                details.append(
                    SimulationTrialResult(
                        trial=trial,
                        fired=True,
                        template_id=resolution.template_id,
                        no_event_reason=None,
                        effects=tuple(
                            {"type": e.type, "payload": e.payload}
                            for e in resolution.effects_applied
                        ),
                    )
                )
        else:
            reason = batch.first_no_event.reason if batch.first_no_event else "unknown"
            by_reason[reason] += 1
            if include_trial_details:
                details.append(
                    SimulationTrialResult(
                        trial=trial,
                        fired=False,
                        template_id=None,
                        no_event_reason=reason,
                        effects=(),
                    )
                )

    return SimulationReport(
        trigger_kind=trigger_kind,
        trials=trials,
        seed=seed,
        fire_count=fire_count,
        miss_count=trials - fire_count,
        by_template=dict(sorted(by_template.items(), key=lambda kv: (-kv[1], kv[0]))),
        by_no_event_reason=dict(sorted(by_reason.items())),
        fire_rate=fire_count / trials,
        trials_detail=tuple(details),
    )


def report_to_dict(report: CatalogValidationReport) -> dict[str, Any]:
    """Serialize a validation report for CLI/JSON output."""

    return {
        "ok": report.ok,
        "event_count": report.event_count,
        "file_count": report.file_count,
        "error_count": len(report.errors),
        "warning_count": len(report.warnings),
        "issues": [
            {
                "severity": i.severity,
                "code": i.code,
                "message": i.message,
                "event_id": i.event_id,
                "source_file": i.source_file,
            }
            for i in report.issues
        ],
        "events_by_file": {k: list(v) for k, v in report.events_by_file.items()},
    }


def stats_to_dict(stats: EventStats) -> dict[str, Any]:
    """Serialize event stats for CLI/JSON output."""

    return {
        "total_events": stats.total_events,
        "enabled_events": stats.enabled_events,
        "disabled_events": stats.disabled_events,
        "by_category": stats.by_category,
        "by_trigger_kind": stats.by_trigger_kind,
        "one_time_count": stats.one_time_count,
        "repeatable_count": stats.repeatable_count,
        "with_ai_prompt_key": stats.with_ai_prompt_key,
        "total_weight_by_trigger": stats.total_weight_by_trigger,
        "files": stats.files,
    }


def simulation_to_dict(report: SimulationReport) -> dict[str, Any]:
    """Serialize a simulation report for CLI/JSON output."""

    return {
        "trigger_kind": report.trigger_kind,
        "trials": report.trials,
        "seed": report.seed,
        "fire_count": report.fire_count,
        "miss_count": report.miss_count,
        "fire_rate": round(report.fire_rate, 4),
        "by_template": report.by_template,
        "by_no_event_reason": report.by_no_event_reason,
    }
