from unittest.mock import AsyncMock, patch

import pytest

from src.classes.alignment import Alignment
from src.classes.language import language_manager
from src.classes.core.sect import Sect
from src.classes.items.weapon import Weapon, WeaponType
from src.classes.technique import Technique, TechniqueAttribute, TechniqueGrade
from src.i18n import reload_translations, t
from src.classes.world_lore import WorldLore, WorldLoreManager
from src.classes.world_lore_snapshot import apply_world_lore_snapshot, build_world_lore_snapshot
from src.systems.world_lore_rewrite import apply_world_lore_rewrite, build_world_lore_context, build_world_lore_jobs
from src.systems.world_lore_rewrite.models import EntityRewrite, WorldLoreRewriteDraft, WorldLoreRewriteConfig
from src.systems.world_lore_rewrite.runner import WorldLoreRewriteRunner
from src.classes.items.auxiliary import auxiliaries_by_id
from src.classes.items.weapon import weapons_by_id
from src.classes.core.sect import sects_by_id
from src.classes.core.world import World
from src.run.load_map import load_cultivation_world_map
from src.run.data_loader import reload_all_static_data
from src.sim.load.load_game import load_game
from src.sim.save.save_game import save_game
from src.sim.simulator import Simulator
from src.systems.time import Month, Year, create_month_stamp
from src.systems.cultivation import Realm
from src.classes.technique import techniques_by_id

import src.classes.core.sect as sect_module
import src.classes.items.weapon as weapon_module
import src.classes.technique as technique_module

_real_apply_world_lore = WorldLoreManager.apply_world_lore


def test_world_lore_structure(base_world):
    assert isinstance(base_world.world_lore, WorldLore)
    assert base_world.world_lore.text == ""

    lore_text = "A cultivation world crowded with sects, where the righteous and the demonic stand opposed."
    base_world.set_world_lore(lore_text)
    assert base_world.world_lore.text == lore_text
    assert t("World lore and history") not in base_world.static_info
    assert lore_text not in str(base_world.get_info())


def test_world_lore_static_info_key_is_localized(base_world):
    original_lang = str(language_manager)
    try:
        language_manager._current = "en-US"
        reload_translations()
        base_world.set_world_lore("Sects rise and fall under rewritten heavens.")
        assert "World lore and history" not in base_world.static_info
    finally:
        language_manager._current = original_lang
        reload_translations()


def test_world_lore_apply_updates_indexes(base_world):
    sect = Sect(
        id=1,
        name="Old Sect",
        desc="Old description",
        member_act_style="",
        alignment=Alignment.RIGHTEOUS,
        headquarter=None,
        technique_names=[],
    )
    technique = Technique(
        id=1,
        name="Old Technique",
        attribute=TechniqueAttribute.GOLD,
        grade=TechniqueGrade.LOWER,
        desc="Old technique description",
        weight=1.0,
        condition="",
    )
    weapon = Weapon(
        id=101,
        name="Old Spirit Sword",
        weapon_type=WeaponType.SWORD,
        realm=Realm.Qi_Refinement,
        desc="Old weapon description",
    )

    draft = WorldLoreRewriteDraft(
        sects={1: EntityRewrite(id=1, name="New Sect", desc="New description")},
        techniques={1: EntityRewrite(id=1, name="New Technique", desc="New technique description")},
        weapons={101: EntityRewrite(id=101, name="New Spirit Sword", desc="New weapon description")},
    )

    with patch.dict(sect_module.sects_by_id, {1: sect}, clear=True), \
         patch.dict(sect_module.sects_by_name, {"Old Sect": sect}, clear=True), \
         patch.dict(technique_module.techniques_by_id, {1: technique}, clear=True), \
         patch.dict(technique_module.techniques_by_name, {"Old Technique": technique}, clear=True), \
         patch.dict(weapon_module.weapons_by_id, {101: weapon}, clear=True), \
         patch.dict(weapon_module.weapons_by_name, {"Old Spirit Sword": weapon}, clear=True):
        apply_world_lore_rewrite(base_world, draft)

        assert sect.name == "New Sect"
        assert sect.desc == "New description"
        assert "Old Sect" not in sect_module.sects_by_name
        assert sect_module.sects_by_name["New Sect"] is sect

        assert technique.name == "New Technique"
        assert technique.desc == "New technique description"
        assert "Old Technique" not in technique_module.techniques_by_name
        assert technique_module.techniques_by_name["New Technique"] is technique

        assert weapon.name == "New Spirit Sword"
        assert weapon.desc == "New weapon description"
        assert "Old Spirit Sword" not in weapon_module.weapons_by_name
        assert weapon_module.weapons_by_name["New Spirit Sword"] is weapon


