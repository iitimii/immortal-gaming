import pytest
from unittest.mock import MagicMock

from src.classes.ranking import RankingManager
from src.systems.cultivation import Realm, CultivationProgress
from src.classes.core.sect import Sect, SectHeadQuarter
from src.classes.alignment import Alignment

@pytest.fixture
def test_sect():
    hq = SectHeadQuarter(name="Test HQ", desc="Test HQ description", image="test.png")
    sect = Sect(
        id=1,
        name="Test Sect",
        desc="Test",
        member_act_style="Test style",
        alignment=Alignment.RIGHTEOUS,
        headquarter=hq,
        technique_names=[]
    )
    return sect

def test_update_rankings_empty():
    manager = RankingManager()
    manager.update_rankings([])
    
    data = manager.get_rankings_data()
    assert len(data["heaven"]) == 0
    assert len(data["earth"]) == 0
    assert len(data["human"]) == 0
    # sect is populated from global sects_by_id, so it might not be empty if there are global sects.
    # We will mock the sects_by_id or just let it be.

def test_update_rankings_avatars(dummy_avatar, test_sect):
    manager = RankingManager()
    
    # Build a Human Ranking (Foundation Establishment) avatar
    human_avatar = MagicMock()
    human_avatar.id = "human_1"
    human_avatar.name = "Human"
    human_avatar.sect = test_sect
    human_avatar.cultivation_progress = CultivationProgress(31) # Foundation Establishment Early Stage
    human_avatar.is_dead = False
    
    # Build an Earth Ranking (Core Formation) avatar
    earth_avatar = MagicMock()
    earth_avatar.id = "earth_1"
    earth_avatar.name = "Earth"
    earth_avatar.sect = None # rogue cultivator
    earth_avatar.cultivation_progress = CultivationProgress(61) # Core Formation Early Stage
    earth_avatar.is_dead = False
    
    # Build a Heaven Ranking (Nascent Soul) avatar
    heaven_avatar = MagicMock()
    heaven_avatar.id = "heaven_1"
    heaven_avatar.name = "Heaven"
    heaven_avatar.sect = test_sect
    heaven_avatar.cultivation_progress = CultivationProgress(91) # Nascent Soul Early Stage
    heaven_avatar.is_dead = False
    
    # get_base_strength derives from realm and effects, so instead of mocking it
    # we build three real Avatars from dummy_avatar for convenience.
    import copy
    import uuid
    
    av1 = copy.deepcopy(dummy_avatar)
    av1.id = str(uuid.uuid4())
    av1.name = "Human"
    av1.cultivation_progress.level = 31
    av1.cultivation_progress.realm = Realm.Foundation_Establishment
    av1.sect = test_sect
    test_sect.add_member(av1)
    
    av2 = copy.deepcopy(dummy_avatar)
    av2.id = str(uuid.uuid4())
    av2.name = "Earth"
    av2.cultivation_progress.level = 61
    av2.cultivation_progress.realm = Realm.Core_Formation
    av2.sect = None
    
    av3 = copy.deepcopy(dummy_avatar)
    av3.id = str(uuid.uuid4())
    av3.name = "Heaven"
    av3.cultivation_progress.level = 91
    av3.cultivation_progress.realm = Realm.Nascent_Soul
    av3.sect = test_sect
    test_sect.add_member(av3)

    # Patch sects_by_id to contain only test_sect so the sect ranking can be tested
    with pytest.MonkeyPatch.context() as m:
        m.setattr("src.classes.core.sect.sects_by_id", {1: test_sect})
        manager.update_rankings([av1, av2, av3])
    
    data = manager.get_rankings_data()
    
    # Verify the Heaven Ranking
    assert len(data["heaven"]) == 1
    assert data["heaven"][0]["name"] == "Heaven"
    assert data["heaven"][0]["sect"] == "Test Sect"
    assert data["heaven"][0]["realm"] == "NASCENT_SOUL"
    assert data["heaven"][0]["stage"] == "EARLY_STAGE"
    assert data["heaven"][0]["cultivation_display"] == "Nascent Soul Early Stage"
    
    # Verify the Earth Ranking
    assert len(data["earth"]) == 1
    assert data["earth"][0]["name"] == "Earth"
    assert data["earth"][0]["sect"] == "Rogue Cultivator"
    assert data["earth"][0]["cultivation"]["realm_id"] == "CORE_FORMATION"
    
    # Verify the Human Ranking
    assert len(data["human"]) == 1
    assert data["human"][0]["name"] == "Human"
    assert data["human"][0]["sect"] == "Test Sect"
    
    # Verify the Sect Ranking
    assert len(data["sect"]) == 1
    assert data["sect"][0]["name"] == "Test Sect"
    assert data["sect"][0]["member_count"] == 2
    # Total sect power should be positive
    assert data["sect"][0]["total_power"] > 0
    
def test_ranking_sorting(dummy_avatar):
    """Avatars in the same realm are sorted by battle strength."""
    manager = RankingManager()
    
    import copy
    import uuid
    from src.systems.battle import get_base_strength
    
    av1 = copy.deepcopy(dummy_avatar)
    av1.id = str(uuid.uuid4())
    av1.name = "Weak Nascent"
    av1.update_cultivation(91) # Nascent Soul Early Stage
    
    av2 = copy.deepcopy(dummy_avatar)
    av2.id = str(uuid.uuid4())
    av2.name = "Strong Nascent"
    av2.update_cultivation(111) # Nascent Soul Late Stage

    print(f"av1 strength: {get_base_strength(av1)}")
    print(f"av2 strength: {get_base_strength(av2)}")

    manager.update_rankings([av1, av2])
    
    data = manager.get_rankings_data()
    print(data["heaven"])
    assert len(data["heaven"]) == 2
    # Stronger avatars rank first
    assert data["heaven"][0]["name"] == "Strong Nascent"
    assert data["heaven"][1]["name"] == "Weak Nascent"

def test_init_tournament_info():
    manager = RankingManager()
    
    # start_year = 100, first tournament should be year 101
    
    # Case 1: Before first tournament
    manager.init_tournament_info(100, 100, 1)
    assert manager.tournament_info["next_year"] == 101
    
    # Case 2: During first tournament month
    manager.init_tournament_info(100, 101, 1)
    assert manager.tournament_info["next_year"] == 101
    
    # Case 3: After first tournament month in the same year
    manager.init_tournament_info(100, 101, 2)
    assert manager.tournament_info["next_year"] == 111
    
    # Case 4: Between tournaments
    manager.init_tournament_info(100, 105, 1)
    assert manager.tournament_info["next_year"] == 111
    
    # Case 5: During second tournament month
    manager.init_tournament_info(100, 111, 1)
    assert manager.tournament_info["next_year"] == 111
    
    # Case 6: After second tournament month
    manager.init_tournament_info(100, 111, 12)
    assert manager.tournament_info["next_year"] == 121

