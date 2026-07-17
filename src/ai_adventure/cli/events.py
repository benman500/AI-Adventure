"""CLI for event catalog validation, inspection, simulation, and stats."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from ai_adventure.engine.event_devtools import (
    assert_event_catalog_valid,
    collect_event_stats,
    inspect_event,
    list_event_summaries,
    report_to_dict,
    simulate_trigger,
    simulation_to_dict,
    stats_to_dict,
    validate_event_catalog,
)
from ai_adventure.engine.errors import EngineValidationError


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _cmd_validate(args: argparse.Namespace) -> int:
    report = validate_event_catalog(args.events_dir)
    _print_json(report_to_dict(report))
    return 0 if report.ok else 1


def _cmd_stats(args: argparse.Namespace) -> int:
    try:
        stats = collect_event_stats(args.events_dir)
    except EngineValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    _print_json(stats_to_dict(stats))
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    try:
        assert_event_catalog_valid(args.events_dir)
        rows = list_event_summaries(
            events_dir=args.events_dir,
            category=args.category,
            trigger_kind=args.trigger,
            enabled_only=args.enabled_only,
        )
    except EngineValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    _print_json(rows)
    return 0


def _cmd_inspect(args: argparse.Namespace) -> int:
    try:
        assert_event_catalog_valid(args.events_dir)
        payload = inspect_event(args.event_id, args.events_dir)
    except EngineValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    _print_json(payload)
    return 0


def _cmd_simulate(args: argparse.Namespace) -> int:
    try:
        report = simulate_trigger(
            args.trigger,
            trials=args.trials,
            seed=args.seed,
            events_dir=args.events_dir,
            path_status=args.path_status,
            world_day=args.world_day,
            include_trial_details=args.details,
        )
    except EngineValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    payload = simulation_to_dict(report)
    if args.details:
        payload["trials_detail"] = [
            {
                "trial": t.trial,
                "fired": t.fired,
                "template_id": t.template_id,
                "no_event_reason": t.no_event_reason,
                "effects": list(t.effects),
            }
            for t in report.trials_detail
        ]
    _print_json(payload)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the event tooling argument parser."""

    parser = argparse.ArgumentParser(
        prog="ai-adventure-events",
        description="Event catalog developer tools (validate, inspect, simulate, stats).",
    )
    parser.add_argument(
        "--events-dir",
        default=None,
        help="Optional alternate events directory (defaults to packaged data/events).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="Validate schema, duplicates, and effect payloads")
    validate.set_defaults(func=_cmd_validate)

    stats = sub.add_parser("stats", help="Print catalog statistics")
    stats.set_defaults(func=_cmd_stats)

    list_cmd = sub.add_parser("list", help="List event summaries")
    list_cmd.add_argument("--category", default=None)
    list_cmd.add_argument("--trigger", default=None, help="Filter by trigger kind")
    list_cmd.add_argument("--enabled-only", action="store_true")
    list_cmd.set_defaults(func=_cmd_list)

    inspect_cmd = sub.add_parser("inspect", help="Inspect one event template")
    inspect_cmd.add_argument("event_id")
    inspect_cmd.set_defaults(func=_cmd_inspect)

    sim = sub.add_parser("simulate", help="Dry-run trigger evaluations (no persistence)")
    sim.add_argument("trigger", help="Trigger kind, e.g. after_cultivation_session")
    sim.add_argument("--trials", type=int, default=1000)
    sim.add_argument("--seed", type=int, default=1)
    sim.add_argument("--path-status", default="confirmed_ordinary")
    sim.add_argument("--world-day", type=int, default=10)
    sim.add_argument("--details", action="store_true", help="Include per-trial rows")
    sim.set_defaults(func=_cmd_simulate)

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""

    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
