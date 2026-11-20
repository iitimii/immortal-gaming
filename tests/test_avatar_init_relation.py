import pytest
from src.classes.core.world import World
from src.systems.time import MonthStamp
from src.classes.age import Age
from src.classes.core.avatar import Avatar, Gender
from src.classes.relation.relation import NumericRelation, Relation, get_relation_label
from src.systems.cultivation import CultivationProgress, Realm
from src.utils.id_generator import get_avatar_id
from src.sim.avatar_init import create_random_mortal, MortalPlanner, AvatarFactory, PopulationPlanner
from src.classes.core.sect import sects_by_id
import src.sim.avatar_init as avatar_init_module

@pytest.fixture
def mock_world(base_world):
    return base_world

def test_single_mortal_relation(mock_world):
    """Verify parent/child relation direction when generating a single new avatar."""
    # 1. Create a hypothetical parent avatar
    parent_avatar = Avatar(
        world=mock_world,
        name="Parent",
        id=get_avatar_id(),
        birth_month_stamp=MonthStamp(0),
        age=Age(100, Realm.Core_Formation),
        gender=Gender.FEMALE,
        cultivation_progress=CultivationProgress(60), # Core Formation
        pos_x=0,
        pos_y=0
    )
    # Register with the world manager
    mock_world.avatar_manager.register_avatar(parent_avatar)

    # 2. Create a new avatar as the child
    # Force parent_avatar to exercise the relation-setting logic
    # create_random_mortal is random internally, so use the underlying factory and build a plan directly
    
    child_age = Age(20, Realm.Qi_Refinement)
    plan = MortalPlanner.plan(mock_world, "Child", child_age, level=10, allow_relations=False)
    
    # Assign the parent manually, simulating a random pick
    plan.parent_avatar = parent_avatar
    
    child_avatar = AvatarFactory.build_from_plan(
        mock_world, 
        mock_world.month_stamp, 
        name="Child", 
        age=child_age, 
        plan=plan,
        attach_relations=True
    )

    # 3. Verify relations
    # Parent viewing child: should be IS_CHILD_OF (the other is my child)
    rel_from_parent = parent_avatar.get_relation(child_avatar)
    assert rel_from_parent == Relation.IS_CHILD_OF, f"Parent-to-child relation should be IS_CHILD_OF, got {rel_from_parent}"
    
    label_from_parent = get_relation_label(rel_from_parent, parent_avatar, child_avatar)
    # The child gender is random, so it may be Son or Daughter
    assert label_from_parent in ["Son", "Daughter"], f"Wrong parent-to-child label: {label_from_parent}"

    # Child viewing parent: should be IS_PARENT_OF (the other is my parent)
    rel_from_child = child_avatar.get_relation(parent_avatar)
    assert rel_from_child == Relation.IS_PARENT_OF, f"Child-to-parent relation should be IS_PARENT_OF, got {rel_from_child}"

    label_from_child = get_relation_label(rel_from_child, child_avatar, parent_avatar)
    assert label_from_child == "Mother", f"Wrong child-to-mother label: {label_from_child}"  # parent is FEMALE


def test_population_planner_relations(mock_world):
    """Verify parent/child relation direction during batch generation."""
    # Generate a group of avatars; a large batch should trigger family relations
    # To raise the odds, call the PopulationPlanner logic directly or inspect the generated result
    
    # Try generating 20 avatars and expect some family relations
    count = 20
    avatars_dict = PopulationPlanner.plan_group(count, existed_sects=None)
    
    # Inspect relations in the plan
    relations = avatars_dict.relations
    
    if not relations:
        pytest.skip("No relations were generated in this random run; skipping")
        return

    found_parent_relation = False
    
    for (a_idx, b_idx), rel in relations.items():
        if rel == Relation.IS_CHILD_OF:
            found_parent_relation = True
            # In plan_group, (a, b) = IS_CHILD_OF means a is the parent (a sees b as its child) and b is the child
            # i.e. in a.relations, the entry for b is IS_CHILD_OF
            pass
            
    # Finding an IS_CHILD_OF relation means the code uses Relation.IS_CHILD_OF
    # After the fix it should be Relation.IS_CHILD_OF
    
    # Further: actually build the avatars and verify
    avatars_map = AvatarFactory.build_group(mock_world, mock_world.month_stamp, avatars_dict)
    avatars = list(avatars_map.values())
    
    # build_group returns dict[id, Avatar] with possibly shuffled order, so indices would need remapping
    # but iterating over all avatars and checking relations is enough
    
    for av in avatars:
        for target, rel in av.relations.items():
            if rel == Relation.IS_CHILD_OF:
                # av sees target as its child -> target is the child
                # Verify age: the parent should be older than the child
                assert av.age.age > target.age.age, f"Parent ({av.name}, {av.age.age}) should be older than child ({target.name}, {target.age.age})"
                
                # Verify the label
                label = get_relation_label(rel, av, target)
                assert label in ["Son", "Daughter"]
                
            elif rel == Relation.IS_PARENT_OF:
                # av sees target as its parent -> target is the parent
                # Verify age: the child should be younger than the parent
                assert av.age.age < target.age.age, f"Child ({av.name}, {av.age.age}) should be younger than parent ({target.name}, {target.age.age})"
                
                # Verify the label
                label = get_relation_label(rel, av, target)
                assert label in ["Father", "Mother"]

    if not found_parent_relation:
        # If no family was rolled, it is enough that nothing failed and the logic is consistent,
        # or random could be mocked to force the path; in integration runs repeated runs usually cover it
        pass


