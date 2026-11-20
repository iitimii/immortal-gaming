from typing import List, Dict, TYPE_CHECKING
import asyncio
from src.classes.gathering.gathering import Gathering, register_gathering
from src.classes.event import Event
from src.classes.story_event_service import StoryEventService
from src.classes.relation.relation_delta_service import RelationDeltaService
from src.utils.config import CONFIG
from src.utils.llm.client import call_llm_with_template
from src.utils.llm.runtime_mode import is_test_mode_enabled

if TYPE_CHECKING:
    from src.classes.core.world import World
    from src.classes.core.avatar import Avatar
    from src.classes.items.item import Item

@register_gathering
class Auction(Gathering):
    """
    Auction event
    """
    
    # Class variable - LLM prompt
    STORY_PROMPT_ID = "auction_story_prompt"
    
    @classmethod
    def get_story_prompt(cls) -> str:
        """Get the story generation prompt."""
        from src.i18n import t
        return t(cls.STORY_PROMPT_ID)
    
    def is_start(self, world: "World") -> bool:
        """
        Check whether the auction starts.
        Condition: the background sold_item_count reaches the configured threshold
        """
        threshold = CONFIG.world.gathering.auction_trigger_count
        return world.circulation.sold_item_count >= threshold

    def get_related_avatars(self, world: "World") -> List[int]:
        """
        All living avatars allowed to join gatherings participate
        """
        return [
            avatar.id 
            for avatar in world.avatar_manager.get_living_avatars()
            if self._can_avatar_join(avatar)
        ]

    def get_info(self, world: "World") -> str:
        from src.i18n import t
        return t("Auction is in progress...")

    async def get_needs(self, world: "World", avatars: List["Avatar"]) -> Dict["Item", Dict["Avatar", int]]:
        """
        Get every participant's need level for the auction items.
        Return format: Dict[Item, Dict[Avatar, int]]
        """
        
        if is_test_mode_enabled():
            return {}

        # 1. Prepare auction item info
        items_info = []
        
        # Collect items from the circulation manager
        circulation = world.circulation
        all_items = []
        all_items.extend(circulation.sold_weapons)
        all_items.extend(circulation.sold_auxiliaries)
        all_items.extend(circulation.sold_elixirs)
        
        for item in all_items:
            # Assume every item has get_info or a similar method
            # Use get_detailed_info uniformly if available, otherwise str(item)
            info = getattr(item, "get_detailed_info", lambda: str(item))()
            # Add the ID so the LLM can reference it
            items_info.append(f"ID: {item.id}, Info: {info}")
            
        items_str = "\n".join(items_info)
        
        # 2. Prepare avatar info and process in batches
        batch_size = 5
        tasks = []
        
        for i in range(0, len(avatars), batch_size):
            batch_avatars = avatars[i : i + batch_size]
            
            # Build this batch's avatar_infos string
            batch_infos = {}
            for avatar in batch_avatars:
                # Use avatar.get_info(detailed=True)
                info = avatar.get_info(detailed=True)
                batch_infos[avatar.name] = str(info)
            
            # Build template params
            template_params = {
                "avatar_infos": str(batch_infos),
                "items": items_str
            }
            
            # Create concurrent tasks
            task = call_llm_with_template(
                template_path=CONFIG.paths.templates / "auction_need.txt",
                infos=template_params
            )
            tasks.append(task)
            
        # 3. Run concurrently and collect results
        results = await asyncio.gather(*tasks)
        
        # 4. Merge results
        final_needs = {}
        for result in results:
            if isinstance(result, dict):
                final_needs.update(result)
                
        # 5. Convert the structure into dict[Item, dict[Avatar, int]]
        # Build a name -> Avatar mapping
        name_to_avatar = {av.name: av for av in avatars}
        # Build an id -> Item mapping
        id_to_item = {str(item.id): item for item in all_items}
        
        item_based_needs: Dict["Item", Dict["Avatar", int]] = {}
        
        # Iterate final_needs: {avatar_name: {item_id: score}}
        for av_name, items_score_map in final_needs.items():
            avatar = name_to_avatar.get(av_name)
            if not avatar:
                continue
                
            for item_id, score in items_score_map.items():
                item = id_to_item.get(str(item_id))
                if not item:
                    continue
                    
                score_val = int(score)
                # Only record need > 1 (optional optimization; 1 means not needed at all)
                if score_val <= 1:
                    continue
                    
                if item not in item_based_needs:
                    item_based_needs[item] = {}
                item_based_needs[item][avatar] = score_val
                
        return item_based_needs

    def _calculate_bid(self, item: "Item", need_level: int, current_balance: int) -> int:
        """
        Compute a single bid, adjusted dynamically by the current balance.
        """
        from src.classes.prices import prices
        
        if need_level <= 1:
            return 0
            
        # Strategy:
        # Need 2: min(money, base_price * 0.8)  (bargain hunting)
        # Need 3: min(money, base_price * 1.5)  (slight premium)
        # Need 4: min(money, base_price * 3.0)  (high premium)
        # Need 5: money                         (all in)
        
        base_price = prices.get_price(item)
        multipliers = {
            2: 0.8,
            3: 1.5,
            4: 3.0,
        }
        
        if need_level >= 5:
            return current_balance
        
        multiplier = multipliers.get(need_level, 0.0)
        calculated_price = int(base_price * multiplier)
        
        # The final bid cannot exceed the current balance
        return min(current_balance, calculated_price)

    def resolve_auctions(
        self,
        needs: Dict["Item", Dict["Avatar", int]]
    ) -> tuple[Dict["Item", tuple["Avatar", int]], List["Item"], Dict["Item", Dict["Avatar", int]]]:
        """
        Settle the auction results.
        Returns:
            deal_results: deal results {item: (winner, price)}
            unsold_items: list of unsold items
            all_willing_prices: all bid records {item: {avatar: price}} (used for story generation)
        """
        from src.classes.prices import prices

        deal_results = {}
        unsold_items = []
        all_willing_prices = {} 
        
        # 1. Snapshot avatar funds
        all_avatars = set()
        for av_map in needs.values():
            all_avatars.update(av_map.keys())
        current_balances = {av: int(av.magic_stone) for av in all_avatars}
        
        # 2. Sort items: settle from highest to lowest value, valuable items first
        sorted_items = sorted(needs.keys(), key=lambda x: prices.get_price(x), reverse=True)
        
        for item in sorted_items:
            avatar_needs = needs[item]
            bids = {}
            
            # Compute all valid bids for this item
            for avatar, need_val in avatar_needs.items():
                balance = current_balances.get(avatar, 0)
                if balance <= 0:
                    continue
                    
                bid = self._calculate_bid(item, need_val, balance)
                if bid > 0:
                    bids[avatar] = bid
            
            if bids:
                all_willing_prices[item] = bids
            
            # Decide whether it goes unsold
            if not bids:
                unsold_items.append(item)
                continue
            
            # Decide the winner (second-price sealed-bid auction)
            sorted_bids = sorted(bids.items(), key=lambda x: x[1], reverse=True)
            winner, highest_bid = sorted_bids[0]
            
            deal_price = 0
            if len(sorted_bids) >= 2:
                second_bid = sorted_bids[1][1]
                deal_price = min(highest_bid, second_bid + 1)
            else:
                # No competition: sold at the reserve price (60% of bid)
                deal_price = max(1, int(highest_bid * 0.6))
            
            # Only valid when the deal price <= balance (in theory calculate_bid already ensures bid <= balance,
            # and since bid >= deal_price, deal_price <= balance always holds; this closes the logic loop)
            
            # Update state
            current_balances[winner] -= deal_price
            deal_results[item] = (winner, deal_price)
            
        return deal_results, unsold_items, all_willing_prices

    def _generate_auction_events(
        self,
        world: "World",
        deal_results: Dict["Item", tuple["Avatar", int]],
        willing_prices: Dict["Item", Dict["Avatar", int]]
    ) -> List[Event]:
        """
        Generate auction events (combining deal and competition info).
        """
        from src.i18n import t
        events = []
        month_stamp = world.month_stamp
        
        for item, (winner, deal_price) in deal_results.items():
            bids = willing_prices.get(item, {})
            # Check for competitors (bidders >= 2)
            if len(bids) >= 2:
                # Get the second-highest bidder
                sorted_bids = sorted(bids.items(), key=lambda x: x[1], reverse=True)
                runner_up = sorted_bids[1][0]
                
                content = t(
                    "In the auction for {item_name}, {winner_name} outbid {runner_up_name} with {price} spirit stones and won the item.",
                    item_name=item.name,
                    winner_name=winner.name,
                    runner_up_name=runner_up.name,
                    price=deal_price
                )
                related_avatars = [winner.id, runner_up.id]
            else:
                content = t(
                    "At the auction, {winner_name} acquired {item_name} for {price} spirit stones.",
                    winner_name=winner.name,
                    item_name=item.name,
                    price=deal_price
                )
                related_avatars = [winner.id]
                
            event = Event(
                month_stamp=month_stamp,
                content=content,
                related_avatars=related_avatars,
                is_major=False
            )
            if len(related_avatars) >= 2:
                runner_up_avatar = world.avatar_manager.get_avatar(related_avatars[1])
                if runner_up_avatar is not None:
                    winner_avatar = world.avatar_manager.get_avatar(related_avatars[0])
                    if winner_avatar is not None:
                        mode = RelationDeltaService.get_action_mode("gathering")
                        if mode == "llm":
                            # The gathering settlement point is synchronous; deltas are applied asynchronously at the end of execute
                            setattr(event, "_relation_delta_pair", (winner_avatar, runner_up_avatar))
            events.append(event)
            
        return events

    async def _generate_story(
        self,
        world: "World",
        deal_results: Dict["Item", tuple["Avatar", int]],
        willing_prices: Dict["Item", Dict["Avatar", int]]
    ) -> List[Event]:
        """
        Generate the story (StoryTeller).
        Summarize all the important info from this auction (deals, competition) for the LLM,
        letting the LLM pick its own angle for the story.
        """
        from src.i18n import t
        events = []
        
        # 1. Collect all relevant event text
        interaction_lines = []
        
        # Collect deal info
        for item, (winner, deal_price) in deal_results.items():
            interaction_lines.append(
                t("Deal: {winner_name} acquired {item_name} for {price} spirit stones.",
                  winner_name=winner.name, item_name=item.name, price=deal_price)
            )
            
        # Collect competition info (outbidding)
        # To avoid trivial repetition, only record fierce competition (participants >= 2)
        rivalry_avatars = set()
        for item, bids in willing_prices.items():
            if len(bids) < 2:
                continue
            sorted_bids = sorted(bids.items(), key=lambda x: x[1], reverse=True)
            winner = sorted_bids[0][0]
            runner_up = sorted_bids[1][0]
            interaction_lines.append(
                t("Competition: In the auction for {item_name}, {winner_name} outbid {runner_up_name} (bid: {bid}).",
                  item_name=item.name, winner_name=winner.name, 
                  runner_up_name=runner_up.name, bid=sorted_bids[1][1])
            )
            rivalry_avatars.add(winner)
            rivalry_avatars.add(runner_up)
            
        if not interaction_lines:
            return []
            
        interaction_result = "\n".join(interaction_lines)
        
        # 2. Collect relevant item info
        # Only collect items that were sold or contested
        related_items = set(deal_results.keys())
        for item in willing_prices:
            if len(willing_prices[item]) >= 2:
                related_items.add(item)
                
        items_info_list = []
        for item in related_items:
            info = getattr(item, "get_detailed_info", lambda: str(item))()
            items_info_list.append(
                t("Item: {item_name}, Description: {description}",
                  item_name=item.name, description=info)
            )
        items_info_str = "\n".join(items_info_list)
        
        # 3. Collect relevant avatars
        # Mainly the winners and those with notable competing behavior
        related_avatars = set()
        for winner, _ in deal_results.values():
            related_avatars.add(winner)
        related_avatars.update(rivalry_avatars)
        
        if not related_avatars:
            return []

        # 4. Call the StoryTeller
        # Prepare template params
        gathering_info = t(
            "Event Type: Mysterious Auction\nScene Setting: The auction takes place in a mysterious space, hosted by a mysterious figure with an unfathomable aura."
        )
        
        # Build details (item info + avatar info)
        # Item info
        details_list = []
        if items_info_str:
            details_list.append(t("[Auction Items Information]"))
            details_list.append(items_info_str)
            
        # Avatar info
        details_list.append(t("\n[Related Avatars Information]"))
        for av in related_avatars:
            # Get detailed info
            info = av.get_info(detailed=True)
            details_list.append(f"- {av.name}: {info}")
            
        details_text = "\n".join(details_list)
        
        story_event = await StoryEventService.maybe_create_gathering_story(
            month_stamp=world.month_stamp,
            gathering_info=gathering_info,
            events_text=interaction_result,
            details_text=details_text,
            related_avatars=list(related_avatars),
            prompt=self.get_story_prompt(),
        )
        if story_event is not None:
            events.append(story_event)
        
        return events

    async def execute(self, world: "World") -> List[Event]:
        """
        Run the auction.
        """
        events = []
        
        # 0. Check that there are items
        # sold_item_count >= threshold already guarantees items, but check again for safety
        if world.circulation.sold_item_count == 0:
            return []
            
        avatars = [world.avatar_manager.get_avatar(aid) for aid in self.get_related_avatars(world)]
        # Filter out None
        avatars = [a for a in avatars if a]
        
        if not avatars:
            return []

        # 1. Compute needs
        needs = await self.get_needs(world, avatars)
        
        # 2. Settle the auction (dynamic bids, handling asset pass-through)
        deal_results, unsold_items, willing_prices = self.resolve_auctions(needs)
        
        # 3. Execute trades (deduct money, give items, remove from circulation)
        from src.classes.items.weapon import Weapon
        from src.classes.items.auxiliary import Auxiliary
        from src.classes.items.elixir import Elixir
        from src.classes.material import Material
        from src.classes.prices import prices
        
        # Process sold items
        for item, (winner, price) in deal_results.items():
            # Deduct money
            winner.magic_stone -= price
            
            # Remove from circulation (remove first, to avoid confusion with add logic when swapping equipment)
            world.circulation.remove_item(item)
            
            # Give the item
            if isinstance(item, (Weapon, Auxiliary)):
                # Equip and handle the old equipment
                # Special logic: old equipment swapped out at an auction is destroyed (recycled at a discount but not returned to the circulation pool) to prevent unbounded item growth
                
                if isinstance(item, Weapon):
                    old_equip = winner.weapon
                    if old_equip:
                        # Compute the recycle price
                        refund = prices.get_selling_price(old_equip, winner)
                        winner.magic_stone += refund
                    # Swap equipment
                    winner.change_weapon(item)
                    
                elif isinstance(item, Auxiliary):
                    old_equip = winner.auxiliary
                    if old_equip:
                        refund = prices.get_selling_price(old_equip, winner)
                        winner.magic_stone += refund
                    # Swap equipment
                    winner.change_auxiliary(item)
                
            elif isinstance(item, Elixir):
                # Elixirs are consumed directly
                winner.consume_elixir(item)
                
            elif isinstance(item, Material):
                # Materials go into the inventory
                winner.add_material(item)
        
        # Handle unsold items: destroy directly (remove from the circulation pool)
        for item in unsold_items:
            world.circulation.remove_item(item)
            
        # 5. Generate base events (combining deal and competition info)
        auction_events = self._generate_auction_events(world, deal_results, willing_prices)
        events.extend(auction_events)
        for event in auction_events:
            pair = getattr(event, "_relation_delta_pair", None)
            if pair is None:
                continue
            winner_avatar, runner_up_avatar = pair
            a_to_b, b_to_a = await RelationDeltaService.resolve_event_text_delta(
                action_key="gathering",
                avatar_a=winner_avatar,
                avatar_b=runner_up_avatar,
                event_text=event.content,
            )
            RelationDeltaService.apply_bidirectional_delta(winner_avatar, runner_up_avatar, a_to_b, b_to_a)

        # 6. Generate the story (StoryTeller)
        story_events = await self._generate_story(world, deal_results, willing_prices)
        events.extend(story_events)
        
        return events
