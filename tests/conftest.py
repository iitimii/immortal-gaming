import pytest
import random
import logging
import sys
import copy
from unittest.mock import MagicMock, AsyncMock, patch

from src.classes.environment.map import Map
from src.i18n.locale_registry import get_default_locale


@pytest.fixture(autouse=True)
def isolate_settings_data_root(monkeypatch, tmp_path):
    """
    Redirect app settings/secrets data root to a per-test temp dir.
    """
    from src.config import reset_data_paths_cache, reset_settings_service_cache

    data_root = tmp_path / "appdata"
    monkeypatch.setenv("CWS_DATA_DIR", str(data_root))
    reset_settings_service_cache()
    reset_data_paths_cache()

    yield data_root

    reset_settings_service_cache()
    reset_data_paths_cache()


@pytest.fixture(scope="session", autouse=True)
def configure_test_logging(tmp_path_factory):
    """
    Configure logging to prevent pollution of project root logs.
    1. Redirect src.run.log to temp directory.
    2. Configure root logger to output to stderr for pytest capture.
    """
    # 1. Setup root logger for pytest
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
    
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.WARNING)
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    # 2. Patch src.run.log to use temp directory
    temp_log_dir = tmp_path_factory.mktemp("logs")
    
    # Import here to avoid circular dependencies if any
    import src.run.log
    
    # Reset singleton to ensure it gets re-initialized with patched method
    src.run.log._logger = None
    
    original_setup = src.run.log.Logger._setup_current_logger
    
    def safe_setup(self):
        # Redirect to temp dir
        self.log_dir = temp_log_dir
        # Ensure dir exists
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Call original (will create file in temp dir)
        original_setup(self)
        
        # Allow propagation so pytest can capture logs via root logger
        self.logger.propagate = True
        
    with patch("src.run.log.Logger._setup_current_logger", side_effect=safe_setup, autospec=True):
        yield

@pytest.fixture(autouse=True)
def isolate_save_path(monkeypatch, tmp_path):
    """
    Redirect the save path to a temp dir for each test to prevent pollution.

    ``CONFIG.paths`` is an OmegaConf DictConfig. ``monkeypatch.setattr`` on a
    DictConfig is not reliably undone (pytest 9 deletes the attribute on undo
    when it cannot observe the original via ``getattr``/``__dict__``), so the
    original value is saved and restored manually instead.
    """
    import src.utils.config
    from src.utils.config import CONFIG

    # Use a unique name to avoid conflict with tests that create "saves" dir manually
    temp_saves = tmp_path / "test_isolation_saves"
    temp_saves.mkdir(parents=True, exist_ok=True)

    paths = CONFIG.paths
    _missing = object()
    original_saves = paths.get("saves", _missing) if hasattr(paths, "get") else getattr(paths, "saves", _missing)

    # 1. Patch current CONFIG
    paths.saves = temp_saves

    # 2. Patch load_config so any reloads also use the temp dir
    original_load_config = src.utils.config.load_config

    def safe_load_config():
        config = original_load_config()
        if hasattr(config, "paths"):
            config.paths.saves = temp_saves
        return config

    monkeypatch.setattr(src.utils.config, "load_config", safe_load_config)

    try:
        yield temp_saves
    finally:
        if original_saves is _missing:
            try:
                del paths["saves"]
            except Exception:
                pass
        else:
            paths.saves = original_saves


@pytest.fixture(autouse=True)
def fixed_random_seed():
    """
    Ensure all tests have deterministic random behavior.
    This fixture is automatically applied to all tests.
    """
    random.seed(42)
    yield

@pytest.fixture(autouse=True)
def force_default_language():
    """
    Reset language around each test so global i18n state does not leak across tests.
    """
    from src.classes.language import language_manager
    from src.utils.df import reload_game_configs
    default_locale = get_default_locale()

    language_manager.set_language(default_locale)
    reload_game_configs()

    yield

    language_manager.set_language(default_locale)
    reload_game_configs()


@pytest.fixture(autouse=True)
def isolate_server_avatar_assets():
    """
    Keep src.server.main.AVATAR_ASSETS from leaking between API/save-load tests.
    Some tests intentionally rescan all race portraits while others assert a
    narrow patched value, so restore the server cache after each test if loaded.
    """
    module = sys.modules.get("src.server.main")
    original_assets = copy.deepcopy(getattr(module, "AVATAR_ASSETS", None)) if module else None

    yield

    module = sys.modules.get("src.server.main")
    if module is None or not hasattr(module, "AVATAR_ASSETS"):
        return
    module.AVATAR_ASSETS.clear()
    if original_assets is None:
        module.AVATAR_ASSETS.update({"human": {"male": [], "female": []}})
    else:
        module.AVATAR_ASSETS.update(original_assets)


