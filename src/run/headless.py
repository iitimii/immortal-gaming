"""Headless simulation runner.

Creates a world through the same initialization flow the server uses for
"Start Game", then steps the simulator for a number of months without the web
server or frontend. Intended for balancing and regression checks.

The run is always in rule-based test mode (``RunConfig.test_mode=True``): no
real LLM request or connectivity check is ever made.

Usage::

    python -m src.run.headless --months 120 --seed 42 --json summary.json
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import io
import json
import math
import random
import sys
import tempfile
import time
import traceback
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Optional

TOP_SECTS_LIMIT = 5
TOP_AVATARS_LIMIT = 5
PROGRESS_EVERY_MONTHS = 12


class HeadlessRunError(RuntimeError):
    """Raised when world initialization or a simulator step fails."""


@dataclass(slots=True)
class HeadlessOptions:
    months: int = 120
    seed: Optional[int] = None
    map_id: Optional[str] = None
    avatars: Optional[int] = None
    sects: Optional[int] = None
    save: bool = False
    json_path: Optional[str] = None
    quiet: bool = False
    verbose: bool = False


class _InitConfigView:
    """Static CONFIG view whose saves dir points at a private scratch directory.

    The init flow creates its working events database under ``config.paths.saves``.
    Headless runs keep that scratch database out of the user's saves dir; ``--save``
    copies it next to the final save file through the normal save path.
    """

    def __init__(self, base: Any, saves_dir: Path):
        self._base = base
        self.paths = SimpleNamespace(saves=saves_dir)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base, name)


def _refuse_connectivity_check() -> tuple[bool, str]:
    raise HeadlessRunError("LLM connectivity check must never run in headless test mode")


def resolve_default_map_id() -> str:
    from src.run.map_presets import DEFAULT_MAP_ID, list_map_presets

    for preset in list_map_presets():
        if preset.is_default:
            return preset.id
    return DEFAULT_MAP_ID


def build_run_config(options: HeadlessOptions):
    """Build the per-run config from bundled defaults plus CLI overrides.

    User ``settings.json`` new-game defaults are intentionally ignored so a run
    is reproducible from its command line alone.
    """
    from src.config import RunConfig

    overrides: dict[str, Any] = {
        "test_mode": True,
        "map_id": options.map_id or resolve_default_map_id(),
    }
    if options.avatars is not None:
        overrides["init_npc_num"] = int(options.avatars)
    if options.sects is not None:
        overrides["sect_num"] = int(options.sects)
    return RunConfig(**overrides)


async def initialize_world(run_config, *, scratch_dir: Path):
    """Create a world through the server's real initialization flow.

    Returns ``(runtime, world, sim)``. Raises ``HeadlessRunError`` if
    initialization does not reach the ``ready`` state.
    """
    from src.classes.core.sect import sects_by_id
    from src.classes.core.world import World
    from src.classes.event import Event
    from src.classes.language import language_manager
    from src.classes.world_lore import WorldLoreManager
    from src.classes.world_lore_snapshot import build_world_lore_snapshot
    from src.i18n import t
    from src.run.data_loader import reload_all_static_data
    from src.run.load_map import load_cultivation_world_map
    from src.server.init_flow import perform_game_initialization
    from src.server.init_runtime import update_init_progress
    from src.server.public_helpers import (
        apply_runtime_content_locale,
        get_runtime_run_config,
        model_to_dict,
        reset_runtime_custom_content,
        scan_avatar_assets,
    )
    from src.server.runtime import GameSessionRuntime, create_default_game_state
    from src.sim import get_events_db_path
    from src.sim.avatar_init import make_avatars
    from src.sim.simulator import Simulator
    from src.systems.dynasty_generator import generate_dynasty, generate_emperor
    from src.systems.time import Month, Year, create_month_stamp
    from src.utils.config import CONFIG

    runtime = GameSessionRuntime(create_default_game_state())
    apply_runtime_content_locale(
        runtime=runtime,
        language_manager=language_manager,
        lang_code=run_config.content_locale,
    )
    runtime.set_run_config(run_config.model_dump())
    runtime.mark_pending_initialization(clear_world=True)

    project_root = Path(__file__).resolve().parents[2]
    await perform_game_initialization(
        runtime=runtime,
        avatar_assets={},
        assets_path=str(project_root / "assets"),
        config=_InitConfigView(CONFIG, scratch_dir),
        update_init_progress=lambda phase, phase_name="": update_init_progress(
            runtime=runtime, phase=phase, phase_name=phase_name
        ),
        reset_runtime_custom_content=reset_runtime_custom_content,
        reload_all_static_data=reload_all_static_data,
        scan_avatar_assets=scan_avatar_assets,
        load_cultivation_world_map=load_cultivation_world_map,
        get_events_db_path=get_events_db_path,
        get_runtime_run_config=get_runtime_run_config,
        world_cls=World,
        create_month_stamp=create_month_stamp,
        year_cls=Year,
        month_enum=Month,
        generate_dynasty=generate_dynasty,
        generate_emperor=generate_emperor,
        event_cls=Event,
        translate=t,
        simulator_cls=Simulator,
        model_to_dict=model_to_dict,
        world_lore_manager_cls=WorldLoreManager,
        build_world_lore_snapshot=build_world_lore_snapshot,
        sects_by_id=sects_by_id,
        make_random_avatars=make_avatars,
        check_llm_connectivity=_refuse_connectivity_check,
    )

    if runtime.get("init_status") != "ready":
        raise HeadlessRunError(
            f"World initialization failed: {runtime.get('init_error') or 'unknown error'}"
        )
    return runtime, runtime.get_world(), runtime.get_simulator()


# --------------------------------------------------------------------------- #
# Run statistics
# --------------------------------------------------------------------------- #


@dataclass(slots=True)
class _RunStats:
    step_times_ms: list[float]
    events: list[Any]
    births: int = 0
    awakenings: int = 0
    deaths: int = 0


def _date_dict(month_stamp) -> dict[str, int]:
    return {
        "year": int(month_stamp.get_year()),
        "month": int(month_stamp.get_month().value),
    }


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100.0 * len(ordered)))
    return ordered[rank - 1]


def build_summary(*, world, stats: _RunStats, run_config, seed: int,
                  start_date: dict[str, int]) -> dict[str, Any]:
    from src.systems.cultivation import REALM_ORDER

    avatar_manager = world.avatar_manager
    living = list(avatar_manager.get_living_avatars())

    realm_counts = Counter(avatar.cultivation_progress.realm for avatar in living)
    realm_distribution = {realm.value: int(realm_counts.get(realm, 0)) for realm in REALM_ORDER}

    sect_members: Counter = Counter()
    sect_names: dict[int, str] = {}
    unaffiliated = 0
    for avatar in living:
        sect = avatar.sect
        if sect is None:
            unaffiliated += 1
            continue
        sect_members[sect.id] += 1
        sect_names[sect.id] = sect.name
    top_sects = [
        {"id": sect_id, "name": sect_names[sect_id], "members": count}
        for sect_id, count in sorted(sect_members.items(), key=lambda kv: (-kv[1], sect_names[kv[0]]))
    ][:TOP_SECTS_LIMIT]

    per_avatar: Counter = Counter()
    for event in stats.events:
        for avatar_id in set(event.related_avatars or []):
            per_avatar[str(avatar_id)] += 1
    top_avatars = []
    for avatar_id, count in sorted(per_avatar.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP_AVATARS_LIMIT]:
        avatar = avatar_manager.get_avatar(avatar_id)
        top_avatars.append(
            {
                "id": avatar_id,
                "name": getattr(avatar, "name", None) or avatar_id,
                "events": count,
                "is_dead": bool(getattr(avatar, "is_dead", False)) if avatar is not None else None,
            }
        )

    step_times = stats.step_times_ms
    return {
        "seed": seed,
        "map_id": run_config.map_id,
        "init_npc_num": int(run_config.init_npc_num),
        "sect_num": int(run_config.sect_num),
        "test_mode": bool(run_config.test_mode),
        "months_simulated": len(step_times),
        "start_date": start_date,
        "final_date": _date_dict(world.month_stamp),
        "population": {
            "living": len(living),
            "dead": len(avatar_manager.dead_avatars),
            "deaths_during_run": stats.deaths,
            "awakenings": stats.awakenings,
            "births": stats.births,
        },
        "realm_distribution": realm_distribution,
        "top_sects": top_sects,
        "unaffiliated": unaffiliated,
        "events": {
            "total": len(stats.events),
            "major": sum(1 for event in stats.events if event.is_major),
            "story": sum(1 for event in stats.events if event.is_story),
        },
        "top_event_avatars": top_avatars,
        "step_time_ms": {
            "avg": round(sum(step_times) / len(step_times), 2) if step_times else 0.0,
            "p95": round(_percentile(step_times, 95), 2),
            "max": round(max(step_times), 2) if step_times else 0.0,
            "total": round(sum(step_times), 2),
        },
        "save_file": None,
    }


def format_summary_text(summary: dict[str, Any]) -> str:
    from src.systems.cultivation import Realm

    def _date(d: dict[str, int]) -> str:
        return f"Year {d['year']}, Month {d['month']}"

    pop = summary["population"]
    events = summary["events"]
    labels = [str(Realm(value)) for value in summary["realm_distribution"]]
    labels += [sect["name"] for sect in summary["top_sects"]]
    labels += [entry["name"] + " (dead)" for entry in summary["top_event_avatars"]]
    width = max([len(label) for label in labels] + [len("(no sect)")]) + 2
    timing = summary["step_time_ms"]
    lines = [
        "=== Headless simulation summary ===",
        f"Seed: {summary['seed']}   Map: {summary['map_id']}   "
        f"Initial NPCs: {summary['init_npc_num']}   Sects: {summary['sect_num']}",
        f"Months simulated: {summary['months_simulated']} "
        f"({_date(summary['start_date'])} -> {_date(summary['final_date'])})",
        f"Population: {pop['living']} living, {pop['dead']} dead "
        f"({pop['deaths_during_run']} died during run), "
        f"{pop['awakenings']} awakenings, {pop['births']} births",
        "Realm distribution (living):",
    ]
    for realm_value, count in summary["realm_distribution"].items():
        lines.append(f"  {str(Realm(realm_value)):<{width}}{count}")
    lines.append("Top sects by members:")
    if summary["top_sects"]:
        for sect in summary["top_sects"]:
            lines.append(f"  {sect['name']:<{width}}{sect['members']}")
    else:
        lines.append("  (none)")
    lines.append(f"  {'(no sect)':<{width}}{summary['unaffiliated']}")
    lines.append(
        f"Events: {events['total']} total, {events['major']} major, {events['story']} story"
    )
    lines.append("Top event-producing avatars:")
    if summary["top_event_avatars"]:
        for entry in summary["top_event_avatars"]:
            suffix = " (dead)" if entry["is_dead"] else ""
            lines.append(f"  {entry['name'] + suffix:<{width}}{entry['events']}")
    else:
        lines.append("  (none)")
    lines.append(
        f"Step time: avg {timing['avg']:.1f} ms, p95 {timing['p95']:.1f} ms, "
        f"max {timing['max']:.1f} ms, total {timing['total'] / 1000:.2f} s"
    )
    if summary.get("save_file"):
        lines.append(f"Saved: {summary['save_file']}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #


async def run_headless(
    options: HeadlessOptions,
    *,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Initialize a world, step it ``options.months`` times and return a summary."""
    from src.utils.llm.runtime_mode import llm_test_mode_scope

    if options.months < 0:
        raise ValueError("months must be >= 0")
    seed = options.seed if options.seed is not None else random.SystemRandom().randrange(2**31)
    random.seed(seed)
    run_config = build_run_config(options)
    report = progress or (lambda _msg: None)

    with tempfile.TemporaryDirectory(prefix="cws-headless-") as scratch, llm_test_mode_scope(True):
        report(f"Initializing world (map={run_config.map_id}, seed={seed}, test_mode=on)...")
        runtime, world, sim = await initialize_world(run_config, scratch_dir=Path(scratch))
        try:
            # Discard change buffers produced during initialization.
            world.avatar_manager.pop_newly_born()
            world.avatar_manager.pop_newly_dead()
            start_date = _date_dict(world.month_stamp)
            stats = _RunStats(step_times_ms=[], events=[])
            known_mortals = set(world.mortal_manager.mortals)

            for index in range(options.months):
                started = time.perf_counter()
                try:
                    events = await runtime.run_mutation(sim.step)
                except Exception as exc:
                    raise HeadlessRunError(
                        f"Simulator step {index + 1} failed: {type(exc).__name__}: {exc}"
                    ) from exc
                stats.step_times_ms.append((time.perf_counter() - started) * 1000.0)
                stats.events.extend(events or [])
                stats.awakenings += len(world.avatar_manager.pop_newly_born())
                stats.deaths += len(world.avatar_manager.pop_newly_dead())
                current_mortals = set(world.mortal_manager.mortals)
                stats.births += len(current_mortals - known_mortals)
                known_mortals = current_mortals

                done = index + 1
                if done % PROGRESS_EVERY_MONTHS == 0 or done == options.months:
                    report(
                        f"  month {done}/{options.months}: "
                        f"{len(world.avatar_manager.avatars)} living, {len(stats.events)} events"
                    )

            summary = build_summary(
                world=world,
                stats=stats,
                run_config=run_config,
                seed=seed,
                start_date=start_date,
            )

            if options.save:
                from src.sim import save_game

                success, filename = save_game(world, sim, list(world.existed_sects or []))
                if not success:
                    raise HeadlessRunError("Saving the world failed")
                summary["save_file"] = filename
            return summary
        finally:
            world.event_manager.close()


