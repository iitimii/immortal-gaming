"""
Test that CSV data loads correctly.
Verify that the column names used in code match the actual CSV columns.
Expected strings are derived dynamically per registered locale rather than hard-coded.
"""
import pytest
import csv
from pathlib import Path
from src.classes.core.sect import sects_by_id, sects_by_name, Sect, reload as reload_sects
from src.classes.technique import techniques_by_id, techniques_by_name, Technique, reload as reload_techniques
from src.classes.items.elixir import elixirs_by_id
from src.utils.config import CONFIG
from src.i18n import t, reload_translations
from src.classes.language import language_manager
from src.i18n.locale_registry import get_default_locale, get_locale_codes

# --- Helpers ---

def read_raw_csv_as_dict(file_path):
    """Read a raw CSV file, skipping the description row."""
    if not file_path.exists():
        return []
    
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        lines = list(csv.reader(f))
        
        if len(lines) < 1:
            return []
            
        headers = lines[0]
        data = []
        
        # Start from index 2 if there's a description row
        start_index = 2 if len(lines) > 1 else 1
        
        for row_values in lines[start_index:]:
            if not row_values: continue
            row_dict = {}
            for i, h in enumerate(headers):
                 if i < len(row_values):
                     row_dict[h] = row_values[i]
                 else:
                     row_dict[h] = None
            data.append(row_dict)
            
        return data

@pytest.fixture(params=get_locale_codes())
def game_lang(request):
    """
    Parametrized fixture: switch language and reload game data.
    Restores the default locale after the test.
    """
    lang = request.param
    
    # 1. Switch Language
    language_manager.set_language(lang)
    reload_translations()
    
    # 2. Force Reload Game Data
    from src.utils.config import update_paths_for_language
    update_paths_for_language(lang)
    
    from src.utils.df import reload_game_configs
    reload_game_configs()
    
    reload_techniques() 
    reload_sects()
    
    yield lang
    
    # Teardown: restore the default locale for other tests
    default_locale = get_default_locale()
    language_manager.set_language(default_locale)
    reload_translations()
    update_paths_for_language(default_locale)
    reload_game_configs()
    reload_techniques()
    reload_sects()


class TestSectLoading:
    """Test sect data loading (dynamic per-locale verification)."""

    def test_sect_headquarter_name_loaded(self, game_lang):
        """Sect headquarters names load correctly."""
        # Read RAW Sect CSV
        sect_csv_path = CONFIG.paths.shared_game_configs / "sect.csv"
        raw_sects = read_raw_csv_as_dict(sect_csv_path)
        
        # Read RAW Sect Region CSV (Source of HQ names)
        region_csv_path = CONFIG.paths.shared_game_configs / "sect_region.csv"
        raw_regions = read_raw_csv_as_dict(region_csv_path)
        sect_region_map = {int(r['sect_id']): r for r in raw_regions if r.get('sect_id')}
        
        # Verify a specific sect (ID=12, Everlasting Bright Palace)
        target_id = 12
        sect = sects_by_id.get(target_id)
        assert sect is not None
        
        # 1. Verify Sect Name
        sect_row = next((r for r in raw_sects if int(r['id']) == target_id), None)
        assert sect_row
        
        expected_sect_name = sect_row.get('name')
        if sect_row.get('name_id'):
            trans = t(sect_row['name_id'])
            if trans and trans != sect_row['name_id']:
                expected_sect_name = trans
        
        assert sect.name == expected_sect_name, f"Sect name mismatch in {game_lang}"
        
        # 2. Verify HQ Name
        region_row = sect_region_map.get(target_id)
        assert region_row
        
        expected_hq_name = region_row.get('name')
        if region_row.get('name_id'):
            trans = t(region_row['name_id'])
            if trans and trans != region_row['name_id']:
                expected_hq_name = trans
                
        assert sect.headquarter.name == expected_hq_name, f"HQ name mismatch in {game_lang}"

    def test_sect_headquarter_desc_loaded(self, game_lang):
        """Sect headquarters descriptions load correctly."""
        target_id = 12
        sect = sects_by_id.get(target_id)
        assert sect is not None
        
        # Read RAW Sect Region CSV
        region_csv_path = CONFIG.paths.shared_game_configs / "sect_region.csv"
        raw_regions = read_raw_csv_as_dict(region_csv_path)
        region_row = next((r for r in raw_regions if int(r.get('sect_id', -1)) == target_id), None)
        assert region_row
        
        expected_desc = region_row.get('desc')
        if region_row.get('desc_id'):
            trans = t(region_row['desc_id'])
            if trans and trans != region_row['desc_id']:
                expected_desc = trans
                
        # Normalize newlines/spaces for comparison if needed
        assert sect.headquarter.desc == expected_desc, f"HQ desc mismatch in {game_lang}"

    def test_all_sects_have_headquarters(self, game_lang):
        """Every sect has headquarters info."""
        for sect_id, sect in sects_by_id.items():
            assert sect.headquarter is not None
            assert sect.headquarter.name, f"Headquarters name of sect {sect.name} should not be empty"

    def test_sect_techniques_loaded(self, game_lang):
        """Sect technique lists load correctly."""
        sect = sects_by_id.get(1) # High Heaven Sword Sect
        assert sect is not None
        assert len(sect.technique_names) > 0

    def test_sect_without_techniques(self, game_lang):
        """A sect without configured techniques."""
        sect = sects_by_id.get(10) # Soul-Seizing Sound Sect
        assert sect is not None
        assert sect.technique_names == []

    def test_gu_and_formation_specialist_sects_have_conservative_bonus_only(self, game_lang):
        """Gu/formation specialist sects only grant conservative bonuses and do not unlock actions directly."""
        gu_sect = sects_by_id.get(5)
        formation_sect = sects_by_id.get(11)
        assert gu_sect is not None
        assert formation_sect is not None

        gu_actions = gu_sect.effects.get("legal_actions", [])
        assert "InflictGu" not in gu_actions
        assert "SetFormation" not in gu_actions
        assert gu_sect.effects["extra_gu_success_rate"] == 0.03
        assert gu_sect.effects["extra_gu_duration_months"] == 2
        assert "extra_gu_success_rate" not in formation_sect.effects

        formation_actions = formation_sect.effects.get("legal_actions", [])
        assert "InflictGu" not in formation_actions
        assert "SetFormation" not in formation_actions
        assert formation_sect.effects["extra_formation_power"] == 0.05
        assert formation_sect.effects["extra_formation_duration_months"] == 2
        assert formation_sect.effects["formation_cost_reduction"] == 0.05

        assert gu_sect.effect_desc
        assert formation_sect.effect_desc


