import random
from src.classes.core.world import World
from src.classes.core.avatar import Avatar, Gender
from src.classes.relation.relation import Relation
from src.classes.mortal import Mortal
from src.classes.event import Event
from src.utils.config import CONFIG
from src.utils.name_generator import get_random_name_with_surname, get_random_name_for_race
from src.utils.id_generator import get_avatar_id
from src.utils.born_region import get_born_region_id
from src.i18n import t
from src.classes.race import get_avatar_race


def _resolve_child_race(parent1: Avatar, parent2: Avatar):
    race1 = get_avatar_race(parent1)
    race2 = get_avatar_race(parent2)
    if race1.id == race2.id:
        return race1
    if race1.is_yao and race2.is_yao:
        return random.choice([race1, race2])
    yao_parent_race = race1 if race1.is_yao else race2 if race2.is_yao else None
    if yao_parent_race is not None and random.random() < 0.5:
        return yao_parent_race
    return get_avatar_race(None)

def process_births(world: World) -> list[Event]:
    """
    Handle birth logic in the world.
    Iterate over all living avatars, check eligible Dao companions and try to produce children.
    
    Returns:
        List of generated events
    """
    events = []
    
    birth_rate = CONFIG.world.birth_rate_per_month
    max_children = CONFIG.world.max_children_per_couple
    current_time = int(world.month_stamp)
    processed_couples = set()

    living_avatars = world.avatar_manager.get_living_avatars()

    for avatar in living_avatars:
        # 1. Find Dao companions
        partner: Avatar | None = None
        for target, state in avatar.relations.items():
            if Relation.IS_LOVER_OF in state.identity_relations:
                partner = target
                break
        
        if not partner:
            continue
            
        if partner.is_dead:
            continue
        
        # 2. Deduplicate (only handle A-B once)
        # Sort by ID to ensure uniqueness
        id1, id2 = sorted([str(avatar.id), str(partner.id)])
        couple_id = (id1, id2)
        
        if couple_id in processed_couples:
            continue
        processed_couples.add(couple_id)
        
        # 3. Check the time (the relation must have lasted > 12 months)
        start_time = avatar.relation_start_dates.get(partner.id, 0)
        if partner.id not in avatar.relation_start_dates:
             # Backfill the time as now, to avoid checking every frame
             avatar.relation_start_dates[partner.id] = current_time
             partner.relation_start_dates[avatar.id] = current_time
             start_time = current_time

        if current_time - start_time <= 12:
            continue
        
        # 4. Check the count limit (stop once either side reaches the limit)
        if len(avatar.children) >= max_children or len(partner.children) >= max_children:
            continue
            
        # 5. Probability roll
        if random.random() < birth_rate:
            event = _create_child_for_couple(world, avatar, partner)
            if event:
                events.append(event)

    return events

def _create_child_for_couple(world: World, parent1: Avatar, parent2: Avatar) -> Event:
    """
    Create a child for a pair of partners
    """
    # 1. Determine the paternal line (for the surname)
    # Prefer the male as father; if same-sex, pick parent1
    father = parent1 if parent1.gender == Gender.MALE else (parent2 if parent2.gender == Gender.MALE else parent1)
    
    # 2. Generate basic info
    child_gender = random.choice(list(Gender))
    
    # Get the father's surname
    father_surname = (father.name.split() or [""])[0] # Names are "Surname Given"; take the first part
    
    # Generate the name via the public API
    child_race = _resolve_child_race(parent1, parent2)
    if child_race.is_yao:
        child_name = get_random_name_for_race(child_gender, child_race)
    else:
        child_name = get_random_name_with_surname(child_gender, father_surname, sect=None)
    
    # 3. Create the object
    child = Mortal(
        id=get_avatar_id(),
        name=child_name,
        gender=child_gender,
        race=child_race,
        birth_month_stamp=world.month_stamp,
        parents=[str(parent1.id), str(parent2.id)],
        born_region_id=get_born_region_id(world, parents=[parent1, parent2], race=child_race)
    )
    
    # 4. Bind relations
    parent1.children.append(child)
    parent2.children.append(child)
    
    # 5. Register with the world's mortal manager
    world.mortal_manager.register_mortal(child)
    
    # 6. Generate the event text
    # key: "{p1} and {p2} gave birth to a {gender} named {child}."
    gender_str_key = "son" if child_gender == Gender.MALE else "daughter"
    gender_str = t(gender_str_key)
    
    event_desc = t(
        "{p1} and {p2} gave birth to a {gender} named {child}.", 
        p1=parent1.name, 
        p2=parent2.name, 
        gender=gender_str, 
        child=child.name
    )
    
    event = Event(
        world.month_stamp,
        event_desc,
        related_avatars=[parent1.id, parent2.id]
    )
    
    return event