def _non_negative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected an integer, got {value!r}") from None
    if parsed < 0:
        raise argparse.ArgumentTypeError(f"must be >= 0, got {parsed}")
    return parsed


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.run.headless",
        description=(
            "Run the cultivation world simulator without the web server, "
            "in rule-based test mode (no LLM calls)."
        ),
    )
    parser.add_argument("--months", type=_non_negative_int, default=120,
                        help="number of months to simulate (default: 120)")
    parser.add_argument("--seed", type=int, default=None,
                        help="random seed; same seed and options give the same summary "
                             "(default: random, printed in the summary)")
    parser.add_argument("--map", dest="map_id", default=None,
                        help="map preset id (default: the default preset)")
    parser.add_argument("--avatars", type=_non_negative_int, default=None,
                        help="initial NPC count (default: the bundled new-game default)")
    parser.add_argument("--sects", type=_non_negative_int, default=None,
                        help="number of sects in the world (default: the bundled new-game default)")
    parser.add_argument("--json", dest="json_path", metavar="PATH", default=None,
                        help="write the summary as JSON to PATH ('-' for stdout)")
    parser.add_argument("--save", action="store_true",
                        help="save the world at the end through the normal save path "
                             "(honours CWS_DATA_DIR)")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--quiet", action="store_true", help="suppress progress output")
    output.add_argument("--verbose", action="store_true",
                        help="show the engine's own console output")
    return parser


