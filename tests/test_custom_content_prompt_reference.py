from src.classes.language import language_manager
from src.i18n import reload_translations
from src.i18n.locale_registry import get_default_locale
from src.classes.effect import get_effect_prompt_meta_map
from src.i18n.template_resolver import resolve_locale_template_path
from src.server.services.custom_content_service import (
    _category_label,
    _format_reference_text,
    _resolve_template_path,
)
from src.utils.config import CONFIG


def test_effect_prompt_meta_covers_all_effects():
    meta_map = get_effect_prompt_meta_map()

    assert "extra_battle_strength_points" in meta_map
    assert "legal_actions" in meta_map


def _use_default_language():
    original_lang = str(language_manager)
    language_manager._current = get_default_locale()
    reload_translations()
    return original_lang


def _restore_language(original_lang):
    language_manager._current = original_lang
    reload_translations()


def test_format_reference_text_reads_structured_meta():
    original_lang = _use_default_language()
    try:
        result = _format_reference_text("extra_battle_strength_points")
        assert result == "small: 1 to 2; medium: 3 to 5; large: 8+"
    finally:
        _restore_language(original_lang)


def test_format_reference_text_includes_constraints_from_meta():
    original_lang = _use_default_language()
    try:
        result = _format_reference_text("shop_buy_price_reduction")
        assert result == "small: 0.1; medium: 0.5; final multiplier >= 1.0"
    finally:
        _restore_language(original_lang)


def test_category_label_uses_gettext_translations():
    original_lang = _use_default_language()
    try:
        assert _category_label("technique") == "technique"
        assert _category_label("auxiliary") == "auxiliary equipment"
    finally:
        _restore_language(original_lang)


def test_resolve_template_path_prefers_configured_dir_then_falls_back_to_locale(tmp_path):
    original_lang = _use_default_language()
    original_templates = CONFIG.paths.templates
    original_locales = CONFIG.paths.locales
    default_locale = get_default_locale()

    try:
        locales_dir = tmp_path / "locales"
        preferred_templates = tmp_path / "custom_templates"
        fallback_templates = locales_dir / default_locale / "templates"
        preferred_templates.mkdir(parents=True)
        fallback_templates.mkdir(parents=True)

        fallback_file = fallback_templates / "custom_content.txt"
        fallback_file.write_text("fallback", encoding="utf-8")

        # Manual assignment (restored in finally): monkeypatch on DictConfig is not undone reliably.
        CONFIG.paths.templates = preferred_templates
        CONFIG.paths.locales = locales_dir

        assert _resolve_template_path("custom_content.txt") == fallback_file

        preferred_file = preferred_templates / "custom_content.txt"
        preferred_file.write_text("preferred", encoding="utf-8")

        assert _resolve_template_path("custom_content.txt") == preferred_file
    finally:
        _restore_language(original_lang)
        CONFIG.paths.templates = original_templates
        CONFIG.paths.locales = original_locales


def test_shared_template_resolver_falls_back_to_default_locale(tmp_path):
    default_locale = get_default_locale()
    locales_dir = tmp_path / "locales"
    preferred_templates = tmp_path / "custom_templates"
    fallback_templates = locales_dir / default_locale / "templates"
    fallback_templates.mkdir(parents=True)

    fallback_file = fallback_templates / "sect_thinker.txt"
    fallback_file.write_text("fallback", encoding="utf-8")
    assert resolve_locale_template_path(
        "sect_thinker.txt",
        current_locale=default_locale,
        preferred_dir=preferred_templates,
        locales_dir=locales_dir,
    ) == fallback_file

    fallback_file.unlink()
    # Nothing exists anywhere: the preferred path is returned so callers report a clear error.
    assert resolve_locale_template_path(
        "sect_thinker.txt",
        current_locale=default_locale,
        preferred_dir=preferred_templates,
        locales_dir=locales_dir,
    ) == preferred_templates / "sect_thinker.txt"
