import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from src.classes.gathering.auction import Auction
from src.classes.items.item import Item
from src.classes.items.weapon import Weapon
from src.classes.items.auxiliary import Auxiliary
from src.classes.prices import prices
from src.utils.config import CONFIG

# Monkeypatch removed as Weapon/Auxiliary now have __hash__ implemented

@pytest.mark.asyncio
async def test_auction_is_start(base_world, mock_item_data):
    auction = Auction()
    weapon = mock_item_data["obj_weapon"]
    
    # Initial state: sold_item_count is 0
    # Clear circulation
    base_world.circulation.sold_weapons = []
    base_world.circulation.sold_auxiliaries = []
    base_world.circulation.sold_elixirs = []
    
    # Set the threshold
    CONFIG.world.gathering.auction_trigger_count = 5
    
    assert auction.is_start(base_world) is False
    
    # Add items until the threshold is reached
    for _ in range(5):
        base_world.circulation.add_weapon(weapon)
        
    assert auction.is_start(base_world) is True

def test_calculate_bid(dummy_avatar, mock_item_data):
    auction = Auction()
    item = mock_item_data["obj_weapon"]
    base_price = prices.get_price(item)
    
    # Case 1: low need (<=1) -> bid 0
    assert auction._calculate_bid(item, 1, 1000) == 0
    
    # Case 2: need 2 (bargain hunting, 0.8)
    expected_price = int(base_price * 0.8)
    assert auction._calculate_bid(item, 2, 100000) == expected_price
    
    # Case 3: insufficient balance -> bid = balance
    avatar_money = 10
    bid = auction._calculate_bid(item, 3, avatar_money) # need 3 is 1.5x, definitely > 10
    assert bid == avatar_money
    
    # Case 4: need 5 (all-in) -> bid = balance
    assert auction._calculate_bid(item, 5, 5000) == 5000

def test_resolve_auctions_basic(dummy_avatar, mock_item_data):
    """Test basic bid settlement logic (single item)."""
    auction = Auction()
    item = mock_item_data["obj_weapon"]
    
    avatar1 = dummy_avatar
    avatar1.magic_stone = 1000
    avatar1.name = "A1"
    
    # Create a second avatar
    avatar2 = MagicMock()
    avatar2.magic_stone = 1000
    avatar2.name = "A2"
    avatar2.__hash__ = MagicMock(return_value=123) # Make it hashable for dict keys
    
    # Mock needs dict
    needs = {
        item: {
            avatar1: 4, # High need
            avatar2: 2  # Low need
        }
    }
    
    # Mock prices
    with patch("src.classes.prices.prices.get_price", return_value=100):
        deal_results, unsold, willing = auction.resolve_auctions(needs)
        
    # Verify results
    assert item in deal_results
    winner, price = deal_results[item]
    
    # A1 bid: 100 * 3.0 = 300
    # A2 bid: 100 * 0.8 = 80
    # Final price should be the second-highest bid (80) + 1 = 81
    assert winner == avatar1
    assert price == 81
    assert not unsold

def test_resolve_auctions_asset_protection(dummy_avatar, mock_item_data):
    """Test overspend protection: one avatar bidding on multiple items."""
    auction = Auction()
    item1 = mock_item_data["obj_weapon"] # expensive
    item2 = mock_item_data["obj_material"] # cheap
    
    avatar = dummy_avatar
    avatar.magic_stone = 100  # only 100 in total
    
    needs = {
        item1: {avatar: 5}, # all-in on item1
        item2: {avatar: 5}  # all-in on item2
    }
    
    # Mock prices: item1=80, item2=50
    # item1 settles first (higher value); all-in (need=5) bids 100.
    # With a single bidder, final price = max(1, 100 * 0.6) = 60.
    # Remaining balance = 100 - 60 = 40.
    # When item2 settles the balance is only 40, so despite need=5 the bid is capped at 40.
    # item2 final price = max(1, 40 * 0.6) = 24.
    
    def get_price_side_effect(item):
        if item == item1: return 80
        return 50
        
    with patch("src.classes.prices.prices.get_price", side_effect=get_price_side_effect):
        deal_results, unsold, willing = auction.resolve_auctions(needs)
    
    # Verify item1
    assert item1 in deal_results
    winner1, price1 = deal_results[item1]
    assert winner1 == avatar
    assert price1 == 60 # 100 * 0.6
    
    # Verify item2
    assert item2 in deal_results
    winner2, price2 = deal_results[item2]
    assert winner2 == avatar
    # Balance is now 40, bid 40, final price 40 * 0.6 = 24
    assert price2 == 24
    
    # Total spend 84 <= 100: protection works
    assert price1 + price2 <= 100

def test_resolve_auctions_unsold(mock_item_data):
    """Test unsold (passed-in) lots."""
    auction = Auction()
    item = mock_item_data["obj_weapon"]
    
    # Empty or uniformly low needs produce no bids
    needs = {
        item: {}
    }
    
    with patch("src.classes.prices.prices.get_price", return_value=100):
        deal_results, unsold, willing = auction.resolve_auctions(needs)
        
    assert item not in deal_results
    assert item in unsold

