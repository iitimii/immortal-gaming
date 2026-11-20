import os
import pytest
from pathlib import Path
from src.classes.language import language_manager
from src.utils.config import CONFIG, update_paths_for_language
from src.utils.df import load_game_configs, reload_game_configs, game_configs
from src.i18n.locale_registry import (
    get_default_locale,
    get_fallback_locale,
    get_locale_codes,
    get_project_root,
)

class TestLanguage:
    def setup_method(self):
        # Reset language to default before each test
        language_manager.set_language(get_default_locale())

    def test_language_manager_defaults(self):
        """Default state of the language manager."""
        default_locale = get_default_locale()
        assert language_manager.current == default_locale
        assert str(language_manager) == default_locale

    def test_language_manager_switch(self):
        """Switching language."""
        target_locale = get_fallback_locale()
        language_manager.set_language(target_locale)
        assert language_manager.current == target_locale
        assert str(language_manager) == target_locale
        
        # An invalid language falls back to the default
        language_manager.set_language("invalid-lang")
        assert language_manager.current == get_default_locale()

    def test_config_path_update(self):
        """Path update logic."""
        target_locale = get_fallback_locale()
        language_manager.set_language(target_locale)
        update_paths_for_language(target_locale)
        
        # game_configs points at the single source static/game_configs
        expected_game_configs = get_project_root() / "static" / "game_configs"
        # Note: Path comparison may need resolve() across platforms
        assert CONFIG.paths.game_configs.resolve() == expected_game_configs.resolve()
        assert CONFIG.paths.shared_game_configs.resolve() == expected_game_configs.resolve()

        default_locale = get_default_locale()
        language_manager.set_language(default_locale)
        update_paths_for_language(default_locale)
        # Still points at the single source
        assert CONFIG.paths.game_configs.resolve() == expected_game_configs.resolve()

    def test_game_config_loading_and_override(self, tmp_path):
        """I18n translation logic during config loading."""
        # 1. Prepare the directory layout
        # There is no shared/localized split any more, only one game_configs dir
        game_configs_dir = tmp_path / "game_configs"
        game_configs_dir.mkdir()
        
        # 2. Create the test file test.csv
        # with name_id/desc_id columns
        csv_content = (
            "id,name_id,name,desc_id,desc\n"
            "Name ID,Name,Desc ID,Desc\n"
            "test_item,TEST_ITEM_NAME,TestItemSource,TEST_ITEM_DESC,TestDescSource"
        )
        (game_configs_dir / "test.csv").write_text(csv_content, encoding="utf-8")
        
        # 3. Temporarily point CONFIG.paths at the test dir
        original_game_configs = CONFIG.paths.game_configs
        original_shared = getattr(CONFIG.paths, "shared_game_configs", None)
        original_localized = getattr(CONFIG.paths, "localized_game_configs", None)
        
        try:
            CONFIG.paths.game_configs = game_configs_dir
            CONFIG.paths.shared_game_configs = game_configs_dir
            CONFIG.paths.localized_game_configs = game_configs_dir
            
            # Mock src.utils.df.t to simulate translation
            # We need to patch 'src.utils.df.t'
            from unittest.mock import patch
            
            # Case 1: a translation exists
            with patch('src.utils.df.t') as mock_t:
                mock_t.side_effect = lambda x: "TestItemTranslated" if x == "TEST_ITEM_NAME" else ("TestDescTranslated" if x == "TEST_ITEM_DESC" else x)
                
                loaded = load_game_configs()
                
                assert "test" in loaded
                item = loaded["test"][0]
                assert item["name"] == "TestItemTranslated"
                assert item["desc"] == "TestDescTranslated"
                
            # Case 2: no translation (fallback)
            with patch('src.utils.df.t') as mock_t:
                # If t returns the key itself (or empty), df.py keeps the original CSV value
                mock_t.side_effect = lambda x: x 
                
                loaded = load_game_configs()
                
                item = loaded["test"][0]
                # Should fallback to CSV values
                assert item["name"] == "TestItemSource"
                assert item["desc"] == "TestDescSource"
            
        finally:
            # Restore config
            CONFIG.paths.game_configs = original_game_configs
            if original_shared:
                CONFIG.paths.shared_game_configs = original_shared
            if original_localized:
                CONFIG.paths.localized_game_configs = original_localized

    def test_reload_game_configs_integration(self):
        """Integration: reload_game_configs really updates the global configs."""
        # Relies on the real static dir; only a simple check
        # make sure it does not raise
        try:
            reload_game_configs()
            # At least the core config tables should be loaded.
            assert "sect" in game_configs
        except Exception as e:
            pytest.fail(f"reload_game_configs failed: {e}")

    def test_i18n_objects_output(self):
        """Localized object output."""
        from src.classes.language import language_manager
        from src.i18n import t, reload_translations
        from src.classes.items.magic_stone import MagicStone
        from src.classes.environment.region import NormalRegion
        from src.classes.persona import Persona
        from src.classes.rarity import Rarity, RarityLevel
        from src.classes.core.avatar.info_presenter import get_avatar_info
        from src.classes.emotions import EmotionType
        from src.classes.root import Root
        from src.classes.appearance import get_appearance_by_level
        from unittest.mock import MagicMock

        language_manager.set_language(get_default_locale())
        reload_translations()

        try:
            # 1. MagicStone
            ms = MagicStone(100)
            assert str(ms) == "100 Spirit Stones"

            # 2. Region
            region = NormalRegion(id=1, name="TestRegion", desc="TestDesc")
            assert "Normal Region" in str(region)
            assert "Resource Distribution" in str(region)
            
            # Distance check
            assert "Distance" in region.get_info(current_loc=(0,0), step_len=1)

            # 3. Persona
            p = Persona(
                id=1, key="TEST", name="TestPersona", desc="TestDesc", 
                exclusion_keys=[], rarity=Rarity(RarityLevel.N, 1.0, (255,255,255), "#FFFFFF", "Common"), 
                condition="", effects={}, effect_desc="TestEffect"
            )
            assert "Effect: TestEffect" in p.get_detailed_info()

            # 4. Avatar Emotion
            # Mock Avatar
            avatar = MagicMock()
            avatar.emotion = EmotionType.CALM
            avatar.name = "TestAvatar"
            avatar.gender = "Male"
            avatar.age = MagicMock()
            avatar.age.__str__.return_value = "20"
            avatar.hp = MagicMock()
            avatar.hp.__str__.return_value = "100/100"
            avatar.magic_stone = MagicStone(0)
            avatar.relations = {}
            avatar.sect = None
            avatar.alignment = None
            avatar.root = MagicMock()
            avatar.root.get_info.return_value = "Fire"
            avatar.technique = None
            avatar.cultivation_progress = MagicMock()
            avatar.cultivation_progress.get_info.return_value = "Qi Refinement"
            avatar.personas = []
            avatar.materials = {}
            avatar.appearance = MagicMock()
            avatar.appearance.get_info.return_value = "Handsome"
            avatar.weapon = None
            avatar.auxiliary = None
            avatar.long_term_objective = None
            avatar.short_term_objective = None
            avatar.nickname = None
            avatar.spirit_animal = None
            avatar.orthodoxy = None
            avatar.emotion = EmotionType.CALM
            avatar.tile = MagicMock()
            avatar.tile.region = None
            avatar.world = MagicMock()
            avatar.world.ranking_manager.get_avatar_rank.return_value = None

            info = get_avatar_info(avatar)
            assert info["Emotion"] == "Calm"
            
            # 5. Root (New check)
            # The root info lists its element names, e.g. "Thunder"
            assert "Thunder" in Root.THUNDER.get_info()
            assert "Water" in Root.THUNDER.get_info()
            assert "Earth" in Root.THUNDER.get_info()
            
            # 6. Appearance (New check)
            app = get_appearance_by_level(7) # 7 is Handsome
            assert "Handsome" in app.get_info()

            # 7. Cultivation Progress (New check)
            from src.systems.cultivation import CultivationProgress
            cp = CultivationProgress(1)
            # Expect space-separated translated values
            assert cp.get_info() == "Qi Refinement Early Stage"

        finally:
            # Restore to default just in case
            language_manager.set_language(get_default_locale())
            reload_translations()