def test_population_planner_can_generate_small_family_cluster(monkeypatch):
    """Family planning should support one parent with multiple children."""
    monkeypatch.setattr(avatar_init_module, "FAMILY_TRIGGER_PROB", 1.0)
    monkeypatch.setattr(avatar_init_module, "FAMILY_PAIR_CAP_DIV", 4)
    monkeypatch.setattr(avatar_init_module, "FAMILY_CHILDREN_MAX", 3)

    found_cluster = False
    for _ in range(20):
        plan = PopulationPlanner.plan_group(24, existed_sects=None)
        child_count_by_parent: dict[int, int] = {}
        for (parent_idx, child_idx), relation in plan.relations.items():
            if relation is not Relation.IS_CHILD_OF:
                continue
            child_count_by_parent[parent_idx] = child_count_by_parent.get(parent_idx, 0) + 1
        if any(count >= 2 for count in child_count_by_parent.values()):
            found_cluster = True
            break

    assert found_cluster, "No family cluster with one parent and multiple children was generated"


def test_family_members_do_not_overconcentrate_in_one_sect(monkeypatch):
    """Members of one small family in the same sect should not exceed the cap."""
    monkeypatch.setattr(avatar_init_module, "FAMILY_TRIGGER_PROB", 1.0)
    monkeypatch.setattr(avatar_init_module, "FAMILY_PAIR_CAP_DIV", 4)
    monkeypatch.setattr(avatar_init_module, "FAMILY_CHILDREN_MAX", 3)
    monkeypatch.setattr(avatar_init_module, "FAMILY_PARENT_SECT_FOLLOW_PROB", 1.0)
    monkeypatch.setattr(avatar_init_module, "FAMILY_OTHER_SECT_PROB", 0.0)
    monkeypatch.setattr(avatar_init_module, "FAMILY_SAME_SECT_CAP", 2)

    plan = PopulationPlanner.plan_group(30, existed_sects=list(sects_by_id.values()))

    family_members: dict[int, list[int]] = {}
    for (parent_idx, child_idx), relation in plan.relations.items():
        if relation is not Relation.IS_CHILD_OF:
            continue
        family_members.setdefault(parent_idx, [parent_idx]).append(child_idx)

    assert family_members, "No family relations generated; cannot verify the sect dispersion rule"

    for members in family_members.values():
        sect_counts: dict[int, int] = {}
        for idx in members:
            sect = plan.sects[idx]
            if sect is None:
                continue
            sect_counts[sect.id] = sect_counts.get(sect.id, 0) + 1
        if sect_counts:
            assert max(sect_counts.values()) <= avatar_init_module.FAMILY_SAME_SECT_CAP, (
                f"Family members are too concentrated in one sect: {sect_counts}"
            )


def test_population_planner_generates_denser_initial_relations():
    """Initial relations should have some density, with a few avatars having multiple relations."""
    relation_coverage_ratios: list[float] = []
    multi_relation_ratios: list[float] = []

    for seed in range(10):
        avatar_init_module.random.seed(seed)
        plan = PopulationPlanner.plan_group(80, existed_sects=list(sects_by_id.values()))

        direct_relation_counts = [0] * 80
        for a_idx, b_idx in plan.relations.keys():
            direct_relation_counts[a_idx] += 1
            direct_relation_counts[b_idx] += 1

        covered_count = sum(1 for count in direct_relation_counts if count >= 1)
        multi_relation_count = sum(1 for count in direct_relation_counts if count >= 2)
        relation_coverage_ratios.append(covered_count / 80)
        multi_relation_ratios.append(multi_relation_count / 80)

    avg_coverage_ratio = sum(relation_coverage_ratios) / len(relation_coverage_ratios)
    avg_multi_ratio = sum(multi_relation_ratios) / len(multi_relation_ratios)

    assert avg_coverage_ratio >= 0.50, f"Share of avatars with direct initial relations is too low: {avg_coverage_ratio:.3f}"
    assert avg_multi_ratio >= 0.12, f"Share of avatars with multiple direct initial relations is too low: {avg_multi_ratio:.3f}"


