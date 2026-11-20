import pytest
import asyncio
from typing import Dict

from src.classes.items.elixir import Elixir, ElixirType, ConsumedElixir, _load_elixirs
from src.classes.core.avatar import Avatar
from src.systems.cultivation import Realm
from src.classes.effect import EffectsMixin
from src.systems.time import create_month_stamp, Year, Month

# ==========================================
# Fixtures
# ==========================================

@pytest.fixture
def test_elixirs() -> Dict[str, Elixir]:
    """
    Build a set of test elixirs by hand to avoid depending on external CSV config.
    """
    # 1. Qi Refinement breakthrough elixir (regular)
    breakthrough = Elixir(
        id=1001,
        name="Test Ascension Pill",
        realm=Realm.Qi_Refinement,
        type=ElixirType.Breakthrough,
        desc="For testing",
        price=100,
        effects=[{"duration_month": 10, "extra_breakthrough_success_rate": 0.1}],
        effect_desc="Breakthrough rate +10%"
    )

    # 2. Qi Refinement lifespan elixir (unlimited duration)
    lifespan_qi = Elixir(
        id=1002,
        name="Test Longevity Pill",
        realm=Realm.Qi_Refinement,
        type=ElixirType.Lifespan,
        desc="For testing",
        price=200,
        effects=[{"extra_max_lifespan": 10}], # no duration_month means permanent
        effect_desc="Lifespan +10"
    )
    
    # 3. Foundation Establishment lifespan elixir (higher realm)
    lifespan_found = Elixir(
        id=1003,
        name="Test Foundation Longevity Pill",
        realm=Realm.Foundation_Establishment,
        type=ElixirType.Lifespan,
        desc="For testing",
        price=500,
        effects=[{"extra_max_lifespan": 20}],
        effect_desc="Lifespan +20"
    )

    # 4. Blood-burning elixir (mixed durations: attack up for 3 months, defense down for 10)
    # Note: mimics the CSV value [{"duration_month": 3, "val": 1}, {"duration_month": 10, "val": -1}]
    burn_blood = Elixir(
        id=1004,
        name="Test Blood-Burning Pill",
        realm=Realm.Qi_Refinement,
        type=ElixirType.BurnBlood,
        desc="For testing",
        price=50,
        effects=[
            {"duration_month": 3, "extra_battle_strength_points": 10},
            {"duration_month": 10, "extra_defense_points": -5}
        ],
        effect_desc="Burst"
    )

    return {
        "breakthrough": breakthrough,
        "lifespan_qi": lifespan_qi,
        "lifespan_found": lifespan_found,
        "burn_blood": burn_blood
    }

# ==========================================
# Tests
# ==========================================

class TestElixirBasic:
    """Basic loading and data structures."""
    
    def test_load_config_structure(self):
        """Loading from the real CSV works (checks structure only, not specific values)."""
        ids, names = _load_elixirs()
        assert len(ids) > 0, "Elixir data should load"
        first_elixir = list(ids.values())[0]
        assert isinstance(first_elixir, Elixir)
        assert isinstance(first_elixir.effects, (dict, list))

    def test_elixir_info(self, test_elixirs):
        """Detailed info display."""
        elixir = test_elixirs["breakthrough"]
        info = elixir.get_detailed_info()
        assert "Test Ascension Pill" in info
        assert "Qi Refinement" in info
        assert "Breakthrough" in info

