
import pytest
from src.classes.effect.desc import format_effects_to_text
from src.classes.effect.process import _evaluate_conditional_effect
from src.classes.language import language_manager
from src.classes.persona import personas_by_id
from src.classes.weapon_type import WeaponType
from src.i18n import reload_translations
from src.i18n.locale_registry import get_locale_codes, get_source_locale

class TestEffectDescI18n:
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        # Remember the original language
        original_lang = str(language_manager)
        yield
        # Restore
        language_manager.set_language(original_lang)
        reload_translations()

    def test_format_effects_with_desc_override(self):
        """A _desc field overrides the whole effect description."""
        language_manager.set_language(get_source_locale())
        reload_translations()

        # Mimic the God-Slaying Spear config
        effects = {
            "extra_battle_strength_points": "3 + avatar.weapon_proficiency * 0.02",
            "_desc": "effect_god_slaying_spear_desc"
        }

        text = format_effects_to_text(effects)
        # Shows the translated text directly instead of "Battle Strength +3 + ..."
        assert "Increases Battle Strength based on Spear Proficiency" in text
        assert "avatar.weapon_proficiency" not in text

    def test_format_effects_with_when_desc_override(self):
        """A when_desc field overrides the condition description."""
        language_manager.set_language(get_source_locale())
        reload_translations()

        # Mimic the Ten Thousand Beasts Flute config
        effects = {
            "when": "avatar.spirit_animal is not None",
            "when_desc": "condition_has_spirit_animal",
            "extra_battle_strength_points": 2
        }

        text = format_effects_to_text(effects)
        # Expected format: [When possessing a Spirit Animal] Battle Strength +2
        assert "[When possessing a Spirit Animal]" in text
        assert "+2" in text
        assert "avatar.spirit_animal" not in text

    def test_mixed_effects_list(self):
        """An effect list mixing entries with and without overrides."""
        language_manager.set_language(get_source_locale())
        reload_translations()

        # Mimic the Heavenly Balance config (list form)
        effects = [
            {
                "when": "avatar.cultivation_progress.realm.value >= 6",
                "when_desc": "condition_realm_high",
                "extra_respire_exp": -25
            },
            {
                "when": "avatar.cultivation_progress.realm.value < 6",
                "when_desc": "condition_realm_low",
                "extra_respire_exp": 10
            }
        ]

        text = format_effects_to_text(effects)

        assert "[At Divinity Transformation stage or higher]" in text
        assert "-25" in text
        assert "[Below Divinity Transformation stage]" in text
        assert "+10" in text

    def test_fallback_behavior(self):
        """Without override fields the default formatting still works."""
        language_manager.set_language(get_source_locale())
        reload_translations()

        # Plain effect, no override
        effects = {
            "extra_max_hp": 100,
            "when": "avatar.level > 10"
        }

        text = format_effects_to_text(effects)
        # Falls back to the default regex-based condition translation;
        # only check the key value and the default bracketed condition
        assert "100" in text
        assert "level" in text
        assert "[" in text and "]" in text

    def test_formation_effect_values_are_player_readable(self):
        language_manager.set_language(get_source_locale())
        reload_translations()

        text = format_effects_to_text({
            "extra_formation_power": 0.08,
            "extra_formation_duration_months": 2,
            "formation_cost_reduction": 0.05,
        })

        assert "Formation Power +8.0%" in text
        assert "Formation Duration +2" in text
        assert "Formation Cost -5.0%" in text

    def test_weapon_persona_conditions_apply_and_are_localized_in_all_locales(self):
        from types import SimpleNamespace

        avatar = SimpleNamespace(
            weapon=SimpleNamespace(weapon_type=WeaponType.SPEAR),
        )
        weapon_personas = [
            persona
            for persona in personas_by_id.values()
            if "avatar.weapon.weapon_type" in str(persona.effects)
        ]
        assert weapon_personas
        assert "avatar.weapon.type" not in str([persona.effects for persona in weapon_personas])

        for persona in weapon_personas:
            condition = persona.effects[0]["when"]
            weapon_key = condition.split("WeaponType.", 1)[1].split()[0]
            matching_avatar = SimpleNamespace(
                weapon=SimpleNamespace(weapon_type=WeaponType[weapon_key]),
            )
            assert _evaluate_conditional_effect(persona.effects, matching_avatar)

        spear_fanatic = personas_by_id[50]
        active = _evaluate_conditional_effect(spear_fanatic.effects, avatar)
        assert active["extra_weapon_proficiency_gain"] == 1.0
        assert active["extra_battle_strength_points"] == 3

        for locale in get_locale_codes():
            language_manager.set_language(locale)
            reload_translations()
            text = format_effects_to_text(spear_fanatic.effects)
            assert "avatar.weapon" not in text
            assert "WeaponType." not in text
            assert "SPEAR" not in text

    def test_official_rank_condition_labels_are_localized_in_all_locales(self):
        from src.classes.official_rank import OFFICIAL_RANKS
        from src.i18n import t

        condition_effects = [
            effect
            for rank in OFFICIAL_RANKS.values()
            for effect in rank.effects
            if isinstance(effect, dict) and effect.get("when_desc")
        ]
        assert condition_effects

        for locale in get_locale_codes():
            language_manager.set_language(locale)
            reload_translations()
            assert t("condition_confucian_orthodoxy") != "condition_confucian_orthodoxy"
            for effect in condition_effects:
                assert "avatar.orthodoxy" not in format_effects_to_text(effect)