@pytest.mark.asyncio
async def test_execute_flow(base_world, dummy_avatar, mock_item_data):
    """Test the full execute flow, including item trades and destruction."""
    auction = Auction()
    item_sold = mock_item_data["obj_weapon"]
    item_unsold = mock_item_data["obj_auxiliary"] # use an Auxiliary instead of a Material
    
    # Set up the environment
    # Add items to circulation to test removal logic
    base_world.circulation.sold_weapons = [item_sold]
    base_world.circulation.sold_auxiliaries = [item_unsold]
    
    # Set up the avatar
    dummy_avatar.magic_stone = 1000
    dummy_avatar.weapon = None # make sure there is no weapon
    dummy_avatar.auxiliary = None 
    
    # Make sure the avatar is in avatar_manager
    base_world.avatar_manager.avatars[dummy_avatar.id] = dummy_avatar
    
    # Mock methods
    # 1. get_related_avatars
    auction.get_related_avatars = MagicMock(return_value=[dummy_avatar.id])
    
    # 2. get_needs (async) -> item_sold gets a buyer, item_unsold does not
    async def mock_get_needs(*args, **kwargs):
        return {
            item_sold: {dummy_avatar: 4}, # High need
            item_unsold: {dummy_avatar: 1} # No need
        }
    auction.get_needs = mock_get_needs
    
    # 3. Mock StoryTeller to avoid LLM
    with patch("src.classes.story_teller.StoryTeller.tell_gathering_story", new_callable=AsyncMock) as mock_story:
        mock_story.return_value = "Auction story..."
        
        # 4. Mock prices
        with patch("src.classes.prices.prices.get_price", return_value=100):
            events = await auction.execute(base_world)
            
    # Verify results
    
    # 1. Where the items went
    # item_sold should be equipped by dummy_avatar
    assert dummy_avatar.weapon == item_sold
    # item_sold should no longer be in circulation
    assert item_sold not in base_world.circulation.sold_weapons
    
    # item_unsold should be destroyed (not in circulation, nor in the avatar's inventory/equipment)
    assert item_unsold not in base_world.circulation.sold_auxiliaries
    assert dummy_avatar.auxiliary != item_unsold
    
    # 2. Funds deducted
    # Base price 100, Need 4 (3.0x) -> Bid 300
    # Single bidder -> Deal 300 * 0.6 = 180
    # Balance 1000 - 180 = 820
    assert dummy_avatar.magic_stone == 820
    
    # 3. Events generated
    assert len(events) > 0
    # Should include the story event
    assert any(e.content == "Auction story..." for e in events)

def test_items_are_hashable():
    """Test that item classes are hashable (usable as dict keys)."""
    from src.classes.items.weapon import Weapon
    from src.classes.weapon_type import WeaponType
    from src.classes.items.auxiliary import Auxiliary
    from src.classes.items.elixir import Elixir, ElixirType
    from src.systems.cultivation import Realm

    # Weapon
    w = Weapon(
        id=1, 
        name="TestSword", 
        weapon_type=WeaponType.SWORD, 
        realm=Realm.Qi_Refinement, 
        desc="Test",
        special_data={"a": 1} # mutable field
    )
    s = set()
    s.add(w)
    assert w in s
    d = {w: 1}
    assert d[w] == 1

    # Auxiliary
    a = Auxiliary(
        id=2, 
        name="TestAux", 
        realm=Realm.Qi_Refinement, 
        desc="Test",
        special_data={"b": 2} # mutable field
    )
    s = set()
    s.add(a)
    assert a in s
    
    # Elixir
    e = Elixir(
        id=3,
        name="TestElixir",
        realm=Realm.Qi_Refinement,
        type=ElixirType.Heal,
        desc="Test",
        price=100
    )
    s = set()
    s.add(e)
    assert e in s

def test_resolve_auctions_tie_breaking(dummy_avatar, mock_item_data):
    """Test tie-breaking when bids are equal (stability)."""
    auction = Auction()
    item = mock_item_data["obj_weapon"]
    
    # Two avatars with equal need and ample funds -> bids should be equal
    avatar1 = dummy_avatar
    avatar1.magic_stone = 1000
    avatar1.name = "A1"
    
    avatar2 = MagicMock()
    avatar2.magic_stone = 1000
    avatar2.name = "A2"
    avatar2.__hash__ = MagicMock(return_value=12345) 
    
    # Build the needs dict manually to control key order
    # Case 1: A1 first
    needs1 = {
        item: {avatar1: 5, avatar2: 5}
    }
    
    with patch("src.classes.prices.prices.get_price", return_value=100):
        deal_results1, _, _ = auction.resolve_auctions(needs1)
        
    winner1, _ = deal_results1[item]
    # With a stable sort and equal bids, order is preserved and A1 wins
    assert winner1 == avatar1
    
    # Case 2: A2 first
    needs2 = {
        item: {avatar2: 5, avatar1: 5}
    }
    with patch("src.classes.prices.prices.get_price", return_value=100):
        deal_results2, _, _ = auction.resolve_auctions(needs2)
    
    winner2, _ = deal_results2[item]
    # A2 should win
    assert winner2 == avatar2