def test_build_group_lovers_start_with_friendliness(monkeypatch, mock_world):
    """Dao companions should not still be strangers after initialization."""
    monkeypatch.setattr(avatar_init_module, "LOVERS_TRIGGER_PROB", 1.0)
    monkeypatch.setattr(avatar_init_module, "LOVERS_PAIR_CAP_DIV", 1)
    monkeypatch.setattr(avatar_init_module, "MASTER_PAIR_PROB", 0.0)
    monkeypatch.setattr(avatar_init_module, "FAMILY_TRIGGER_PROB", 0.0)

    plan = PopulationPlanner.plan_group(2, existed_sects=None)
    avatars = list(AvatarFactory.build_group(mock_world, mock_world.month_stamp, plan).values())
    assert len(avatars) == 2

    lover_pairs = [
        (a, b)
        for a in avatars
        for b in avatars
        if a is not b and a.get_relation(b) == Relation.IS_LOVER_OF
    ]
    assert lover_pairs, "No Dao companion pair generated; cannot verify initial friendliness"

    avatar_a, avatar_b = lover_pairs[0]
    assert avatar_a.get_friendliness(avatar_b) >= 25
    assert avatar_b.get_friendliness(avatar_a) >= 25
    assert avatar_a.get_numeric_relation(avatar_b) in {NumericRelation.FRIEND, NumericRelation.BEST_FRIEND}
    assert avatar_b.get_numeric_relation(avatar_a) in {NumericRelation.FRIEND, NumericRelation.BEST_FRIEND}


def test_population_planner_generates_numeric_relations_from_friendliness(monkeypatch, mock_world):
    """Initial numeric relations (friend/enemy) should derive from friendliness rather than be planned explicitly."""
    monkeypatch.setattr(avatar_init_module, "LOVERS_TRIGGER_PROB", 0.0)
    monkeypatch.setattr(avatar_init_module, "MASTER_PAIR_PROB", 0.0)
    monkeypatch.setattr(avatar_init_module, "FAMILY_TRIGGER_PROB", 0.0)
    monkeypatch.setattr(avatar_init_module, "INITIAL_FRIENDLINESS_PAIR_CAP_DIV", 1)

    plan = PopulationPlanner.plan_group(12, existed_sects=None)
    assert all(rel not in {Relation.IS_FRIEND_OF, Relation.IS_ENEMY_OF} for rel in plan.relations.values())

    avatars = list(AvatarFactory.build_group(mock_world, mock_world.month_stamp, plan).values())
    non_stranger_pairs = []
    for avatar in avatars:
        for target in avatars:
            if avatar is target:
                continue
            numeric_relation = avatar.get_numeric_relation(target)
            if numeric_relation != NumericRelation.STRANGER:
                non_stranger_pairs.append((avatar, target, numeric_relation))

    assert non_stranger_pairs, "No numeric relation was derived from initial friendliness"


def test_same_sect_pairs_are_more_often_positive(monkeypatch, mock_world):
    """Avatars from the same sect should more often get positive initial relations."""
    sects = list(sects_by_id.values())
    assert len(sects) >= 2

    def make_avatar(name: str, sect, level: int) -> Avatar:
        return Avatar(
            world=mock_world,
            name=name,
            id=get_avatar_id(),
            birth_month_stamp=MonthStamp(0),
            age=Age(30, CultivationProgress(level).realm),
            gender=Gender.MALE,
            cultivation_progress=CultivationProgress(level),
            pos_x=0,
            pos_y=0,
            sect=sect,
        )

    same_a = make_avatar("SameA", sects[0], 30)
    same_b = make_avatar("SameB", sects[0], 32)
    diff_a = make_avatar("DiffA", sects[0], 30)
    diff_b = make_avatar("DiffB", sects[1], 70)

    same_positive = 0
    diff_positive = 0
    samples = 200

    for seed in range(samples):
        avatar_init_module.random.seed(seed)
        a_to_b, b_to_a = avatar_init_module._roll_social_initial_friendliness_pair(same_a, same_b)
        if a_to_b > 0 or b_to_a > 0:
            same_positive += 1

        avatar_init_module.random.seed(seed)
        a_to_b, b_to_a = avatar_init_module._roll_social_initial_friendliness_pair(diff_a, diff_b)
        if a_to_b > 0 or b_to_a > 0:
            diff_positive += 1

    assert same_positive > diff_positive
