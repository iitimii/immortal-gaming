import pytest
from src.classes.relation.relation import Relation, is_innate
from src.classes.relation.relations import get_possible_new_relations, cancel_relation
from src.classes.core.avatar import Avatar, Gender
from src.classes.age import Age
from src.systems.cultivation import Realm, CultivationProgress
from src.systems.time import MonthStamp
from src.utils.id_generator import get_avatar_id

@pytest.fixture
def base_avatars(base_world):
    """
    Provide a set of base avatars for testing, with different levels and genders.
    """
    def _create(name, gender, level):
        return Avatar(
            world=base_world,
            name=name,
            id=get_avatar_id(),
            birth_month_stamp=MonthStamp(0),
            age=Age(20, CultivationProgress(level).realm),
            gender=gender,
            cultivation_progress=CultivationProgress(level),
            pos_x=0, pos_y=0
        )
    
    male_low = _create("MaleLow", Gender.MALE, 10)
    female_low = _create("FemaleLow", Gender.FEMALE, 10)
    male_high = _create("MaleHigh", Gender.MALE, 50) # Level 50 > 10 + 20
    female_high = _create("FemaleHigh", Gender.FEMALE, 50)
    
    return {
        "male_low": male_low,
        "female_low": female_low,
        "male_high": male_high,
        "female_high": female_high
    }

def test_relation_rules_lovers(base_avatars):
    """
    Test the rules for forming Dao companion relations:
    1. Opposite genders can become Dao companions (IS_LOVER_OF)
    2. Same gender cannot become Dao companions
    3. Existing Dao companions no longer appear in the candidate list
    """
    m = base_avatars["male_low"]
    f = base_avatars["female_low"]
    m2 = base_avatars["male_high"]
    
    # 1. Opposite gender
    # Possible relations of f relative to m
    candidates = get_possible_new_relations(m, f)
    assert Relation.IS_LOVER_OF in candidates
    
    # 2. Same gender
    candidates_same = get_possible_new_relations(m, m2)
    assert Relation.IS_LOVER_OF not in candidates_same
    
    # 3. Already exists
    m.become_lovers_with(f)
    candidates_exist = get_possible_new_relations(m, f)
    assert Relation.IS_LOVER_OF not in candidates_exist

def test_relation_rules_master(base_avatars):
    """
    Test level limits for taking a master (MASTER):
    1. Other level >= own level + 20: can take them as master (IS_MASTER_OF)
    2. Other level < own level + 20: cannot take them as master
    """
    low = base_avatars["male_low"]   # Lv 10
    high = base_avatars["male_high"] # Lv 50
    
    # 1. Take a master (is high the master of low?)
    # get_possible_new_relations(from, to) returns the relation of to relative to from
    # i.e. check whether high can be the MASTER of low
    candidates = get_possible_new_relations(low, high)
    assert Relation.IS_MASTER_OF in candidates
    
    # 2. Level too low (is low the master of high?) -> impossible
    candidates_rev = get_possible_new_relations(high, low)
    assert Relation.IS_MASTER_OF not in candidates_rev

def test_relation_rules_disciple(base_avatars):
    """
    Test level limits for taking a disciple (DISCIPLE):
    1. Other level <= own level - 20: can take them as disciple (IS_DISCIPLE_OF)
    2. Other level > own level - 20: cannot take them as disciple
    """
    low = base_avatars["male_low"]   # Lv 10
    high = base_avatars["male_high"] # Lv 50
    
    # 1. Take a disciple (is low the disciple of high?)
    # get_possible_new_relations(from, to) -> what is to relative to from?
    # Check whether low can be the DISCIPLE of high
    candidates = get_possible_new_relations(high, low)
    assert Relation.IS_DISCIPLE_OF in candidates
    
    # 2. Level too high (is high the disciple of low?) -> impossible
    candidates_rev = get_possible_new_relations(low, high)
    assert Relation.IS_DISCIPLE_OF not in candidates_rev

def test_relation_reciprocal_consistency(base_avatars):
    """
    Test bidirectional consistency of the semantic relation methods:
    1. A acknowledge_master(B) -> A stores IS_MASTER_OF, B stores IS_DISCIPLE_OF
    2. A acknowledge_parent(B) -> A stores IS_PARENT_OF, B stores IS_CHILD_OF
    3. A make_friend_with(B) -> both store IS_FRIEND_OF
    """
    a = base_avatars["male_low"]
    b = base_avatars["female_high"]
    
    # 1. Master/Disciple
    a.acknowledge_master(b)
    assert a.get_relation(b) == Relation.IS_MASTER_OF
    assert b.get_relation(a) == Relation.IS_DISCIPLE_OF
    
    # Cleanup
    a.clear_relation(b)
    assert a.get_relation(b) is None
    
    # 2. Parent/Child
    a.acknowledge_parent(b)
    assert a.get_relation(b) == Relation.IS_PARENT_OF
    assert b.get_relation(a) == Relation.IS_CHILD_OF
    
    a.clear_relation(b)
    
    # 3. Friend (Symmetric)
    a.make_friend_with(b)
    assert a.get_relation(b) == Relation.IS_FRIEND_OF
    assert b.get_relation(a) == Relation.IS_FRIEND_OF

def test_relation_cancel_rules(base_avatars):
    """
    Test relation cancellation rules:
    1. Acquired relations (e.g. friend, master/disciple) can be cancelled
    2. Innate relations (e.g. parent, child) cannot be cancelled
    """
    a = base_avatars["male_low"]
    b = base_avatars["female_high"]
    
    # 1. Acquired relation (Friend)
    a.make_friend_with(b)
    success = cancel_relation(a, b, Relation.IS_FRIEND_OF)
    assert success is True
    assert a.get_relation(b) is None
    
    # 2. Innate relation (Parent)
    # First verify PARENT is innate
    assert is_innate(Relation.IS_PARENT_OF) is True
    
    a.acknowledge_parent(b)
    success = cancel_relation(a, b, Relation.IS_PARENT_OF)
    assert success is False # should fail
    assert a.get_relation(b) == Relation.IS_PARENT_OF # the relation still exists

def test_relation_rules_desc_contains_all_rules():
    """
    Test that the relation-rules description function includes every rule translation,
    so no information is lost because a translation is missing (the raw msgid is returned).
    """
    from src.classes.relation.relation import get_relation_rules_desc, ADD_RELATION_RULES, CANCEL_RELATION_RULES
    
    desc = get_relation_rules_desc()
    
    # Every relation formation/cancellation rule should be translated rather than left as a raw msgid
    # get_relation_rules_desc calls t() internally
    for rel, msgid in ADD_RELATION_RULES.items():
        assert msgid not in desc, f"Missing translation, or the formation rule translation is absent from the description: {msgid}"
        
    for rel, msgid in CANCEL_RELATION_RULES.items():
        assert msgid not in desc, f"Missing translation, or the cancellation rule translation is absent from the description: {msgid}"
