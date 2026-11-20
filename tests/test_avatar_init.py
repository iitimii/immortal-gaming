"""Tests for avatar creation logic in the new_avatar module."""
import pytest

from src.classes.core.orthodoxy import get_orthodoxy
from src.classes.relation.relation import Relation
from src.classes.core.sect import sects_by_id
from src.classes.official_rank import OFFICIAL_COUNTY, OFFICIAL_GRAND_COUNCILOR, OFFICIAL_NONE
from src.i18n import t
from src.sim.avatar_init import (
    INITIAL_AGE_MAX_BY_REALM,
    _assign_initial_official_status,
    _get_initial_official_chance,
    create_avatar_from_request,
    get_manual_avatar_age_limits,
    make_avatars,
    ManualAvatarAgeLimitError,
)
from src.systems.cultivation import CultivationProgress, Realm
from src.classes.goldfinger import goldfingers_by_id


def _find_goldfinger_by_key(key: str):
    for goldfinger in goldfingers_by_id.values():
        if goldfinger.key == key:
            return goldfinger
    raise AssertionError(f"Goldfinger not found: {key}")


class TestAgeLifespanInitialization:
    """Innate lifespan and immediate-death rules for new avatars."""

    def test_batch_creation_innate_lifespan_within_range(self, base_world):
        avatars = make_avatars(base_world, count=100)

        for avatar in avatars.values():
            assert 60 <= avatar.age.innate_max_lifespan <= 90

    def test_batch_creation_age_stays_within_realm_band(self, base_world):
        avatars = make_avatars(base_world, count=120)

        for avatar in avatars.values():
            realm = avatar.cultivation_progress.realm
            assert avatar.age.age <= INITIAL_AGE_MAX_BY_REALM[realm]

    def test_batch_creation_living_avatar_not_over_limit(self, base_world):
        avatars = make_avatars(base_world, count=120)

        for avatar in avatars.values():
            if avatar.is_dead:
                continue
            assert avatar.age.age < avatar.age.max_lifespan

    def test_realm_bonus_participates_in_effects_breakdown(self, base_world):
        avatars = make_avatars(base_world, count=80)
        living = [avatar for avatar in avatars.values() if not avatar.is_dead]
        assert living

        avatar = living[0]
        breakdown = dict(avatar.get_effect_breakdown())
        realm_label = t("effect_source_cultivation_realm")
        assert realm_label in breakdown
        assert "extra_max_lifespan" in breakdown[realm_label]

    def test_manual_creation_age_limits_keep_qi_refinement_young(self):
        assert get_manual_avatar_age_limits() == {
            "min": 16,
            "max_by_realm": {
                "QI_REFINEMENT": 65,
                "FOUNDATION_ESTABLISHMENT": 109,
                "CORE_FORMATION": 159,
                "NASCENT_SOUL": 459,
            },
        }

    def test_manual_qi_refinement_avatar_is_alive_at_maximum_age(self, base_world):
        avatar = create_avatar_from_request(
            base_world,
            base_world.month_stamp,
            name="Veteran",
            age=65,
            level=1,
        )

        assert avatar.age.age == 65
        assert avatar.age.max_lifespan > avatar.age.age
        assert avatar.is_dead is False

    def test_manual_qi_refinement_avatar_rejects_age_above_limit(self, base_world):
        with pytest.raises(ManualAvatarAgeLimitError):
            create_avatar_from_request(
                base_world,
                base_world.month_stamp,
                name="Overflow",
                age=66,
                level=1,
            )


class TestInitialOfficialStatus:
    """Initial official reputation rules for starting avatars."""

    def test_confucian_avatar_has_higher_initial_official_chance(self, dummy_avatar):
        confucian_sect = sects_by_id[13]
        dummy_avatar.sect = confucian_sect

        assert get_orthodoxy(confucian_sect.orthodoxy_id).id == "confucianism"
        assert _get_initial_official_chance(dummy_avatar) == pytest.approx(0.70)

        dummy_avatar.sect = None
        assert _get_initial_official_chance(dummy_avatar) == pytest.approx(0.25)

    def test_assign_initial_official_status_can_promote_by_realm_band(self, dummy_avatar, monkeypatch):
        confucian_sect = sects_by_id[13]
        dummy_avatar.sect = confucian_sect
        dummy_avatar.cultivation_progress = CultivationProgress(95)

        random_values = iter([0.20])
        randint_values = iter([1080])
        monkeypatch.setattr("src.sim.avatar_init.random.random", lambda: next(random_values))
        monkeypatch.setattr("src.sim.avatar_init.random.randint", lambda a, b: next(randint_values))

        _assign_initial_official_status(dummy_avatar)

        assert dummy_avatar.court_reputation == 1080
        assert dummy_avatar.official_rank == OFFICIAL_GRAND_COUNCILOR

    def test_assign_initial_official_status_can_leave_avatar_unranked(self, dummy_avatar, monkeypatch):
        dummy_avatar.sect = None
        dummy_avatar.cultivation_progress = CultivationProgress(20)

        monkeypatch.setattr("src.sim.avatar_init.random.random", lambda: 0.50)

        _assign_initial_official_status(dummy_avatar)

        assert dummy_avatar.court_reputation == 0
        assert dummy_avatar.official_rank == OFFICIAL_NONE

    def test_batch_creation_can_generate_initial_officials(self, base_world):
        avatars = make_avatars(base_world, count=120)

        officials = [avatar for avatar in avatars.values() if avatar.official_rank != OFFICIAL_NONE]
        assert officials
        assert any(avatar.official_rank == OFFICIAL_COUNTY for avatar in officials)
        assert all(avatar.court_reputation >= 80 for avatar in officials)


