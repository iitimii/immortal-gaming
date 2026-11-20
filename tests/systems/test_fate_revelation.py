from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.systems.fate_revelation import (
    FATE_REVELATION_EVENT_TYPE,
    is_valid_oracle_text,
    should_trigger_fate_revelation,
    try_trigger_fate_revelation,
)


@pytest.fixture
def set_fate_probability():
    """
    Set CONFIG.world.fate_revelation_probability for one test and restore it.

    monkeypatch.setattr on an OmegaConf DictConfig is not reliably undone
    (pytest 9 deletes the key on undo), so restore the value manually.
    """
    from src.systems import fate_revelation

    world_cfg = fate_revelation.CONFIG.world
    original = world_cfg.fate_revelation_probability

    def _set(value: float) -> None:
        world_cfg.fate_revelation_probability = value

    yield _set
    world_cfg.fate_revelation_probability = original


def test_oracle_text_validation_allows_poetic_forms():
    assert is_valid_oracle_text("Round with the tide, silent with the letter")
    assert is_valid_oracle_text("Dusk snow of a thousand peaks pours into the eastern sea; at first light the tide climbs again")
    assert is_valid_oracle_text("Falling blossoms are not spring's end; a tolling bell is no homecoming")


def test_oracle_text_validation_rejects_explanations():
    assert not is_valid_oracle_text("This foretells that he will ascend")
    assert not is_valid_oracle_text("Fate: a noble benefactor helps")
    assert not is_valid_oracle_text("The system grants an attribute reward")


def test_should_not_trigger_when_avatar_already_has_fate(dummy_avatar, monkeypatch):
    dummy_avatar.fate_revelation = {
        "trigger_text": "Old rain falls on the stone steps.",
        "oracle_text": "Old rain lights the lamp; the tide returns without a shore",
    }
    monkeypatch.setattr("src.systems.fate_revelation.random.random", lambda: 0.0)

    assert should_trigger_fate_revelation(dummy_avatar) is False


def test_should_not_trigger_when_probability_zero(dummy_avatar, monkeypatch, set_fate_probability):
    set_fate_probability(0.0)
    monkeypatch.setattr("src.systems.fate_revelation.random.random", lambda: 0.0)

    assert should_trigger_fate_revelation(dummy_avatar) is False


@pytest.mark.asyncio
async def test_try_trigger_fate_revelation_writes_avatar_and_event(dummy_avatar, monkeypatch, set_fate_probability):
    dummy_avatar.fate_revelation = None
    set_fate_probability(1.0)
    monkeypatch.setattr("src.systems.fate_revelation.random.random", lambda: 0.0)

    llm_result = {
        "trigger_text": "At the Azure Creek ferry a backflow suddenly curls into a circle, a few withered leaves clinging to the surface without drifting apart.",
        "oracle_text": "Dusk snow of a thousand peaks pours into the eastern sea; at first light the tide climbs again",
        "event_text": "At the Azure Creek ferry a backflow suddenly curls into a circle, a few withered leaves clinging to the surface without drifting apart. TestDummy gazed intently, and a line of fate rose in his heart: \"Dusk snow of a thousand peaks pours into the eastern sea; at first light the tide climbs again\"",
    }
    with patch(
        "src.systems.fate_revelation.call_llm_with_task_name",
        new_callable=AsyncMock,
        return_value=llm_result,
    ) as mock_call:
        events = await try_trigger_fate_revelation(dummy_avatar, dummy_avatar.world)

    assert len(events) == 1
    event = events[0]
    assert event.is_major is True
    assert event.is_story is False
    assert event.event_type == FATE_REVELATION_EVENT_TYPE
    assert event.related_avatars == [dummy_avatar.id]
    assert "Dusk snow of a thousand peaks" in event.content
    assert dummy_avatar.fate_revelation is not None
    assert dummy_avatar.fate_revelation["oracle_text"] == llm_result["oracle_text"]
    assert dummy_avatar.fate_revelation["trigger_text"] == llm_result["trigger_text"]
    assert dummy_avatar.fate_revelation["revealed_month"] == int(dummy_avatar.world.month_stamp)
    assert mock_call.call_args.kwargs["task_name"] == "fate_revelation"


@pytest.mark.asyncio
async def test_try_trigger_fate_revelation_rejects_bad_oracle(dummy_avatar, monkeypatch, set_fate_probability):
    dummy_avatar.fate_revelation = None
    set_fate_probability(1.0)
    monkeypatch.setattr("src.systems.fate_revelation.random.random", lambda: 0.0)

    llm_result = {
        "trigger_text": "Night rain beats on a ruined stele; a faint glimmer flickers in a crack and dies.",
        "oracle_text": "This foretells that he will ascend",
        "event_text": "bad output",
    }
    with patch(
        "src.systems.fate_revelation.call_llm_with_task_name",
        new_callable=AsyncMock,
        return_value=llm_result,
    ):
        events = await try_trigger_fate_revelation(dummy_avatar, dummy_avatar.world)

    assert events == []
    assert dummy_avatar.fate_revelation is None