class TestConsumption:
    """Consumption logic."""

    def test_consume_success(self, dummy_avatar, test_elixirs):
        """Normal consumption."""
        elixir = test_elixirs["breakthrough"]
        dummy_avatar.consume_elixir(elixir)
        
        assert len(dummy_avatar.elixirs) == 1
        record = dummy_avatar.elixirs[0]
        assert record.elixir.id == elixir.id
        assert record.consume_time == int(dummy_avatar.world.month_stamp)

    def test_consume_realm_restriction(self, dummy_avatar, test_elixirs):
        """Realm restriction: a Qi Refinement avatar cannot take a Foundation Establishment elixir."""
        # Confirm the avatar is in Qi Refinement
        assert dummy_avatar.cultivation_progress.realm == Realm.Qi_Refinement
        
        elixir = test_elixirs["lifespan_found"] # Foundation Establishment elixir
        success = dummy_avatar.consume_elixir(elixir)
        
        assert not success
        assert len(dummy_avatar.elixirs) == 0

    def test_consume_duplicate_lifespan(self, dummy_avatar, test_elixirs):
        """
        Taking a same-realm lifespan elixir again does not add more lifespan.
        """
        elixir = test_elixirs["lifespan_qi"]
        
        # 1. First dose
        base_lifespan = dummy_avatar.age.max_lifespan
        success1 = dummy_avatar.consume_elixir(elixir)
        assert success1
        
        # Check the attribute change
        new_lifespan = dummy_avatar.age.max_lifespan
        # Avatar inherits EffectsMixin; recalc_effects adds the extra_max_lifespan
        # effect, which the Age/Avatar attribute computation picks up.
        # Verify via the effect value.
        assert dummy_avatar.effects.get("extra_max_lifespan") == 10
        
        # 2. Taking it again immediately fails
        success2 = dummy_avatar.consume_elixir(elixir)
        assert not success2
        assert len(dummy_avatar.elixirs) == 1
        assert dummy_avatar.effects.get("extra_max_lifespan") == 10

        # 3. Advance a long time (lifespan elixirs are permanent, so it still cannot be taken)
        dummy_avatar.world.month_stamp += 1000
        success3 = dummy_avatar.consume_elixir(elixir)
        assert not success3
        assert len(dummy_avatar.elixirs) == 1
        
    def test_consume_duplicate_expired(self, dummy_avatar, test_elixirs):
        """An elixir can be taken again after it expires."""
        elixir = test_elixirs["breakthrough"] # lasts 10 months
        
        # 1. Take it
        dummy_avatar.consume_elixir(elixir)
        assert len(dummy_avatar.elixirs) == 1
        
        # 2. Advance time until expiry (current + 11)
        # consume_time is the month_stamp when taken
        # expire_time = consume_time + 10
        # is_completely_expired is True when current >= expire_time
        
        # Advance 9 months first (1 month left)
        dummy_avatar.world.month_stamp += 9
        # Cleanup is normally passive; here we rely on the check done at consumption
        # consume_elixir checks is_completely_expired internally
        success_fail = dummy_avatar.consume_elixir(elixir)
        assert not success_fail # not expired yet, cannot take it
        
        # Advance 2 more months (+11 total): expired
        dummy_avatar.world.month_stamp += 2
        
        # 3. Taking it again succeeds
        # Note: consume_elixir rejects only if the same elixir was taken and is still active
        # Even if the old record is still in the list (not cleaned up yet), it can be taken again once is_completely_expired is True
        success_ok = dummy_avatar.consume_elixir(elixir)
        assert success_ok
        
        # The list now holds 2 records (the old one is not cleaned up yet)
        # consume_elixir only appends; cleanup happens in process_elixir_expiration
        assert len(dummy_avatar.elixirs) == 2
        
        # One record is expired and the other is new
        expired_one = dummy_avatar.elixirs[0]
        new_one = dummy_avatar.elixirs[1]
        assert expired_one.is_completely_expired(int(dummy_avatar.world.month_stamp))
        assert not new_one.is_completely_expired(int(dummy_avatar.world.month_stamp))