@pytest.fixture(autouse=True)
def isolate_server_runtime_state():
    """
    Keep src.server.main.game_instance from leaking between API/runtime tests.
    Many historical tests still patch the global dict directly; this fixture
    restores the same dict object so runtime wrappers and services keep their
    references while test data is cleaned up.
    """
    module = sys.modules.get("src.server.main")
    original_state = copy.deepcopy(getattr(module, "game_instance", None)) if module else None

    yield

    module = sys.modules.get("src.server.main")
    if module is None or not hasattr(module, "game_instance"):
        return
    if original_state is None:
        from src.server.runtime import create_default_game_state

        original_state = create_default_game_state()
    module.game_instance.clear()
    module.game_instance.update(original_state)
from src.classes.environment.tile import TileType, Tile
from src.classes.core.world import World
from src.systems.time import Month, Year, create_month_stamp
from src.classes.core.avatar import Avatar, Gender
from src.classes.age import Age
from src.systems.cultivation import Realm
from src.utils.id_generator import get_avatar_id
from src.utils.name_generator import get_random_name
from src.classes.root import Root
from src.classes.alignment import Alignment

# Action related imports
from src.classes.items.elixir import Elixir, ElixirType
from src.classes.material import Material
from src.classes.items.weapon import Weapon
from src.classes.weapon_type import WeaponType
from src.classes.items.auxiliary import Auxiliary
from src.classes.environment.region import CityRegion

@pytest.fixture
def base_map():
    """Create a 10x10 map made entirely of plains."""
    width, height = 10, 10
    game_map = Map(width=width, height=height)
    for x in range(width):
        for y in range(height):
            game_map.create_tile(x, y, TileType.PLAIN)
    return game_map

@pytest.fixture
def base_world(base_map):
    """Create a world on top of base_map at Year 1, January."""
    return World(map=base_map, month_stamp=create_month_stamp(Year(1), Month.JANUARY))

@pytest.fixture
def dummy_avatar(base_world):
    """Create a standard male Qi Refinement avatar at (0, 0)."""
    # IDs must not collide (get_avatar_id returns a random UUID, which is fine)
    av = Avatar(
        world=base_world,
        name="TestDummy",
        id=get_avatar_id(),
        birth_month_stamp=create_month_stamp(Year(2000), Month.JANUARY),
        age=Age(20, Realm.Qi_Refinement, innate_max_lifespan=80),
        gender=Gender.MALE,
        pos_x=0,
        pos_y=0,
        root=Root.GOLD, # fixed spirit root
        personas=[],    # clear personas to avoid random effects
        alignment=Alignment.RIGHTEOUS # fixed alignment
    )
    
    # Give a mock weapon so get_avatar_info does not fail
    av.weapon = MagicMock()
    av.weapon.get_detailed_info.return_value = "Test Wooden Sword (Qi Refinement)"
    av.weapon_proficiency = 0.0

    # Force-clear personas (__post_init__ randomizes them when the list is empty)
    av.personas = []
    # Force-clear the technique so a random one cannot add movement-step bonuses
    av.technique = None
    av.recalc_effects()
    
    return av