def test_resolve_auctions_no_refund_consideration(dummy_avatar, mock_item_data):
    """Test that settlement ignores refunds from later equipment sales (prevents overdraft)."""
    auction = Auction()
    item1 = mock_item_data["obj_weapon"] # expensive, settles first
    item2 = mock_item_data["obj_elixir"] # cheap, settles later
    
    avatar = dummy_avatar
    avatar.magic_stone = 100 
    
    # Suppose the avatar has equipment that would sell for 50
    old_weapon = MagicMock()
    avatar.weapon = old_weapon
    # but resolve_auctions only looks at the snapshot, not equipment refunds
    
    needs = {
        item1: {avatar: 5}, # all-in on item1, cost 100
        item2: {avatar: 5}  # all-in on item2
    }
    
    # Mock prices: item1=80, item2=50
    # item1 price 80, need 5 -> bid 100 (balance). Deal: 100*0.6 = 60.
    # item2 price 50. Remaining balance 100-60=40.
    # need 5 -> bid 40 (balance). Deal: 40*0.6 = 24.
    # If refund (50) was considered, balance would be 40+50=90.
    # Bid 90 -> Deal 54.
    
    def get_price_side_effect(item):
        if item == item1: return 80
        return 50
        
    with patch("src.classes.prices.prices.get_price", side_effect=get_price_side_effect):
        deal_results, _, _ = auction.resolve_auctions(needs)
        
    # item1 should sell for 60 (100 * 0.6)
    assert deal_results[item1][0] == avatar
    assert deal_results[item1][1] == 60
    
    # item2 should sell for 24 (40 * 0.6)
    # proving the 40 balance was used rather than 90 (which would include the refund)
    assert item2 in deal_results
    assert deal_results[item2][1] == 24
    
    # Total spend 84 <= 100
    assert deal_results[item1][1] + deal_results[item2][1] <= 100

@pytest.mark.asyncio
async def test_execute_item_types(base_world, dummy_avatar, mock_item_data):
    """Test execute logic for a different item type (Elixir)."""
    auction = Auction()
    elixir = mock_item_data["obj_elixir"]
    
    dummy_avatar.magic_stone = 1000
    base_world.circulation.sold_elixirs = [elixir]
    
    # Register avatar
    base_world.avatar_manager.avatars[dummy_avatar.id] = dummy_avatar
    
    # Mock resolve_auctions
    auction.resolve_auctions = MagicMock(return_value=(
        {elixir: (dummy_avatar, 100)}, 
        [], 
        {}
    ))
    
    # Mock dependencies
    auction.get_related_avatars = MagicMock(return_value=[dummy_avatar.id])
    auction.get_needs = AsyncMock(return_value={}) # ignored by mocked resolve
    auction._generate_deal_events = MagicMock(return_value=[])
    auction._generate_rivalry_events = MagicMock(return_value=[])
    auction._generate_story = AsyncMock(return_value=[])
    
    # Mock circulation remove
    base_world.circulation.remove_item = MagicMock()
    
    # Mock consume_elixir
    dummy_avatar.consume_elixir = MagicMock()
    
    # Ensure items are "in" circulation logic (count > 0)
    # Circulation.sold_item_count is a property, depends on lists.
    # We set sold_elixirs above, so it should be > 0.
    
    await auction.execute(base_world)
    
    # Verify consume_elixir called
    dummy_avatar.consume_elixir.assert_called_once_with(elixir)
    
    # Verify remove_item called
    base_world.circulation.remove_item.assert_called_once_with(elixir)

@pytest.mark.asyncio
async def test_get_needs_parsing(base_world, dummy_avatar, mock_item_data):
    """Test parsing of LLM results in get_needs."""
    auction = Auction()
    item = mock_item_data["obj_weapon"]
    # Mock circulation
    base_world.circulation.sold_weapons = [item]
    
    # Mock LLM response
    mock_response = {
        dummy_avatar.name: {
            str(item.id): 5  # High need
        }
    }
    
    with patch("src.classes.gathering.auction.call_llm_with_template", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_response
        
        needs = await auction.get_needs(base_world, [dummy_avatar])
        
    assert item in needs
    assert needs[item][dummy_avatar] == 5
    
    # Test filtering of low needs (<=1)
    mock_response_low = {
        dummy_avatar.name: {
            str(item.id): 1 
        }
    }
    with patch("src.classes.gathering.auction.call_llm_with_template", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = mock_response_low
        needs = await auction.get_needs(base_world, [dummy_avatar])
        
    # Should be empty because score 1 is filtered
    assert item not in needs or not needs.get(item)