class TestExpirationAndEffects:
    """Durations and effect calculation."""

    def test_mixed_duration_effects(self, dummy_avatar, test_elixirs):
        """Multi-stage effects of the blood-burning elixir."""
        # Compute baseline values first (without elixir effects)
        dummy_avatar.recalc_effects()
        base_atk = dummy_avatar.effects.get("extra_battle_strength_points", 0)
        base_def = dummy_avatar.effects.get("extra_defense_points", 0)

        elixir = test_elixirs["burn_blood"]
        # effects: duration 3 (atk+10), duration 10 (def-5)
        
        dummy_avatar.consume_elixir(elixir)
        start_time = int(dummy_avatar.world.month_stamp)
        
        # 1. Just taken (Month 0)
        # all effects active
        active = dummy_avatar.elixirs[0].get_active_effects(start_time)
        assert len(active) == 2
        
        dummy_avatar.recalc_effects()
        # Expect baseline + elixir delta
        assert dummy_avatar.effects.get("extra_battle_strength_points") == base_atk + 10
        assert dummy_avatar.effects.get("extra_defense_points") == base_def - 5

        # 2. Month 2 (Month 0 + 2 < 3)
        current = start_time + 2
        active = dummy_avatar.elixirs[0].get_active_effects(current)
        assert len(active) == 2

        # 3. Month 5 (Month 0 + 5)
        # The attack buff (3 months) is gone; the defense debuff (10 months) remains
        current = start_time + 5
        dummy_avatar.world.month_stamp = create_month_stamp(Year(2000), Month.JANUARY) + 5 # Reset timestamp just to be safe
        # update world time manually
        dummy_avatar.world.month_stamp = start_time + 5
        
        # Trigger cleanup and recalculation explicitly
        dummy_avatar.process_elixir_expiration(current) # not fully expired, so the Elixir record is kept
        dummy_avatar.recalc_effects() # but the active effects changed, so recompute attributes
        
        # Active effects
        active = dummy_avatar.elixirs[0].get_active_effects(current)
        assert len(active) == 1
        assert "extra_battle_strength_points" not in active[0]
        assert active[0]["extra_defense_points"] == -5
        
        # Attribute panel
        # Note: Avatar.recalc_effects() calls self.get_all_effects()
        # get_all_effects calls get_active_effects on each elixir
        assert dummy_avatar.effects.get("extra_battle_strength_points", 0) == base_atk
        assert dummy_avatar.effects.get("extra_defense_points") == base_def - 5

        # 4. Month 11 (Month 0 + 11)
        # everything expired
        current = start_time + 11
        dummy_avatar.world.month_stamp = current
        
        # is_completely_expired should now be True
        assert dummy_avatar.elixirs[0].is_completely_expired(current)
        
        # Trigger cleanup
        dummy_avatar.process_elixir_expiration(current)
        assert len(dummy_avatar.elixirs) == 0
        
        # Attributes restored
        dummy_avatar.recalc_effects()
        assert dummy_avatar.effects.get("extra_defense_points", 0) == base_def

    def test_infinite_duration(self, dummy_avatar, test_elixirs):
        """Unlimited duration (lifespan elixir)."""
        elixir = test_elixirs["lifespan_qi"]
        dummy_avatar.consume_elixir(elixir)
        
        # Advance 100 years
        dummy_avatar.world.month_stamp += 1200 
        current = int(dummy_avatar.world.month_stamp)
        
        assert not dummy_avatar.elixirs[0].is_completely_expired(current)
        dummy_avatar.process_elixir_expiration(current)
        assert len(dummy_avatar.elixirs) == 1
        
        # The effect is still active
        dummy_avatar.recalc_effects()
        assert dummy_avatar.effects.get("extra_max_lifespan") == 10

class TestSimulatorIntegration:
    """Simulator integration."""
    
    @pytest.mark.asyncio
    async def test_passive_update_loop(self, base_world, dummy_avatar, test_elixirs, mock_llm_managers):
        """Simulator.step() automatically cleans up expired elixirs."""
        from src.sim.simulator import Simulator
        
        # Set up
        sim = Simulator(base_world)
        # Make sure dummy_avatar is in the world's manager (base_world does not add it automatically)
        base_world.avatar_manager.avatars[dummy_avatar.id] = dummy_avatar
        
        # Build a very short elixir (lasts 1 month)
        short_elixir = Elixir(
            id=9999,
            name="Instant Pill",
            realm=Realm.Qi_Refinement,
            type=ElixirType.Breakthrough,
            desc="For testing",
            price=1,
            effects=[{"duration_month": 1, "test_val": 1}],
            effect_desc="Instant"
        )
        dummy_avatar.consume_elixir(short_elixir)
        
        # Only 2 steps are needed (month 0->1 still active, month 1->2 expired and cleaned)
        # month 0: consume. expires at 0+1=1.
        # step 1: check expiration (time=0). not expired. time becomes 1.
        # step 2: check expiration (time=1). expired! cleaned. time becomes 2.
        for _ in range(2):
            await sim.step()
            
        # Cleaned up automatically
        assert len(dummy_avatar.elixirs) == 0

