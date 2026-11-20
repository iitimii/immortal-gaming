from typing import List, Dict, Optional, Any, TYPE_CHECKING
import random
import asyncio
from dataclasses import dataclass

from src.classes.gathering.gathering import Gathering, register_gathering
from src.classes.event import Event
if TYPE_CHECKING:
    from src.classes.core.world import World
    from src.classes.core.avatar import Avatar

from src.classes.items.item import Item
from src.utils.df import game_configs, get_str, get_float, get_int
from src.systems.cultivation import Realm, REALM_ORDER, REALM_RANK
from src.classes.death_reason import DeathReason, DeathType
from src.classes.death import handle_death
from src.classes.items.weapon import get_random_weapon_by_realm
from src.classes.items.auxiliary import get_random_auxiliary_by_realm
from src.classes.technique import get_random_technique_for_avatar
from src.classes.story_event_service import StoryEventService
from src.classes.relation.relation_delta_service import RelationDeltaService
from src.i18n import t
from src.run.log import get_logger

logger = get_logger().logger

@dataclass
class DomainConfig:
    id: str
    name: str
    desc: str
    required_realm: Realm
    danger_prob: float
    hp_loss_percent: float
    drop_prob: float
    cd_years: int
    open_prob: float

@register_gathering
class HiddenDomain(Gathering):
    """
    Hidden Domain system
    Opens periodically; only cultivators of the matching realm may enter and explore, facing danger or gaining opportunities.
    """
    
    # Year each hidden domain last opened {domain_id: last_open_year}
    _domain_states: Dict[str, int] = {}
    
    # Temporary storage of domains opened this round
    _active_domains: List[DomainConfig] = []
    
    # LLM Prompt ID
    STORY_PROMPT_ID = "hidden_domain_story_prompt"

    @classmethod
    def get_story_prompt(cls) -> str:
        return t(cls.STORY_PROMPT_ID)

    def _load_configs(self) -> List[DomainConfig]:
        """Load hidden domain config from the config table."""
        configs = []
        df = game_configs.get("hidden_domain")
        if df is None:
            return []
        
        for row in df:
            try:
                # Required fields
                conf = DomainConfig(
                    id=get_str(row, "id"),
                    name=get_str(row, "name"),
                    desc=get_str(row, "desc"),
                    required_realm=Realm.from_str(get_str(row, "required_realm")),
                    danger_prob=get_float(row, "danger_prob"),
                    hp_loss_percent=get_float(row, "hp_loss_percent"),
                    drop_prob=get_float(row, "drop_prob"),
                    cd_years=get_int(row, "cd_years"),
                    open_prob=get_float(row, "open_prob"),
                )
                configs.append(conf)
            except Exception as e:
                logger.error(f"Failed to load hidden domain config: {e}")
                continue
        return configs

    def is_start(self, world: "World") -> bool:
        """
        Determine whether any hidden domain opens.
        """
        self._active_domains = []
        current_year = world.month_stamp.get_year()
        configs = self._load_configs()
        
        for conf in configs:
            last_open = self._domain_states.get(conf.id, -999)
            
            # Only roll the probability once the CD is over
            if current_year - last_open >= conf.cd_years:
                if random.random() < conf.open_prob:
                    self._active_domains.append(conf)
                    # Update state immediately to avoid inconsistency if called multiple times in one step (though execute is the formal run)
                    # GatheringManager runs is_start -> execute in order, so updating here is fine
                    # If execute failures need rollback, move the update into execute. Kept here for simplicity.
                    self._domain_states[conf.id] = current_year
                    
        return len(self._active_domains) > 0

    def get_related_avatars(self, world: "World") -> List[int]:
        """
        Get all potential participants (all living avatars; concrete filtering by domain conditions happens in execute)
        """
        return [av.id for av in world.avatar_manager.get_living_avatars() if self._can_avatar_join(av)]

    def get_info(self, world: "World") -> str:
        details = []
        for conf in self._active_domains:
            detail = t("Hidden Domain {name} opened! Entry restricted to {realm} only.", 
                       name=conf.name, 
                       realm=str(conf.required_realm))
            details.append(detail)
        return t("Hidden Domains opened: {names}", names="\n".join(details))

    def _get_next_realm(self, realm: Realm) -> Optional[Realm]:
        """Get the next major realm."""
        current_idx = REALM_RANK.get(realm)
        if current_idx is not None and current_idx + 1 < len(REALM_ORDER):
            return REALM_ORDER[current_idx + 1]
        return None

    def _generate_loot(self, avatar: "Avatar", next_realm: Realm) -> Optional[Item]:
        """Generate a drop: prefer items one tier higher."""
        # Drop type weights: weapon (40%), armor (40%), technique (20%)
        roll = random.random()
        
        loot = None
        if roll < 0.4:
            # Weapon
            loot = get_random_weapon_by_realm(next_realm)
        elif roll < 0.8:
            # Armor
            loot = get_random_auxiliary_by_realm(next_realm)
        else:
            # Technique: try to get a higher-grade technique
            # get_random_technique_for_avatar matches by spiritual root, but here we want a bit of "opportunity"
            # Reuse that function, though it may return the same grade. To reflect "opportunity" we could retry and take the best, or just give it
            # Simply call the existing interface here
            loot = get_random_technique_for_avatar(avatar)
            
        return loot

    async def execute(self, world: "World") -> List[Event]:
        events = []
        
        for domain in self._active_domains:
            domain_events = await self._process_single_domain(world, domain)
            events.extend(domain_events)
            
        return events

    async def _process_single_domain(self, world: "World", domain: DomainConfig) -> List[Event]:
        """Handle the logic for a single hidden domain."""
        events = []
        month_stamp = world.month_stamp
        
        # 1. Filter avatars entering the domain
        entrants: List["Avatar"] = []
        for av in world.avatar_manager.get_living_avatars():
            if not self._can_avatar_join(av):
                continue
            # Realm check: only the matching realm may enter
            if av.cultivation_progress.realm == domain.required_realm:
                entrants.append(av)

        # Add the opening event
        entrants_names = [av.name for av in entrants]
        if entrants_names:
            entrants_str = ", ".join(entrants_names)
            open_event_content = t("Hidden Domain {name} opened! Entry restricted to {realm} only. Entrants: {entrants}", 
                                   name=domain.name, 
                                   realm=str(domain.required_realm),
                                   entrants=entrants_str)
        else:
            open_event_content = t("Hidden Domain {name} opened! Entry restricted to {realm} only. No one entered.", 
                                   name=domain.name, 
                                   realm=str(domain.required_realm))
        events.append(Event(month_stamp, open_event_content))
                
        if not entrants:
            return events

        # Record this domain's event texts and related avatars
        event_texts: List[str] = [open_event_content]
        related_avatars_set: set["Avatar"] = set()
        empty_handed_avatars: List["Avatar"] = []
        
        # 2. Iterate over avatars
        for av in entrants:
            # --- Effect settlement ---
            extra_drop = float(av.effects.get("extra_hidden_domain_drop_prob", 0.0))
            extra_danger = float(av.effects.get("extra_hidden_domain_danger_prob", 0.0))

            drop_prob = domain.drop_prob + extra_drop
            danger_prob = domain.danger_prob + extra_danger
            
            # Keep probabilities sane
            danger_prob = max(0.0, danger_prob)
                
            # --- Danger check ---
            triggered_event = False
            
            if random.random() < danger_prob:
                triggered_event = True
                loss_percent = domain.hp_loss_percent
                damage = int(av.hp.max * loss_percent)
                av.hp.cur -= damage
                
                if av.hp.cur <= 0:
                    # Death settlement
                    reason = DeathReason(DeathType.HIDDEN_DOMAIN)
                    handle_death(world, av, reason)
                    
                    event_content = t("{name} perished in the hidden domain {domain}.", name=av.name, domain=domain.name)
                    event = Event(
                        month_stamp,
                        event_content,
                        related_avatars=[av.id],
                        is_major=True,
                        event_type="death",
                        render_params={"subject_name": av.name},
                    )
                    events.append(event)
                    
                    event_texts.append(event_content)
                    related_avatars_set.add(av)
                    continue # The dead can't take rewards
            
            # --- Opportunity check ---
            if random.random() < drop_prob:
                triggered_event = True
                # Get the reward tier (one higher)
                target_realm = self._get_next_realm(av.cultivation_progress.realm)
                # If already at the top tier, keep the current tier
                if not target_realm:
                    target_realm = av.cultivation_progress.realm
                    
                loot = self._generate_loot(av, target_realm)
                
                if loot:
                    # Grant the reward
                    from src.classes.items.weapon import Weapon
                    from src.classes.items.auxiliary import Auxiliary
                    from src.classes.technique import Technique
                    from src.classes.prices import prices
                    
                    loot_name = loot.name
                    
                    if isinstance(loot, Weapon):
                        old = av.weapon
                        av.change_weapon(loot)
                        if old: # Recycle the old item
                            av.magic_stone += prices.get_selling_price(old, av)
                            
                    elif isinstance(loot, Auxiliary):
                        old = av.auxiliary
                        av.change_auxiliary(loot)
                        if old:
                            av.magic_stone += prices.get_selling_price(old, av)
                            
                    elif isinstance(loot, Technique):
                        # Only replace if better than the current technique, or if there's none?
                        # Or put it in the inventory (if any)? Avatar has no general inventory for this; usually learned directly
                        # Simplified: learn it directly
                        av.technique = loot
                    
                    # Record the event
                    event_content = t("{name} found a treasure {loot} in {domain}!", name=av.name, loot=loot_name, domain=domain.name)
                    event = Event(
                        month_stamp,
                        event_content,
                        related_avatars=[av.id]
                    )
                    events.append(event)
                    
                    event_texts.append(event_content)
                    related_avatars_set.add(av)

            if not triggered_event:
                # Neither died nor got anything: came back empty-handed
                empty_handed_avatars.append(av)
        
        # Handle those who came back empty-handed
        if empty_handed_avatars:
            empty_names = ", ".join([av.name for av in empty_handed_avatars])
            empty_event_content = t("{names} returned from {domain} empty-handed.", names=empty_names, domain=domain.name)
            
            # Add as one aggregated event (avoid spamming)
            # Or only add to event_texts for the story, without a standalone Event?
            # Per the requirement "show everyone's names + the empty-handed text", it should also be a log entry
            events.append(Event(
                month_stamp,
                empty_event_content,
                related_avatars=[av.id for av in empty_handed_avatars]
            ))
            event_texts.append(empty_event_content)
            # Also add them to related_avatars_set so the story teller knows they took part
            related_avatars_set.update(empty_handed_avatars)


        # 3. Generate the story (StoryTeller)
        # Only generate a story when something noteworthy happened (a death, or someone got a treasure), to avoid spamming
        if event_texts:
            story_event = await self._generate_story(world, domain, event_texts, list(related_avatars_set))
            if story_event:
                events.append(story_event)

        await self._apply_relation_deltas(entrants, event_texts)
                
        return events

    async def _apply_relation_deltas(self, entrants: List["Avatar"], event_texts: List[str]) -> None:
        if len(entrants) < 2 or not event_texts:
            return

        shuffled_entrants = list(entrants)
        random.shuffle(shuffled_entrants)
        shared_event_text = "\n".join(event_texts[:4])

        for idx in range(0, len(shuffled_entrants) - 1, 2):
            avatar_a = shuffled_entrants[idx]
            avatar_b = shuffled_entrants[idx + 1]
            a_to_b, b_to_a = await RelationDeltaService.resolve_event_text_delta(
                action_key="gathering",
                avatar_a=avatar_a,
                avatar_b=avatar_b,
                event_text=shared_event_text,
            )
            RelationDeltaService.apply_bidirectional_delta(avatar_a, avatar_b, a_to_b, b_to_a)

    async def _generate_story(
        self, 
        world: "World", 
        domain: DomainConfig, 
        event_texts: List[str], 
        related_avatars: List["Avatar"]
    ) -> Optional[Event]:
        """Call the LLM to generate the hidden domain exploration story."""
        
        if not related_avatars:
            return None
            
        # 1. Scene description
        gathering_info = t(
            "Event: Hidden Domain Opening\nName: {name}\nDescription: {desc}",
            name=domain.name, desc=domain.desc
        )
        
        # 2. Event list
        events_str = "\n".join(event_texts)
        
        # 3. Avatar info (optional, adds story detail)
        details_list = []
        details_list.append(t("\n[Related Avatars Information]"))
        for av in related_avatars:
            info = av.get_info(detailed=True)
            details_list.append(f"- {av.name}: {info}")
        details_text = "\n".join(details_list)

        return await StoryEventService.maybe_create_gathering_story(
            month_stamp=world.month_stamp,
            gathering_info=gathering_info,
            events_text=events_str,
            details_text=details_text,
            related_avatars=related_avatars,
            prompt=self.get_story_prompt(),
        )
