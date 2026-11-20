from pathlib import Path

from src.i18n.locale_registry import get_locale_codes


def _template(locale: str, name: str) -> str:
    return Path("static/locales", locale, "templates", name).read_text(encoding="utf-8")


def test_action_decision_templates_prioritize_race_over_persona():
    markers = ("racial instinct", "persona")
    for locale in get_locale_codes():
        text = _template(locale, "ai.txt")
        for marker in markers:
            assert marker in text


def test_goal_conversation_and_story_templates_require_yao_race_expression():
    markers = ("yao", "racial")
    template_names = (
        "long_term_objective.txt",
        "conversation.txt",
        "story_single.txt",
        "story_dual.txt",
        "story_gathering.txt",
    )

    for locale in get_locale_codes():
        for template_name in template_names:
            text = _template(locale, template_name)
            for marker in markers:
                assert marker.lower() in text.lower()