def test_world_lore_syncs_sect_region_metadata():
    world = World(
        map=load_cultivation_world_map(),
        month_stamp=create_month_stamp(Year(1), Month.JANUARY),
    )
    sect = next(iter(sects_by_id.values()))
    region = next(r for r in world.map.sect_regions.values() if getattr(r, "sect_id", None) == sect.id)

    apply_world_lore_rewrite(
        world,
        WorldLoreRewriteDraft(
            sects={sect.id: EntityRewrite(id=sect.id, name="Great Void Sect", desc="New sect description")},
            regions={region.id: EntityRewrite(id=region.id, name="Great Void Celestial Palace", desc="New headquarters description")},
        ),
    )

    assert sect.name == "Great Void Sect"
    assert region.name == "Great Void Celestial Palace"
    assert region.sect_name == "Great Void Sect"
    assert sect.headquarter.name == "Great Void Celestial Palace"
    assert sect.headquarter.desc == "New headquarters description"
    reload_all_static_data()


def test_world_lore_planner_uses_current_map_and_overrides():
    world = World(
        map=load_cultivation_world_map("island_seas"),
        month_stamp=create_month_stamp(Year(1), Month.JANUARY),
    )
    context = build_world_lore_context(world, "Archipelago world in the Dharma-Ending Age")
    jobs = build_world_lore_jobs(context)
    region_jobs = [job for job in jobs if job.kind == "regions"]

    assert context.map_summary["map_id"] == "island_seas"
    assert context.map_summary["wilderness_tile"] == "sea"
    assert region_jobs
    all_region_inputs = [entity for job in region_jobs for entity in job.entities]
    assert {entity["id"] for entity in all_region_inputs} <= set(world.map.regions)
    assert any(entity["map_override"] for entity in all_region_inputs)


