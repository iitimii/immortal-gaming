from fastapi.testclient import TestClient

from src.classes.age import Age
from src.classes.alignment import Alignment
from src.classes.core.avatar import Avatar, Gender
from src.classes.core.dynasty import Dynasty, Emperor
from src.classes.language import language_manager
from src.classes.official_rank import OFFICIAL_COMMANDERY, OFFICIAL_COUNTY, OFFICIAL_NONE, OFFICIAL_PROVINCE
from src.classes.root import Root
from src.server import main
from src.systems.cultivation import Realm
from src.systems.time import Month, Year, create_month_stamp
from src.utils.id_generator import get_avatar_id


def _make_official(base_world, name: str, rank_key: str, reputation: int, realm: Realm) -> Avatar:
    avatar = Avatar(
        world=base_world,
        name=name,
        id=get_avatar_id(),
        birth_month_stamp=create_month_stamp(Year(2000), Month.JANUARY),
        age=Age(20, realm, innate_max_lifespan=80),
        gender=Gender.MALE,
        pos_x=0,
        pos_y=0,
        root=Root.GOLD,
        personas=[],
        alignment=Alignment.RIGHTEOUS,
    )
    avatar.personas = []
    avatar.technique = None
    avatar.weapon = None
    avatar.auxiliary = None
    avatar.official_rank = rank_key
    avatar.court_reputation = reputation
    avatar.recalc_effects()
    base_world.avatar_manager.register_avatar(avatar)
    return avatar


def test_get_dynasty_overview_empty_when_world_missing():
    original_instance = main.game_instance.copy()
    try:
        main.game_instance["world"] = None
        client = TestClient(main.app)
        resp = client.get("/api/v1/query/dynasty/overview")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == ""
        assert data["royal_surname"] == ""
        assert data["style_tag"] == ""
        assert data["official_preference_label"] == ""
        assert data["is_low_magic"] is True
    finally:
        main.game_instance.update(original_instance)


def test_get_dynasty_overview_returns_world_dynasty(base_world):
    original_instance = main.game_instance.copy()
    try:
        base_world.dynasty = Dynasty(
            id=2,
            name="Jin",
            desc="Great clans stand in solemn ranks; the gentry delight in lofty discourse, and court and countryside prize ritual and reputation.",
            royal_surname="Sima",
            effect_desc="",
            effects={},
            style_tag="dynasty_style_pure_discourse_and_orthodoxy",
            official_preference_type="orthodoxy",
            official_preference_value="confucianism",
            current_emperor=Emperor(
                surname="Sima",
                given_name="Chengan",
                birth_month_stamp=int(base_world.month_stamp) - 34 * 12,
                max_age=80,
            ),
        )
        main.game_instance["world"] = base_world
        main.game_instance["sim"] = None

        client = TestClient(main.app)
        resp = client.get("/api/v1/query/dynasty/overview")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "Jin"
        assert data["title"] == "Jin Dynasty"
        assert data["royal_surname"] == "Sima"
        assert data["royal_house_name"] == "House Sima"
        assert data["desc"] == "Great clans stand in solemn ranks; the gentry delight in lofty discourse, and court and countryside prize ritual and reputation."
        assert data["effect_desc"] == "Governance Reputation Gain +35.0%"
        assert data["style_tag"] == "Pure Discourse and Orthodoxy"
        assert data["official_preference_label"] == "Prefers Confucian cultivators"
        assert data["is_low_magic"] is True
        assert data["current_emperor"]["name"] == "Sima Chengan"
        assert data["current_emperor"]["age"] == 34
        assert data["current_emperor"]["max_age"] == 80
        assert data["current_emperor"]["is_mortal"] is True
    finally:
        main.game_instance.update(original_instance)


def test_get_dynasty_detail_empty_when_world_missing():
    original_instance = main.game_instance.copy()
    try:
        main.game_instance["world"] = None
        client = TestClient(main.app)
        resp = client.get("/api/v1/query/dynasty/detail")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["overview"]["name"] == ""
        assert data["summary"]["official_count"] == 0
        assert data["summary"]["top_official_rank_name"] == ""
        assert data["officials"] == []
    finally:
        main.game_instance.update(original_instance)


def test_get_dynasty_detail_returns_sorted_officials(base_world):
    original_instance = main.game_instance.copy()
    try:
        base_world.dynasty = Dynasty(
            id=10,
            name="Han",
            desc="Its power is not flaunted, but it values practical affairs and grassroots governance.",
            royal_surname="Liu",
            effect_desc="",
            effects={},
            style_tag="dynasty_style_pragmatic_conservatism",
            official_preference_type="persona_key",
            official_preference_value="ORTHODOX_GENTLEMAN",
            current_emperor=Emperor(
                surname="Liu",
                given_name="Chengtian",
                birth_month_stamp=int(base_world.month_stamp) - 30 * 12,
                max_age=78,
            ),
        )

        _make_official(base_world, "Official B", OFFICIAL_COUNTY, 180, Realm.Foundation_Establishment)
        _make_official(base_world, "Official A", OFFICIAL_PROVINCE, 260, Realm.Core_Formation)
        _make_official(base_world, "Official C", OFFICIAL_COMMANDERY, 250, Realm.Nascent_Soul)
        _make_official(base_world, "Official D", OFFICIAL_NONE, 999, Realm.Nascent_Soul)

        main.game_instance["world"] = base_world
        main.game_instance["sim"] = None

        client = TestClient(main.app)
        resp = client.get("/api/v1/query/dynasty/detail")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["overview"]["name"] == "Han"
        assert data["summary"]["official_count"] == 3
        assert data["summary"]["top_official_rank_name"] == "Provincial Governor"
        assert [item["name"] for item in data["officials"]] == ["Official A", "Official C", "Official B"]
        assert data["officials"][0]["official_rank_key"] == OFFICIAL_PROVINCE
        assert data["officials"][0]["official_rank_name"] == "Provincial Governor"
        assert data["officials"][1]["court_reputation"] == 250
    finally:
        main.game_instance.update(original_instance)


def test_get_dynasty_overview_prefers_template_text_over_stored_desc(base_world):
    original_instance = main.game_instance.copy()
    original_lang = str(language_manager)
    try:
        language_manager.set_language("en-US")
        base_world.dynasty = Dynasty(
            id=2,
            name="Jin",
            desc="Stale stored description",
            royal_surname="Yun",
            effect_desc="",
            effects={},
            style_tag="dynasty_style_pure_discourse_and_orthodoxy",
            official_preference_type="orthodoxy",
            official_preference_value="confucianism",
            current_emperor=Emperor(
                surname="Yun",
                given_name="Chengan",
                birth_month_stamp=int(base_world.month_stamp) - 34 * 12,
                max_age=80,
            ),
        )
        main.game_instance["world"] = base_world
        main.game_instance["sim"] = None

        client = TestClient(main.app)
        resp = client.get("/api/v1/query/dynasty/overview")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "Jin"
        assert data["title"] == "Jin Dynasty"
        assert data["royal_house_name"] == "House Yun"
        assert "Stale stored description" not in data["desc"]
        assert data["desc"].startswith("Great clans stand in solemn ranks")
        assert data["style_tag"] == "Pure Discourse and Orthodoxy"
        assert data["official_preference_label"] == "Prefers Confucian cultivators"
    finally:
        language_manager.set_language(original_lang)
        main.game_instance.update(original_instance)

