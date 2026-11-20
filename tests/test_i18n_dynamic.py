import unittest
from unittest.mock import MagicMock
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.systems.time import get_date_str
from src.classes.environment.sect_region import SectRegion
from src.classes.core.world import World
from src.classes.language import language_manager
from src.classes.celestial_phenomenon import CelestialPhenomenon
from src.i18n.locale_registry import get_default_locale


class TestI18nDynamic(unittest.TestCase):
    """Runtime-formatted strings resolve through the active (en-US) locale."""

    def setUp(self):
        # Save current language
        self.original_lang = str(language_manager)
        language_manager.set_language(get_default_locale())

    def tearDown(self):
        # Restore language
        language_manager.set_language(self.original_lang)

    def test_date_format_uses_locale_template(self):
        """Date strings are rendered with the en-US template."""
        # 13 = Year 1, Month 2 (formula: year*12 + month - 1 => 1*12 + 2 - 1 = 13)
        self.assertEqual(get_date_str(13), "Year 1 Month 2")

    def test_sect_region_desc_uses_locale_template(self):
        """Sect headquarters descriptions are rendered with the en-US template."""
        # Provide dummy id, name, desc for SectRegion
        region = SectRegion(id=1, name="Dummy", desc="DummyDesc", sect_name="TestSect", sect_id=1)

        desc = region._get_desc()
        self.assertIn("(TestSect HQ)", desc)

    def test_world_info_key_uses_locale_template(self):
        """The world info prompt key and value use the en-US templates."""
        mock_map = MagicMock()
        mock_map.get_info.return_value = {}
        mock_month = MagicMock()

        world = World(map=mock_map, month_stamp=mock_month)

        world.current_phenomenon = CelestialPhenomenon(
            id=1,
            name="TestPhenomenon",
            desc="TestDesc",
            rarity=None,
            effects={},
            effect_desc="",
            duration_years=5
        )

        info = world.get_info()

        self.assertIn("Current World Phenomenon", info)
        self.assertEqual(info["Current World Phenomenon"], "TestPhenomenon: TestDesc")


if __name__ == '__main__':
    unittest.main()
