from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.classes.ai import llm_ai
from src.classes.backstory import generate_backstory
from src.classes.long_term_objective import generate_long_term_objective
from src.classes.nickname import generate_nickname
from src.classes.story_teller import StoryTeller


@pytest.mark.asyncio
async def test_generate_backstory_passes_world_lore_separately(dummy_avatar):
    dummy_avatar.world.set_world_lore("The order of heaven and earth was rewritten by an ancient war.")

    with patch("src.classes.backstory.call_llm_with_task_name", new=AsyncMock(return_value={"backstory": "Born into a humble family."})) as mock_llm:
        await generate_backstory(dummy_avatar)

    infos = mock_llm.await_args.args[2]
    assert infos["world_lore"] == "The order of heaven and earth was rewritten by an ancient war."
    assert "The order of heaven and earth was rewritten by an ancient war." not in infos["world_info"]


@pytest.mark.asyncio
async def test_generate_nickname_passes_world_lore_separately(dummy_avatar):
    dummy_avatar.world.set_world_lore("The righteous and demonic paths have long stood in opposition.")
    dummy_avatar.world.event_manager.get_major_events_by_avatar = MagicMock(return_value=[])
    dummy_avatar.world.event_manager.get_minor_events_by_avatar = MagicMock(return_value=[])

    with patch("src.classes.nickname.call_llm_with_task_name", new=AsyncMock(return_value={"nickname": "Cold Edge", "thinking": "", "reason": "A cold sword and a quiet heart"})) as mock_llm:
        await generate_nickname(dummy_avatar)

    infos = mock_llm.await_args.args[2]
    assert infos["world_lore"] == "The righteous and demonic paths have long stood in opposition."
    assert "The righteous and demonic paths have long stood in opposition." not in str(infos["world_info"])


@pytest.mark.asyncio
async def test_generate_long_term_objective_passes_world_lore_separately(dummy_avatar):
    dummy_avatar.world.set_world_lore("Dynasties and sects rule the world together.")

    with patch(
        "src.classes.long_term_objective.call_llm_with_task_name",
        new=AsyncMock(return_value={"long_term_objective": "Guard the Dao heart"}),
    ) as mock_llm:
        await generate_long_term_objective(dummy_avatar)

    infos = mock_llm.await_args.args[2]
    assert infos["world_lore"] == "Dynasties and sects rule the world together."
    assert "Dynasties and sects rule the world together." not in str(infos["world_info"])


@pytest.mark.asyncio
async def test_story_teller_passes_world_lore_separately(dummy_avatar):
    dummy_avatar.world.set_world_lore("Heaven and earth's spiritual currents are in turmoil, and the old order is loosening.")

    with patch("src.classes.story_teller.call_llm_with_task_name", new=AsyncMock(return_value={"story": "A short story"})) as mock_llm:
        await StoryTeller.tell_story("Two people meet", "They part ways", dummy_avatar)

    infos = mock_llm.await_args.args[2]
    assert infos["world_lore"] == "Heaven and earth's spiritual currents are in turmoil, and the old order is loosening."
    assert "Heaven and earth's spiritual currents are in turmoil, and the old order is loosening." not in str(infos["world_info"])


@pytest.mark.asyncio
async def test_llm_ai_passes_world_lore_separately(dummy_avatar):
    dummy_avatar.world.set_world_lore("Secret realms open often and the sects vie for supremacy.")
    dummy_avatar.get_expanded_info = MagicMock(return_value={"name": dummy_avatar.name})
    dummy_avatar.world.get_observable_avatars = MagicMock(return_value=[])

    payload = {
        dummy_avatar.name: {
            "action_name_params_pairs": [["MoveToDirection", {"direction": "north"}]],
            "avatar_thinking": "Survey the situation first.",
            "current_emotion": "emotion_calm",
            "short_term_objective": "Scout the way",
        }
    }
    with patch("src.classes.ai.call_llm_with_task_name", new=AsyncMock(return_value=payload)) as mock_llm, patch(
        "src.classes.ai.get_action_infos_str",
        return_value="MoveToDirection",
    ), patch(
        "src.classes.core.avatar.info_presenter.get_avatar_ai_context",
        return_value={},
    ):
        await llm_ai._decide(dummy_avatar.world, [dummy_avatar])

    infos = mock_llm.await_args.args[2]
    assert infos["world_lore"] == "Secret realms open often and the sects vie for supremacy."
    assert "Secret realms open often and the sects vie for supremacy." not in str(infos["world_info"])
