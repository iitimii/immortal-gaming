import re
import tempfile
from pathlib import Path

from src.classes.core.world import World
from src.classes.core.sect import Sect, SectHeadQuarter
from src.classes.alignment import Alignment
from src.classes.event import Event
from src.classes.event_storage import EventStorage
from src.classes.language import language_manager
from src.i18n import reload_translations
from src.sim.managers.sect_manager import SectManager
from src.systems.time import MonthStamp
from src.systems.sect_decision_context import build_sect_decision_context, SectDecisionContext


def _create_world_with_sects(base_world: World) -> tuple[World, Sect, Sect]:
    """
    Build a world on top of the standard base_world with two sects and a sect headquarters region.

    - sect1: has a headquarters region, producing influence territory and income;
    - sect2: no headquarters region, used only for relation calculations.
    """
    world: World = base_world
    game_map = world.map

    # Register a SectRegion for sect1 so it has a headquarters center and territory
    from src.classes.environment.sect_region import SectRegion

    r1_id = 1001
    cors1 = [(0, 0)]
    r1 = SectRegion(id=r1_id, name="R1", desc="", sect_id=1, sect_name="Test Sect 1", cors=cors1)
    game_map.regions[r1_id] = r1
    game_map.region_cors[r1_id] = cors1
    game_map.update_sect_regions()

    hq = SectHeadQuarter(name="Test Headquarters", desc="", image=Path(""))
    sect1 = Sect(
        id=1,
        name="Test Sect 1",
        desc="",
        member_act_style="",
        alignment=Alignment.NEUTRAL,
        headquarter=hq,
        technique_names=[],
    )
    sect2 = Sect(
        id=2,
        name="Test Sect 2",
        desc="",
        member_act_style="",
        alignment=Alignment.EVIL,
        headquarter=hq,
        technique_names=[],
    )

    world.existed_sects = [sect1, sect2]
    world.sect_context.from_existed_sects(world.existed_sects)

    return world, sect1, sect2


def _create_event_storage_with_sect_events(sect_id: int) -> EventStorage:
    """Create a temporary EventStorage and write a few events related to the given sect."""
    tmpdir = tempfile.TemporaryDirectory()
    db_path = Path(tmpdir.name) / "sect_events.db"
    storage = EventStorage(db_path)

    # Three events with increasing month_stamp
    e1 = Event(month_stamp=MonthStamp(1), content="E1", related_sects=[sect_id])
    e2 = Event(month_stamp=MonthStamp(2), content="E2", related_sects=[sect_id])
    e3 = Event(month_stamp=MonthStamp(3), content="E3", related_sects=[sect_id])
    for ev in (e1, e2, e3):
        storage.add_event(ev)

    # Attach the temp dir to the instance for manual cleanup after the test
    storage._tmpdir = tmpdir  # type: ignore[attr-defined]
    return storage


def _cleanup_event_storage(storage: EventStorage) -> None:
    """Close and clean up the temporary EventStorage."""
    tmpdir = getattr(storage, "_tmpdir", None)
    storage.close()
    if tmpdir is not None:
        tmpdir.cleanup()


def test_build_sect_decision_context_basic(base_world):
    """Base snapshot: should include static info, current strength/influence, economy and history events."""
    world, sect1, sect2 = _create_world_with_sects(base_world)

    # Run update_sects first so strength, radius and income are up to date
    manager = SectManager(world)
    manager.update_sects()

    storage = _create_event_storage_with_sect_events(sect1.id)
    try:
        ctx = build_sect_decision_context(sect1, world, storage, history_limit=2)
    finally:
        _cleanup_event_storage(storage)

    assert isinstance(ctx, SectDecisionContext)

    # Basic info
    assert ctx.basic_structured["name"] == sect1.name
    assert sect1.name in ctx.basic_text

    # Influence and strength: should match the current sect fields and have at least a radius
    assert ctx.power["influence_radius"] == sect1.influence_radius
    assert ctx.power["total_battle_strength"] == sect1.total_battle_strength
    assert ctx.territory["tile_count"] >= 0

    # Economy: reads current fields and income derived from territory tiles only
    assert ctx.economy["current_magic_stone"] == sect1.magic_stone
    assert ctx.economy["effective_income_per_tile"] >= 0.0
    assert ctx.economy["controlled_tile_income"] == ctx.economy["effective_income_per_tile"] * ctx.territory["tile_count"]
    assert "estimated_member_upkeep" in ctx.economy
    assert "estimated_net_annual_balance" in ctx.economy
    assert "treasury_pressure" in ctx.economy
    assert isinstance(ctx.economy["member_upkeep_breakdown"], list)
    assert ctx.rule["rule_id"] == ""
    assert ctx.identity["purpose"] == sect1.desc
    assert ctx.identity["rule_desc"] == sect1.rule_desc
    assert ctx.self_assessment["war_weariness"] == 0
    assert isinstance(ctx.recruitment_candidates, list)
    assert isinstance(ctx.member_candidates, list)

    # History events: only the latest N are kept
    recent = ctx.history["recent_events"]
    assert len(recent) == 2
    # The latest two should be the events with month_stamp 2 and 3
    stamps = [int(e.month_stamp) for e in recent]
    assert stamps == [2, 3]
    summary = ctx.history["summary_text"]
    assert "E2" in summary and "E3" in summary


def test_build_sect_decision_context_relations(base_world):
    """Relations snapshot: should include current relations with other sects."""
    world, sect1, sect2 = _create_world_with_sects(base_world)

    manager = SectManager(world)
    manager.update_sects()

    storage = _create_event_storage_with_sect_events(sect1.id)
    try:
        ctx = build_sect_decision_context(sect1, world, storage, history_limit=0)
    finally:
        _cleanup_event_storage(storage)

    # Should include at least one relation record with sect2
    others = {r["other_sect_id"] for r in ctx.relations}
    assert sect2.id in others

    # Relation values should be within [-100, 100]
    for r in ctx.relations:
        assert -100 <= r["value"] <= 100

    # relations_summary should at least include the total count
    assert f"total={len(ctx.relations)}" in ctx.relations_summary
    assert isinstance(ctx.diplomacy_targets, list)
    assert ctx.diplomacy_targets
    assert ctx.diplomacy_targets[0]["status"] in {"war", "peace"}


def test_build_sect_decision_context_localizes_runtime_notes(base_world):
    world, sect1, _ = _create_world_with_sects(base_world)

    manager = SectManager(world)
    manager.update_sects()

    storage = _create_event_storage_with_sect_events(sect1.id)
    original_lang = str(language_manager)
    try:
        language_manager._current = "en-US"
        reload_translations()
        ctx = build_sect_decision_context(sect1, world, storage, history_limit=1)
    finally:
        _cleanup_event_storage(storage)
        language_manager._current = original_lang
        reload_translations()

    assert ctx.economy["action_cost_notes"]
    assert all(not re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", note) for note in ctx.economy["action_cost_notes"])
    assert "spirit stones" in ctx.economy["action_cost_notes"][0]
    assert "[3] E3" in ctx.history["summary_text"]

