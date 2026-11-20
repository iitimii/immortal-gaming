from pathlib import Path

from src.utils.llm.prompt import build_prompt, load_template
from src.i18n.locale_registry import get_project_root, get_source_locale


def test_sect_random_event_template_can_be_formatted() -> None:
    source_locale = get_source_locale()
    template_path = get_project_root() / "static" / "locales" / source_locale / "templates" / "sect_random_event.txt"
    template = load_template(template_path)

    infos = {
        "language": source_locale,
        "event_type": "relation_down",
        "sect_a_name": "Sect A",
        "sect_b_name": "Sect B",
        "sect_a_detail": "A sect detail",
        "sect_b_detail": "B sect detail",
        "value": 12,
        "duration_months": 60,
        "target_chars": 20,
    }

    prompt = build_prompt(template, infos)

    assert "reason_fragment" in prompt
    assert "Sect A" in prompt
    assert "Sect B" in prompt


def test_sect_decider_template_can_be_formatted() -> None:
    template_path = get_project_root() / "static" / "locales" / get_source_locale() / "templates" / "sect_decider.txt"
    template = load_template(template_path)

    infos = {
        "sect_name": "Sect A",
        "world_info": "{}",
        "world_lore": "",
        "decision_context_info": "{}",
        "recruit_cost": 500,
        "support_amount": 300,
    }

    prompt = build_prompt(template, infos)

    assert "recruit_avatar_ids" in prompt
    assert "Sect A" in prompt


def test_custom_goldfinger_template_can_be_formatted() -> None:
    source_locale = get_source_locale()
    template_path = get_project_root() / "static" / "locales" / source_locale / "templates" / "custom_goldfinger.txt"
    template = load_template(template_path)

    infos = {
        "allowed_effects": "- extra_luck: luck, value type int, example 2",
        "user_prompt": "I want a check-in style goldfinger with slightly stronger stats",
    }

    prompt = build_prompt(template, infos)

    assert "goldfinger" in prompt.lower()
    assert "\"thinking\"" in prompt
    assert "extra_luck" in prompt
    assert "I want a check-in style goldfinger with slightly stronger stats" in prompt


def test_roleplay_conversation_turn_template_can_be_formatted() -> None:
    source_locale = get_source_locale()
    template_path = get_project_root() / "static" / "locales" / source_locale / "templates" / "roleplay_conversation_turn.txt"
    template = load_template(template_path)

    infos = {
        "avatar_name": "Wenren Wu",
        "target_avatar_name": "Ye Ming",
        "world_info": "The immortal path flourishes and sects abound.",
        "avatar_infos": "{\"Wenren Wu\": \"rogue cultivator\", \"Ye Ming\": \"sect disciple\"}",
        "conversation_history": "Wenren Wu: Greetings, fellow Daoist.\nYe Ming: What brings you here?",
    }

    prompt = build_prompt(template, infos)

    assert "Wenren Wu" in prompt
    assert "Ye Ming" in prompt
    assert "reply_content" in prompt
    assert "speaker_thinking" in prompt


def test_relation_delta_template_can_be_formatted() -> None:
    source_locale = get_source_locale()
    template_path = get_project_root() / "static" / "locales" / source_locale / "templates" / "relation_delta.txt"
    template = load_template(template_path)

    infos = {
        "min_delta": -5,
        "max_delta": 5,
        "avatar_a_name": "Wenren Wu",
        "avatar_a_personas": "cautious, competitive",
        "avatar_a_to_b_friendliness": "ordinary",
        "avatar_a_to_b_numeric_relation": 3,
        "avatar_b_name": "Ye Ming",
        "avatar_b_personas": "calm, taciturn",
        "avatar_b_to_a_friendliness": "neutral",
        "avatar_b_to_a_numeric_relation": 1,
        "identity_relations": "fellow travelers",
        "event_text": "The two met by chance and exchanged a few pleasantries; the mood was fairly calm.",
    }

    prompt = build_prompt(template, infos)

    assert "delta_a_to_b" in prompt
    assert "delta_b_to_a" in prompt
    assert "Wenren Wu" in prompt
    assert "Ye Ming" in prompt


def test_fate_revelation_template_can_be_formatted() -> None:
    source_locale = get_source_locale()
    template_path = get_project_root() / "static" / "locales" / source_locale / "templates" / "fate_revelation.txt"
    template = load_template(template_path)

    infos = {
        "avatar_info": "{\"name\": \"Wenren Wu\", \"realm\": \"Qi Refinement\"}",
        "location": "Qingxi Ferry",
        "current_action": "Traveling",
        "world_info": "{\"Phenomenon\": \"Tide Sound Enters Dreams\"}",
        "current_phenomenon": "Tide Sound Enters Dreams: the sound of the tide echoes among the mountains.",
    }

    prompt = build_prompt(template, infos)

    assert "Fate" in prompt
    assert "oracle_text" in prompt
    assert "Dusk snow pours into the eastern sea" in prompt
    assert "Qingxi Ferry" in prompt