def parse_options(argv: list[str] | None = None) -> HeadlessOptions:
    """Parse CLI arguments; exits with code 2 on invalid arguments."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.map_id is not None:
        # Config modules print on import; keep stdout clean for `--json -`.
        with contextlib.redirect_stdout(sys.stderr):
            from src.run.map_presets import list_map_presets

        available = [preset.id for preset in list_map_presets()]
        if args.map_id not in available:
            parser.error(f"unknown map preset {args.map_id!r} (available: {', '.join(available)})")
    return HeadlessOptions(
        months=args.months,
        seed=args.seed,
        map_id=args.map_id,
        avatars=args.avatars,
        sects=args.sects,
        save=args.save,
        json_path=args.json_path,
        quiet=args.quiet,
        verbose=args.verbose,
    )


def main(argv: list[str] | None = None) -> int:
    options = parse_options(argv)

    def progress(message: str) -> None:
        if not options.quiet:
            print(message, file=sys.stderr, flush=True)

    engine_output = io.StringIO()
    redirect = contextlib.nullcontext() if options.verbose else contextlib.redirect_stdout(engine_output)
    try:
        with redirect:
            summary = asyncio.run(run_headless(options, progress=progress))
    except Exception as exc:
        captured = engine_output.getvalue().strip()
        if captured:
            tail = "\n".join(captured.splitlines()[-40:])
            print(f"--- engine output (last lines) ---\n{tail}", file=sys.stderr)
        traceback.print_exc()
        print(f"Error: headless simulation failed: {exc}", file=sys.stderr)
        return 1

    if options.json_path == "-":
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0
    if options.json_path:
        try:
            path = Path(options.json_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        except OSError as exc:
            print(f"Error: could not write JSON summary to {options.json_path}: {exc}", file=sys.stderr)
            return 1
        progress(f"JSON summary written to {options.json_path}")
    print(format_summary_text(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