class TestInitialGoldfingerAssignment:
    """Random goldfinger assignment at game start."""

    def test_batch_creation_can_assign_goldfinger_when_probability_hits(self, base_world, monkeypatch):
        target_goldfinger = _find_goldfinger_by_key("TRANSMIGRATOR")

        monkeypatch.setattr("src.sim.avatar_init.INITIAL_GOLDFINGER_PROBABILITY", 1.0)
        monkeypatch.setattr(
            "src.sim.avatar_init.get_random_compatible_goldfinger",
            lambda avatar: target_goldfinger,
        )

        avatars = make_avatars(base_world, count=8)

        assert avatars
        assert all(avatar.goldfinger is target_goldfinger for avatar in avatars.values())

    def test_manual_avatar_creation_does_not_auto_assign_random_goldfinger(self, base_world, monkeypatch):
        monkeypatch.setattr("src.sim.avatar_init.INITIAL_GOLDFINGER_PROBABILITY", 1.0)
        monkeypatch.setattr(
            "src.sim.avatar_init.get_random_compatible_goldfinger",
            lambda avatar: _find_goldfinger_by_key("CHILD_OF_FORTUNE"),
        )

        avatar = create_avatar_from_request(
            base_world,
            base_world.month_stamp,
            name="Manually Created Avatar",
            level=10,
        )

        assert avatar.goldfinger is None

    def test_batch_creation_skips_goldfinger_when_probability_misses(self, base_world, monkeypatch):
        monkeypatch.setattr("src.sim.avatar_init.INITIAL_GOLDFINGER_PROBABILITY", 0.0)

        avatars = make_avatars(base_world, count=8)

        assert avatars
        assert all(avatar.goldfinger is None for avatar in avatars.values())


class TestInitialRelationConstraints:
    """Relation constraints during initial batch generation."""

    def test_batch_creation_parent_child_constraints(self, base_world):
        """Parent-child relations must satisfy age and level gap constraints."""
        for _ in range(10):
            avatars = make_avatars(base_world, count=80)
            for avatar in avatars.values():
                for other, relation in avatar.relations.items():
                    if relation is not Relation.IS_CHILD_OF:
                        continue
                    assert avatar.age.age - other.age.age >= 16, (
                        f"Parent {avatar.name}({avatar.age.age}) and child "
                        f"{other.name}({other.age.age}) have an invalid age gap"
                    )
                    assert avatar.cultivation_progress.level - other.cultivation_progress.level >= 10, (
                        f"Parent {avatar.name}({avatar.cultivation_progress.level}) and child "
                        f"{other.name}({other.cultivation_progress.level}) have an invalid level gap"
                    )

    def test_batch_creation_master_disciple_constraints(self, base_world):
        """Master-disciple relations must satisfy the level gap constraint."""
        sects = list(sects_by_id.values())
        for _ in range(10):
            avatars = make_avatars(base_world, count=80, existed_sects=sects)
            found_master_pair = False
            for avatar in avatars.values():
                for other, relation in avatar.relations.items():
                    if relation is not Relation.IS_DISCIPLE_OF:
                        continue
                    found_master_pair = True
                    assert avatar.cultivation_progress.level - other.cultivation_progress.level >= 20, (
                        f"Master {avatar.name}({avatar.cultivation_progress.level}) and disciple "
                        f"{other.name}({other.cultivation_progress.level}) have an invalid level gap"
                    )
            if found_master_pair:
                break
        else:
            pytest.skip("No master-disciple relation generated in this random run; skipping constraint assertions")

    def test_batch_creation_cultivation_start_not_in_future(self, base_world):
        """No initial avatar may start cultivating later than the current time."""
        avatars = make_avatars(base_world, count=120, current_month_stamp=base_world.month_stamp)
        current_month = int(base_world.month_stamp)
        for avatar in avatars.values():
            assert avatar.cultivation_start_month_stamp is not None
            assert int(avatar.cultivation_start_month_stamp) <= current_month, (
                f"Avatar {avatar.name} cultivation start time "
                f"{int(avatar.cultivation_start_month_stamp)} is later than the current time {current_month}"
            )
