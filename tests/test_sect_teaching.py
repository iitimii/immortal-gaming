from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.classes.age import Age
from src.classes.alignment import Alignment
from src.classes.core.avatar.core import Avatar
from src.classes.core.sect import Sect, SectHeadQuarter
from src.classes.gender import Gender
from src.classes.gathering.sect_teaching import SectTeachingConference
from src.classes.sect_ranks import SectRank
from src.systems.cultivation import CultivationProgress
from src.systems.time import MonthStamp


def _create_member(world, sect, avatar_id: str, name: str, level: int, rank: SectRank) -> Avatar:
    avatar = Avatar(
        world=world,
        name=name,
        id=avatar_id,
        birth_month_stamp=MonthStamp(1),
        age=Age(18, realm=0),
        gender=Gender.MALE,
    )
    avatar.cultivation_progress = CultivationProgress(level)
    avatar.join_sect(sect, rank)
    avatar.is_dead = False
    world.avatar_manager.avatars[avatar.id] = avatar
    return avatar


def test_build_sect_teaching_context_text_summarizes_decision_context(base_world):
    world = base_world
    sect = Sect(
        id=1,
        name="High Heaven Sword Sect",
        desc="Upholds righteousness and a clear heart",
        member_act_style="steady",
        alignment=Alignment.NEUTRAL,
        headquarter=SectHeadQuarter(name="Mountain Gate", desc="Amid a sea of clouds", image=Path("")),
        technique_names=[],
    )
    teacher = _create_member(world, sect, "teacher_1", "Lecturer A", 61, SectRank.Elder)
    world.event_manager._storage = MagicMock()

    mock_ctx = MagicMock()
    mock_ctx.active_wars = [{"other_sect_name": "Crimson Flame Sect", "status": "war"}]
    mock_ctx.economy = {"treasury_pressure": "tight"}
    mock_ctx.self_assessment = {"war_readiness": "stretched", "alive_member_count": 7}
    mock_ctx.territory = {"border_pressure_ratio": 0.35, "tile_count": 12}
    mock_ctx.power = {"total_battle_strength": 88.0}

    conference = SectTeachingConference()
    with patch("src.classes.core.sect.get_sect_decision_context", return_value=mock_ctx):
        text = conference._build_sect_teaching_context_text(sect, teacher)

    assert "High Heaven Sword Sect" in text
    assert "at war with Crimson Flame Sect" in text
    assert "treasury tight" in text
    assert "war readiness stretched" in text
    assert "Border pressure: 35%" in text
    assert "7 living members" in text
    assert "battle strength about 88" in text


@pytest.mark.asyncio
async def test_generate_story_uses_refined_sect_context_in_details(base_world):
    world = base_world
    sect = Sect(
        id=1,
        name="Great Void Gate",
        desc="Tranquil and actionless",
        member_act_style="serene",
        alignment=Alignment.NEUTRAL,
        headquarter=SectHeadQuarter(name="Cloud Terrace", desc="A high terrace for stargazing", image=Path("")),
        technique_names=[],
    )
    teacher = _create_member(world, sect, "teacher_1", "Master A", 61, SectRank.Elder)
    student = _create_member(world, sect, "student_1", "Disciple B", 1, SectRank.OuterDisciple)

    conference = SectTeachingConference()
    with patch.object(
        conference,
        "_build_sect_teaching_context_text",
        return_value="[Sect background] Currently at war with the Mystic Frost Sect; the treasury is stable.",
    ), patch(
        "src.classes.gathering.sect_teaching.StoryEventService.maybe_create_gathering_story",
        new=AsyncMock(return_value=None),
    ) as mock_story:
        await conference._generate_story(
            sect=sect,
            teacher=teacher,
            students=[student],
            exp_gains=[(student, 42)],
            epiphany_list=[],
            month_stamp=world.month_stamp,
        )

    details_text = mock_story.await_args.kwargs["details_text"]
    assert "[Sect background] Currently at war with the Mystic Frost Sect; the treasury is stable." in details_text
    assert "Master A:" in details_text
    assert "- Disciple B:" in details_text
