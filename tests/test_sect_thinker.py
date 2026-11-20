import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.classes.sect_thinker import SectThinker
from src.classes.language import language_manager
from src.i18n import reload_translations
from src.i18n.locale_registry import get_default_locale, get_project_root
from src.systems.sect_decision_context import SectDecisionContext


class _DummySect:
    def __init__(self, name: str):
        self.name = name


class _DummyPhenomenon:
    def __init__(self, name: str, desc: str):
        self.name = name
        self.desc = desc


class _DummyWorld:
    def __init__(self):
        self.current_phenomenon = _DummyPhenomenon("Heaven Tide", "Spiritual qi surges")
        self.world_lore = type("WorldLore", (), {"text": ""})()

    def get_info(self, detailed: bool = False):
        return {"world_state": "stable", "detailed": detailed}


def _dummy_ctx() -> SectDecisionContext:
    return SectDecisionContext(
        basic_structured={"name": "Test Sect"},
        basic_text="Test sect detailed info",
        identity={
            "purpose": "guard the sect rules and lineage",
            "style": "acts with caution",
            "orthodoxy_name": "Immortal Dao",
            "rule_desc": "Never collude with demonic cultivators.",
        },
        power={"total_battle_strength": 100.0, "influence_radius": 2},
        territory={"tile_count": 5, "conflict_tile_count": 1, "headquarter_center": (1, 1)},
        self_assessment={
            "member_count": 0,
            "alive_member_count": 0,
            "peak_member_realm": "",
            "patriarch_realm": "",
            "war_readiness": "stable",
            "resource_pressure": "normal",
            "can_afford_recruit_count": 0,
            "can_afford_support_count": 0,
        },
        economy={
            "current_magic_stone": 200,
            "effective_income_per_tile": 10.0,
            "controlled_tile_income": 50.0,
            "treasury_pressure": "tight",
            "estimated_member_upkeep": 30,
            "estimated_net_annual_balance": 20,
            "action_cost_notes": [
                "Recruiting newcomers increases future upkeep costs.",
                "Granting techniques consumes the sect's lineage resources.",
            ],
        },
        rule={"rule_id": "righteous_orthodoxy", "rule_desc": "Never collude with demonic cultivators."},
        recruitment_candidates=[],
        member_candidates=[],
        relations=[],
        relations_summary="total=0",
        history={"recent_events": [], "summary_text": ""},
    )


@pytest.mark.asyncio
async def test_sect_thinker_returns_llm_content_when_valid():
    sect = _DummySect("Qingyun Sect")
    world = _DummyWorld()
    ctx = _dummy_ctx()

    payload = {
        "sect_thinking": "Our sect has made its choices: first secure our borders and resources, then steadily grow our disciples and lineage to seize the initiative in the middle game."
    }
    with patch.object(SectThinker, "_llm_available", return_value=True), patch(
        "src.classes.sect_thinker.call_llm_with_task_name",
        return_value=payload,
    ) as mock_llm:
        text = await SectThinker.think(sect, ctx, world, decision_summary="Recruited 1 rogue cultivator.")

    assert text == payload["sect_thinking"][: SectThinker.MAX_LEN]
    kwargs = mock_llm.call_args.kwargs
    assert kwargs["infos"]["decision_summary"] == "Recruited 1 rogue cultivator."
    assert "guard the sect rules and lineage" in kwargs["infos"]["decision_context_info"]
    assert "upkeep costs" in kwargs["infos"]["decision_context_info"]
    assert kwargs["infos"]["world_lore"] == ""


@pytest.mark.asyncio
async def test_sect_thinker_falls_back_when_llm_unavailable():
    sect = _DummySect("Qingyun Sect")
    world = _DummyWorld()
    ctx = _dummy_ctx()
    original_lang = str(language_manager)

    mock_service = MagicMock()
    mock_service.get_llm_runtime_config.return_value = (
        type("Profile", (), {"base_url": "", "model_name": "", "fast_model_name": ""})(),
        "",
    )
    try:
        language_manager._current = get_default_locale()
        reload_translations()
        with patch("src.classes.sect_thinker.get_settings_service", return_value=mock_service), patch(
            "src.classes.sect_thinker.get_logger"
        ) as mock_logger:
            text = await SectThinker.think(sect, ctx, world)

        assert text.startswith("Our sect")
        assert SectThinker.MIN_LEN <= len(text) <= SectThinker.MAX_LEN
        assert "LLM runtime config unavailable" in mock_logger.return_value.logger.warning.call_args.args[-1]
    finally:
        language_manager._current = original_lang
        reload_translations()


def test_sect_thinker_llm_available_uses_runtime_config():
    mock_service = MagicMock()
    mock_service.get_llm_runtime_config.return_value = (
        type("Profile", (), {"base_url": "http://test", "model_name": "test-model", "fast_model_name": "test-fast"})(),
        "secret",
    )
    with patch("src.classes.sect_thinker.get_settings_service", return_value=mock_service):
        assert SectThinker._llm_available() is True


@pytest.mark.asyncio
async def test_sect_thinker_warns_when_response_too_short():
    sect = _DummySect("Qingyun Sect")
    world = _DummyWorld()
    ctx = _dummy_ctx()
    original_lang = str(language_manager)
    mock_service = MagicMock()
    mock_service.get_llm_runtime_config.return_value = (
        type("Profile", (), {"base_url": "http://test", "model_name": "test-model", "fast_model_name": "test-fast"})(),
        "secret",
    )

    try:
        language_manager._current = get_default_locale()
        reload_translations()
        with patch("src.classes.sect_thinker.get_settings_service", return_value=mock_service), patch(
            "src.classes.sect_thinker.call_llm_with_task_name",
            return_value={"sect_thinking": "Too short"},
        ), patch("src.classes.sect_thinker.get_logger") as mock_logger:
            text = await SectThinker.think(sect, ctx, world)

        assert text.startswith("Our sect")
        assert "LLM response too short" in mock_logger.return_value.logger.warning.call_args.args[-1]
    finally:
        language_manager._current = original_lang
        reload_translations()


def test_sect_thinker_current_phenomenon_info_uses_i18n_fallback_text():
    original_lang = str(language_manager)
    try:
        language_manager._current = get_default_locale()
        reload_translations()
        world = type("World", (), {"current_phenomenon": None})()
        assert SectThinker._current_phenomenon_info(world) == "There is currently no celestial phenomenon."

        world.current_phenomenon = type("Phenomenon", (), {"name": "", "desc": ""})()
        assert SectThinker._current_phenomenon_info(world) == "A celestial phenomenon is present, but its description is missing."
    finally:
        language_manager._current = original_lang
        reload_translations()


def test_sect_thinker_template_forces_english_output():
    template_path = (
        get_project_root() / "static" / "locales" / get_default_locale() / "templates" / "sect_thinker.txt"
    )
    content = template_path.read_text(encoding="utf-8")

    assert "fully written in natural english" in content.lower()