@pytest.fixture(autouse=True)
def mock_llm_managers():
    """
    Mock every manager/function that calls the LLM so tests never hit a real LLM.
    """
    # Build a mock LLM config
    mock_llm_config = MagicMock()
    mock_llm_config.api_key = "test_key"
    mock_llm_config.base_url = "http://test.api/v1"
    mock_llm_config.model_name = "test-model"
    
    with patch("src.sim.simulator_engine.phases.actions.llm_ai") as mock_ai, \
         patch("src.sim.simulator_engine.phases.lifecycle.process_avatar_long_term_objective", new_callable=AsyncMock) as mock_lto, \
         patch("src.sim.simulator_engine.phases.lifecycle.process_avatar_backstory", new_callable=AsyncMock) as mock_backstory, \
         patch("src.sim.simulator_engine.phases.lifecycle.process_avatar_nickname", new_callable=AsyncMock) as mock_nick, \
         patch("src.classes.relation.relation_resolver.RelationResolver.run_batch", new_callable=AsyncMock) as mock_rr, \
         patch("src.classes.relation.relation_delta_service.call_llm_with_task_name", new_callable=AsyncMock) as mock_relation_delta, \
         patch("src.classes.world_lore.WorldLoreManager.apply_world_lore", new_callable=AsyncMock) as mock_hist, \
         patch("src.classes.story_teller.call_llm_with_task_name", new_callable=AsyncMock) as mock_call_llm_story, \
         patch("src.utils.llm.config.LLMConfig.from_mode", return_value=mock_llm_config) as mock_config:
        
        mock_ai.decide = AsyncMock(return_value={})
        mock_lto.return_value = None
        mock_backstory.return_value = None
        mock_nick.return_value = None
        mock_rr.return_value = []
        mock_relation_delta.return_value = {"delta_a_to_b": 0, "delta_b_to_a": 0}
        mock_hist.return_value = None
        mock_call_llm_story.return_value = {"story": "Test story"}

        yield {
            "ai": mock_ai,
            "lto": mock_lto,
            "backstory": mock_backstory,
            "nick": mock_nick,
            "rr": mock_rr,
            "relation_delta": mock_relation_delta,
            "hist": mock_hist,
            "story": mock_call_llm_story,
            "gathering_story": mock_call_llm_story,
            "config": mock_config
        }

# --- Shared Helpers for Item Creation ---

def create_test_elixir(name, realm, price=100, elixir_id=1, effects=None):
    if effects is None:
        effects = {"max_hp": 10}
    return Elixir(
        id=elixir_id,
        name=name,
        realm=realm,
        type=ElixirType.Breakthrough,
        desc="Test elixir",
        price=price,
        effects=effects
    )

def create_test_material(name, realm, material_id=101):
    return Material(
        id=material_id,
        name=name,
        desc="Test item",
        realm=realm
    )

def create_test_weapon(name, realm, weapon_id=201):
    return Weapon(
        id=weapon_id,
        name=name,
        weapon_type=WeaponType.SWORD,
        realm=realm,
        desc="Test weapon",
        effects={},
        effect_desc=""
    )

def create_test_auxiliary(name, realm, aux_id=301):
    return Auxiliary(
        id=aux_id,
        name=name,
        realm=realm,
        desc="Test auxiliary",
        effects={},
        effect_desc=""
    )

@pytest.fixture
def avatar_in_city(dummy_avatar):
    """
    Place dummy_avatar in a city and give it starting funds.
    """
    city_region = CityRegion(id=1, name="TestCity", desc="Test city")
    tile = Tile(0, 0, TileType.CITY)
    tile.region = city_region
    
    dummy_avatar.tile = tile
    dummy_avatar.magic_stone = 1000
    dummy_avatar.cultivation_progress.realm = Realm.Qi_Refinement
    dummy_avatar.elixirs = []
    dummy_avatar.materials = {} # make sure the inventory is empty
    dummy_avatar.weapon = None
    dummy_avatar.auxiliary = None
    
    return dummy_avatar

@pytest.fixture
def mock_item_data():
    """
    Provide a standard set of test items: material, elixirs, weapon, auxiliary.
    Returns a dict of these objects for convenient use in mocks.
    """
    test_elixir = create_test_elixir("Qi Gathering Pill", Realm.Qi_Refinement, price=100)
    high_level_elixir = create_test_elixir("Foundation Pill", Realm.Foundation_Establishment, price=1000, elixir_id=2)
    test_material = create_test_material("Iron Ore", Realm.Qi_Refinement)
    test_weapon = create_test_weapon("Azure Cloud Sword", Realm.Qi_Refinement)
    test_auxiliary = create_test_auxiliary("Spirit Gathering Orb", Realm.Qi_Refinement)

    return {
        "elixirs": {
            "Qi Gathering Pill": [test_elixir],
            "Foundation Pill": [high_level_elixir]
        },
        "materials": {
            "Iron Ore": test_material
        },
        "weapons": {
            "Azure Cloud Sword": test_weapon
        },
        "auxiliaries": {
            "Spirit Gathering Orb": test_auxiliary
        },
        # Direct access
        "obj_elixir": test_elixir,
        "obj_high_elixir": high_level_elixir,
        "obj_material": test_material,
        "obj_weapon": test_weapon,
        "obj_auxiliary": test_auxiliary
    }
