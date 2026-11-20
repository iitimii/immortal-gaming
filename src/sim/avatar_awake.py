import random
from typing import List, Optional

from src.classes.core.world import World
from src.classes.core.avatar import Avatar, Gender
from src.classes.mortal import Mortal
from src.systems.time import MonthStamp
from src.systems.cultivation import CultivationProgress, Realm
from src.classes.age import Age
from src.classes.relation.relation import Relation
from src.classes.root import Root
from src.classes.items.magic_stone import MagicStone
from src.classes.death_reason import DeathReason, DeathType
from src.classes.death import handle_death
from src.classes.event import Event
from src.utils.id_generator import get_avatar_id
from src.classes.technique import attribute_to_root
from src.classes.items.weapon import get_random_weapon_by_realm
from src.utils.config import CONFIG
from src.utils.born_region import get_born_region_id
from src.i18n import t
from src.classes.race import Race, roll_avatar_race
from src.systems.world_secret import sync_avatar_public_world_secret_knowledge

# Constants
MIN_AWAKENING_AGE = 16
MAX_AWAKENING_AGE = 60 # Maximum age at which a mortal can awaken
BLOODLINE_AWAKENING_RATE = 0.05 # Monthly awakening probability for each eligible mortal
WILD_AWAKENING_RATE_BASE = 0.1 # Base wild awakening rate (if not configured)


def _register_avatar_and_resolve_lifespan(world: World, avatar: Avatar) -> None:
    """Register a newly awakened avatar, then resolve an immediately expired lifespan.

    Registration must happen before death resolution so the usual death path
    can archive the avatar, create a grave POI, and emit client deltas.
    """
    world.avatar_manager.register_avatar(avatar, is_newly_born=True)
    if avatar.age.age >= avatar.age.max_lifespan:
        handle_death(world, avatar, DeathReason(DeathType.OLD_AGE))

def process_awakening(world: World) -> List[Event]:
    events = []
    
    # 1. Bloodline awakening (existing mortals)
    events.extend(_process_bloodline_awakening(world))
    
    # 2. Fortuitous awakening (wild avatars)
    # Read the awakening rate from config
    run_config = getattr(world, "run_config_snapshot", {}) or {}
    wild_rate = run_config.get("npc_awakening_rate_per_month", WILD_AWAKENING_RATE_BASE)
    
    if random.random() < wild_rate:
        wild_event = _process_wild_awakening(world)
        if wild_event:
            events.append(wild_event)
            
    return events

def _process_bloodline_awakening(world: World) -> List[Event]:
    events = []
    # Get candidates
    candidates = world.mortal_manager.get_awakening_candidates(world.month_stamp, min_age=MIN_AWAKENING_AGE)
    
    for mortal in candidates:
        # Past the age cap, no more awakening (can only wait to die)
        current_age_years = (int(world.month_stamp) - int(mortal.birth_month_stamp)) // 12
        if current_age_years > MAX_AWAKENING_AGE:
            continue
            
        # Roll for awakening
        if random.random() < BLOODLINE_AWAKENING_RATE:
            avatar = _promote_mortal_to_avatar(world, mortal)
            sync_avatar_public_world_secret_knowledge(world, avatar)

            _register_avatar_and_resolve_lifespan(world, avatar)

            # Remove the Mortal
            world.mortal_manager.remove_mortal(mortal.id)

            if avatar.is_dead:
                desc = t("{name} awakened spiritual roots, but their lifespan was already exhausted.", name=avatar.name)
            else:
                desc = t("{name} has awakened their spiritual roots and embarked on the path of cultivation.", name=avatar.name)
            event = Event(world.month_stamp, desc, related_avatars=[avatar.id])
            events.append(event)
            
    return events

def _process_wild_awakening(world: World) -> Optional[Event]:
    # Randomly generate a new wild avatar
    gender = random.choice(list(Gender))
    race = roll_avatar_race()
    from src.utils.name_generator import get_random_name_for_race
    name = get_random_name_for_race(gender, race)
    
    age_val = random.randint(MIN_AWAKENING_AGE, 30)
    
    # Build the Avatar
    born_id = get_born_region_id(world, race=race)
    avatar = _create_simple_avatar(world, name, gender, age_val, parents=[], born_region_id=born_id, race=race)
    sync_avatar_public_world_secret_knowledge(world, avatar)
    
    _register_avatar_and_resolve_lifespan(world, avatar)

    if avatar.is_dead:
        desc = t("A rogue cultivator {name} appeared, but their lifespan was already exhausted.", name=avatar.name)
    else:
        desc = t("A rogue cultivator {name} has appeared in the world.", name=avatar.name)
    event = Event(world.month_stamp, desc, related_avatars=[avatar.id])
    return event

def _promote_mortal_to_avatar(world: World, mortal: Mortal) -> Avatar:
    # Compute current age
    age_years = (int(world.month_stamp) - int(mortal.birth_month_stamp)) // 12
    
    avatar = _create_simple_avatar(
        world, 
        mortal.name, 
        mortal.gender, 
        age_years, 
        parents=mortal.parents,
        mortal_id=mortal.id, # Reuse the ID
        race=getattr(mortal, "race", None),
        born_region_id=mortal.born_region_id,
    )
    
    return avatar

def _create_simple_avatar(
    world: World, 
    name: str, 
    gender: Gender, 
    age_years: int, 
    parents: List[str],
    mortal_id: Optional[str] = None,
    born_region_id: Optional[int] = None,
    race: Optional[Race] = None,
) -> Avatar:
    # 1. Basic attributes
    level = 1
    cultivation = CultivationProgress(level)
    age = Age(
        age_years,
        cultivation.realm,
        innate_max_lifespan=Age.roll_innate_max_lifespan(),
    )
    
    # Reuse the ID or generate a new one
    aid = mortal_id if mortal_id else get_avatar_id()
    
    # Random birth location
    x = random.randint(0, world.map.width - 1)
    y = random.randint(0, world.map.height - 1)
    
    birth_stamp = world.month_stamp - age_years * 12
    avatar_race = race or roll_avatar_race()
    if born_region_id is None:
        born_region_id = get_born_region_id(world, race=avatar_race)
    
    avatar = Avatar(
        world=world,
        name=name,
        id=aid,
        birth_month_stamp=MonthStamp(int(birth_stamp)),
        age=age,
        gender=gender,
        cultivation_progress=cultivation,
        pos_x=x,
        pos_y=y,
        root=random.choice(list(Root)),
        sect=None, # Newly awakened avatars are rogue cultivators by default
        born_region_id=born_region_id,
        race=avatar_race,
    )
    
    avatar.cultivation_start_month_stamp = world.month_stamp
    
    avatar.magic_stone = MagicStone(10) # A few spirit stones
    avatar.tile = world.map.get_tile(x, y)
    
    # 2. Equipment and technique (simplified setup)
    # Weapon: one Qi Refinement weapon
    avatar.weapon = get_random_weapon_by_realm(avatar.cultivation_progress.realm)
    # Auxiliary: none
    avatar.auxiliary = None
    
    # Technique: none yet
    # Newly awakened mortals only have a spirit root and have not learned a technique (or could be given a basic one)
    # avatar.technique = ...
    
    # 3. Bind relations
    for pid in parents:
        parent = world.avatar_manager.get_avatar(pid)
        if parent:
            # Establish relation (Parent -> Child)
            # Semantics: Parent recognizes Avatar as its child
            parent.acknowledge_child(avatar)

    return avatar