@pytest.mark.asyncio
async def test_world_lore_runner_uses_rewrite_tasks_and_fallback(base_world):
    from src.systems.world_lore_rewrite.models import RewriteJob, WorldLoreRewriteContext

    context = WorldLoreRewriteContext(
        world=base_world,
        lore_text="Dharma-Ending wasteland",
        map_summary={"map_id": "test"},
        style_guide={},
        config=WorldLoreRewriteConfig(
            task_timeout_seconds=5,
            total_timeout_seconds=10,
            max_parse_retries=1,
            min_retry_budget_seconds=1,
        ),
    )
    job = RewriteJob(
        id="regions#1",
        kind="regions",
        task_name="world_lore_region_rewrite",
        entities=[{"id": 1, "name": "Old Town", "desc": "Old description"}],
        entity_label="location",
        instructions="Rewrite locations",
        result_field="entities",
        map_summary=context.map_summary,
        style_guide=context.style_guide,
        lore_text=context.lore_text,
    )

    async def fake_call(**kwargs):
        assert kwargs["task_name"] == "world_lore_region_rewrite"
        return {"entities": [{"id": 1, "name": "New Town", "desc": "An old town reshaped by wind, sand and the setting sun."}]}

    with patch("src.systems.world_lore_rewrite.runner.call_llm_with_task_name", new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = fake_call
        partial = await WorldLoreRewriteRunner(context)._run_job(job, 9999999999)

    assert partial.regions[1].name == "New Town"
    assert partial.llm_count == 1


def test_save_load_preserves_world_lore(base_world, tmp_path):
    base_world.set_world_lore("After the ancient great war, the order of the sects was rewritten.")
    simulator = Simulator(base_world)
    save_path = tmp_path / "world_lore_save.json"

    ok, _ = save_game(base_world, simulator, [], save_path)
    assert ok is True

    loaded_world, _, _ = load_game(save_path)
    assert loaded_world.world_lore.text == "After the ancient great war, the order of the sects was rewritten."


def test_world_lore_snapshot_reapplies_static_changes():
    world = World(
        map=load_cultivation_world_map(),
        month_stamp=create_month_stamp(Year(1), Month.JANUARY),
    )
    region_id = next(iter(world.map.regions))
    sect_id = next(iter(sects_by_id))
    technique_id = next(iter(techniques_by_id))
    weapon_id = next(iter(weapons_by_id))
    auxiliary_id = next(iter(auxiliaries_by_id))

    world.map.regions[region_id].name = "Great Void Ancient City"
    world.map.regions[region_id].desc = "Rewritten region description"
    sects_by_id[sect_id].name = "Great Void Sect"
    sects_by_id[sect_id].desc = "Rewritten sect description"
    techniques_by_id[technique_id].name = "Great Void Mystic Art"
    techniques_by_id[technique_id].desc = "Rewritten technique description"
    weapons_by_id[weapon_id].name = "Great Void Sword"
    weapons_by_id[weapon_id].desc = "Rewritten weapon description"
    auxiliaries_by_id[auxiliary_id].name = "Great Void Pendant"
    auxiliaries_by_id[auxiliary_id].desc = "Rewritten auxiliary description"

    snapshot = build_world_lore_snapshot(world)

    reload_all_static_data()
    fresh_world = World(
        map=load_cultivation_world_map(),
        month_stamp=create_month_stamp(Year(1), Month.JANUARY),
    )
    apply_world_lore_snapshot(fresh_world, snapshot)

    assert fresh_world.map.regions[region_id].name == "Great Void Ancient City"
    assert fresh_world.map.regions[region_id].desc == "Rewritten region description"
    assert sects_by_id[sect_id].name == "Great Void Sect"
    assert sects_by_id[sect_id].desc == "Rewritten sect description"
    assert techniques_by_id[technique_id].name == "Great Void Mystic Art"
    assert weapons_by_id[weapon_id].name == "Great Void Sword"
    assert auxiliaries_by_id[auxiliary_id].name == "Great Void Pendant"


def test_world_lore_snapshot_rebuilds_sect_metadata_links():
    world = World(
        map=load_cultivation_world_map(),
        month_stamp=create_month_stamp(Year(1), Month.JANUARY),
    )
    sect_id = next(iter(sects_by_id))
    region = next(r for r in world.map.sect_regions.values() if getattr(r, "sect_id", None) == sect_id)

    sects_by_id[sect_id].name = "Heavenly Secrets Pavilion"
    sects_by_id[sect_id].desc = "Keeper of heaven's numbers and hidden lore."
    region.name = "Stargazing Terrace"
    region.desc = "A high terrace from which the stars of the nine heavens can be observed."

    snapshot = build_world_lore_snapshot(world)

    reload_all_static_data()
    fresh_world = World(
        map=load_cultivation_world_map(),
        month_stamp=create_month_stamp(Year(1), Month.JANUARY),
    )
    apply_world_lore_snapshot(fresh_world, snapshot)

    fresh_region = next(r for r in fresh_world.map.sect_regions.values() if getattr(r, "sect_id", None) == sect_id)
    assert sects_by_id[sect_id].name == "Heavenly Secrets Pavilion"
    assert fresh_region.sect_name == "Heavenly Secrets Pavilion"
    assert sects_by_id[sect_id].headquarter.name == "Stargazing Terrace"
    assert sects_by_id[sect_id].headquarter.desc == "A high terrace from which the stars of the nine heavens can be observed."
    reload_all_static_data()


def test_save_load_preserves_world_lore_snapshot_after_static_reload(tmp_path):
    world = World(
        map=load_cultivation_world_map(),
        month_stamp=create_month_stamp(Year(1), Month.JANUARY),
    )
    region_id = next(iter(world.map.regions))
    sect_id = next(iter(sects_by_id))
    technique_id = next(iter(techniques_by_id))
    weapon_id = next(iter(weapons_by_id))

    world.set_world_lore("The shape of the world has been rewritten.")
    world.map.regions[region_id].name = "Heavenly Secrets City"
    world.map.regions[region_id].desc = "Stargazing terraces fill the city."
    sects_by_id[sect_id].name = "Heavenly Secrets Pavilion"
    sects_by_id[sect_id].desc = "Keeper of heaven's numbers and hidden lore."
    techniques_by_id[technique_id].name = "Heavenly Secrets Dao-Deduction Art"
    techniques_by_id[technique_id].desc = "Deduces the Great Dao from the stars."
    weapons_by_id[weapon_id].name = "Heavenly Secrets Ruler"
    weapons_by_id[weapon_id].desc = "Can fix the bearings of mountains and rivers."
    world.world_lore_snapshot = build_world_lore_snapshot(world)

    simulator = Simulator(world)
    save_path = tmp_path / "world_lore_snapshot_save.json"
    ok, _ = save_game(world, simulator, [], save_path)
    assert ok is True

    reload_all_static_data()

    loaded_world, _, _ = load_game(save_path)
    assert loaded_world.world_lore.text == "The shape of the world has been rewritten."
    assert loaded_world.map.regions[region_id].name == "Heavenly Secrets City"
    assert loaded_world.map.regions[region_id].desc == "Stargazing terraces fill the city."
    assert sects_by_id[sect_id].name == "Heavenly Secrets Pavilion"
    assert sects_by_id[sect_id].desc == "Keeper of heaven's numbers and hidden lore."
    assert techniques_by_id[technique_id].name == "Heavenly Secrets Dao-Deduction Art"
    assert techniques_by_id[technique_id].desc == "Deduces the Great Dao from the stars."
    assert weapons_by_id[weapon_id].name == "Heavenly Secrets Ruler"
    assert weapons_by_id[weapon_id].desc == "Can fix the bearings of mountains and rivers."