class TestTechniqueLoading:
    """Test technique data loading."""

    def test_technique_sect_id_loaded(self, game_lang):
        """Technique sect_id loads correctly."""
        tech_id = 30 # Star Slashing Withered Glory Sword
        technique = techniques_by_id.get(tech_id)
        assert technique is not None
        
        # Verify Name using Dynamic Logic
        tech_csv_path = CONFIG.paths.shared_game_configs / "technique.csv"
        raw_techs = read_raw_csv_as_dict(tech_csv_path)
        row = next((r for r in raw_techs if int(r['id']) == tech_id), None)
        
        expected_name = row.get('name')
        if row.get('name_id'):
            trans = t(row['name_id'])
            if trans and trans != row['name_id']:
                expected_name = trans
                
        assert technique.name == expected_name, f"Technique name mismatch in {game_lang}"
        assert technique.sect_id == 1

    def test_technique_without_sect(self, game_lang):
        """A rogue-cultivator technique."""
        technique = techniques_by_id.get(1)
        assert technique is not None
        assert technique.sect_id is None

    def test_sect_techniques_match(self, game_lang):
        """Sect techniques and technique sect IDs match each other."""
        for sect_id, sect in sects_by_id.items():
            for tech_name in sect.technique_names:
                technique = techniques_by_name.get(tech_name)
                # Note: technique_names is a list of strings; mismatched names (translation issues) would miss here.
                # sect.technique_names is loaded directly from technique.csv, so as long as the reload
                # order is correct (techniques before sects) the names stay consistent.
                assert technique is not None, f"Technique '{tech_name}' should exist (Lang: {game_lang})"
                assert technique.sect_id == sect_id


class TestElixirLoading:
    """Elixir loading test (ID check, less dependent on lang but good to verify integrity)"""

    def test_elixir_loaded_with_item_id(self):
        # Elixirs currently have no dedicated reload/translation-key binding to verify,
        # so no parametrization is needed here
        assert len(elixirs_by_id) > 0
        for elixir_id, elixir in elixirs_by_id.items():
            assert elixir_id > 0
            assert elixir.id == elixir_id


class TestGameDataAPI:
    """Test the API (run in a fixed environment, without locale parametrization, to avoid affecting server state)."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from src.server.main import app
        return TestClient(app)

    def test_game_data_techniques_have_sect_id(self, client):
        response = client.get("/api/v1/query/meta/game-data")
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["techniques"]) > 0
        assert "sect_id" in data["techniques"][0]

    def test_game_data_sects_structure(self, client):
        response = client.get("/api/v1/query/meta/game-data")
        assert response.status_code == 200
        data = response.json()["data"]
        assert len(data["sects"]) > 0
        assert "id" in data["sects"][0]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
