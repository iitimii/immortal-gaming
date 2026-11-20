from unittest.mock import AsyncMock, MagicMock, patch
import json
import asyncio

from fastapi.testclient import TestClient

from src.server import main
from src.classes.age import Age
from src.classes.alignment import Alignment
from src.classes.core.avatar import Avatar, Gender
from src.classes.root import Root
from src.systems.cultivation import Realm
from src.systems.time import Month, Year, create_month_stamp
from src.utils.id_generator import get_avatar_id
from src.classes.core.world import World
from src.classes.environment.map import Map
from src.classes.environment.tile import TileType
import pytest


def _reset_state():
    original = dict(main.game_instance)
    main.game_instance.clear()
    main.game_instance.update(
        {
            "world": None,
            "sim": None,
            "is_paused": True,
            "roleplay_auto_paused": False,
            "init_status": "idle",
            "init_phase": 0,
            "init_phase_name": "",
            "init_progress": 0,
            "init_start_time": None,
            "init_error": None,
            "run_config": None,
            "current_save_path": None,
            "llm_check_failed": False,
            "llm_error_message": "",
            "roleplay_session": {
                "controlled_avatar_id": None,
                "status": "inactive",
                "pending_request": None,
                "last_prompt_context": None,
                "conversation_session": None,
                "interaction_history": [],
            },
        }
    )
    return original


@pytest.fixture
def temp_save_dir(tmp_path):
    path = tmp_path / "saves"
    path.mkdir()
    return path


def _make_avatar(base_world) -> Avatar:
    avatar = Avatar(
        world=base_world,
        name="V1Target",
        id=get_avatar_id(),
        birth_month_stamp=create_month_stamp(Year(2000), Month.JANUARY),
        age=Age(20, Realm.Qi_Refinement, innate_max_lifespan=80),
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
    avatar.recalc_effects()
    base_world.avatar_manager.register_avatar(avatar)
    return avatar


def _create_test_map():
    game_map = Map(width=5, height=5)
    for x in range(5):
        for y in range(5):
            game_map.create_tile(x, y, TileType.PLAIN)
    return game_map


def test_v1_runtime_status_uses_ok_envelope():
    original = _reset_state()
    try:
        client = TestClient(main.app)
        response = client.get("/api/v1/query/runtime/status")

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["status"] == "idle"
        assert data["data"]["is_paused"] is True
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_world_state_returns_structured_error_when_world_missing():
    original = _reset_state()
    try:
        client = TestClient(main.app)
        response = client.get("/api/v1/query/world/state")

        assert response.status_code == 503
        detail = response.json()["detail"]
        assert detail["code"] == "WORLD_NOT_READY"
        assert detail["message"] == "World not initialized"
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_world_state_uses_ok_envelope_with_world():
    original = _reset_state()
    try:
        mock_world = MagicMock()
        mock_world.month_stamp.get_year.return_value = 100
        mock_world.month_stamp.get_month.return_value = MagicMock(value=2)
        mock_world.avatar_manager.avatars = {}
        mock_world.event_manager = None
        mock_world.current_phenomenon = None
        main.game_instance["world"] = mock_world

        client = TestClient(main.app)
        response = client.get("/api/v1/query/world/state")

        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["data"]["year"] == 100
        assert payload["data"]["month"] == 2
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_game_pause_and_resume_use_ok_envelope():
    original = _reset_state()
    try:
        main.game_instance["is_paused"] = False
        client = TestClient(main.app)

        pause_response = client.post("/api/v1/command/game/pause")
        assert pause_response.status_code == 200
        assert pause_response.json()["ok"] is True
        assert main.game_instance["is_paused"] is True

        resume_response = client.post("/api/v1/command/game/resume")
        assert resume_response.status_code == 200
        assert resume_response.json()["ok"] is True
        assert main.game_instance["is_paused"] is False
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_set_speed_updates_runtime_and_runtime_status():
    original = _reset_state()
    try:
        client = TestClient(main.app)

        status = client.get("/api/v1/query/runtime/status").json()["data"]
        assert status["speed"] == 1.0
        assert status["allowed_speeds"] == [0.5, 1.0, 2.0, 4.0]

        response = client.post("/api/v1/command/game/set-speed", json={"speed": 4})
        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["data"]["speed"] == 4.0
        assert payload["data"]["allowed_speeds"] == [0.5, 1.0, 2.0, 4.0]
        assert main.game_instance["simulation_speed"] == 4.0

        status = client.get("/api/v1/query/runtime/status").json()["data"]
        assert status["speed"] == 4.0

        client.post("/api/v1/command/game/set-speed", json={"speed": 0.5})
        assert client.get("/api/v1/query/runtime/status").json()["data"]["speed"] == 0.5
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


@pytest.mark.parametrize("body", [{"speed": 3}, {"speed": 0}, {"speed": "fast"}, {}])
def test_v1_set_speed_rejects_invalid_values_with_public_error(body):
    original = _reset_state()
    try:
        main.game_instance["simulation_speed"] = 2.0
        client = TestClient(main.app)

        response = client.post("/api/v1/command/game/set-speed", json=body)

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert detail["code"] == "INVALID_SIMULATION_SPEED"
        assert detail["details"]["allowed_speeds"] == [0.5, 1.0, 2.0, 4.0]
        assert main.game_instance["simulation_speed"] == 2.0
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_reset_restores_default_speed():
    original = _reset_state()
    try:
        client = TestClient(main.app)
        client.post("/api/v1/command/game/set-speed", json={"speed": 2})

        response = client.post("/api/v1/command/game/reset")

        assert response.status_code == 200
        assert client.get("/api/v1/query/runtime/status").json()["data"]["speed"] == 1.0
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_world_state_includes_speed():
    original = _reset_state()
    try:
        mock_world = MagicMock()
        mock_world.month_stamp.get_year.return_value = 100
        mock_world.month_stamp.get_month.return_value = MagicMock(value=2)
        mock_world.avatar_manager.avatars = {}
        mock_world.event_manager = None
        mock_world.current_phenomenon = None
        main.game_instance["world"] = mock_world
        main.game_instance["simulation_speed"] = 2.0

        client = TestClient(main.app)
        data = client.get("/api/v1/query/world/state").json()["data"]

        assert data["speed"] == 2.0
        assert data["allowed_speeds"] == [0.5, 1.0, 2.0, 4.0]
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


@pytest.mark.asyncio
async def test_load_game_into_runtime_resets_speed(tmp_path):
    from types import SimpleNamespace

    from src.server.runtime import DEFAULT_GAME_STATE, GameSessionRuntime
    from src.server.services.save_load_control import load_game_into_runtime

    save_path = tmp_path / "demo.json"
    save_path.write_text("{}", encoding="utf-8")
    runtime = GameSessionRuntime(dict(DEFAULT_GAME_STATE))
    runtime.set_simulation_speed(4.0)

    new_world = SimpleNamespace(run_config_snapshot={"content_locale": "en-US"})
    result = await load_game_into_runtime(
        runtime,
        filename="demo.json",
        saves_dir=tmp_path,
        get_save_info=lambda _path: None,
        language_manager="en-US",
        manager=SimpleNamespace(broadcast=AsyncMock()),
        t=lambda text, **_kwargs: text,
        apply_runtime_content_locale=lambda _locale: None,
        scan_avatar_assets=lambda: None,
        load_game=lambda _path: (new_world, object(), []),
        get_settings_service=lambda: SimpleNamespace(get_default_run_config=lambda: {}),
        _model_to_dict=lambda model: model,
    )

    assert result["status"] == "ok"
    assert runtime.get_simulation_speed() == 1.0


def test_v1_world_state_returns_every_living_avatar():
    original = _reset_state()
    try:
        avatars = {}
        for index in range(51):
            avatar = MagicMock()
            avatar.id = f"avatar-{index}"
            avatar.name = f"Avatar {index}"
            avatar.pos_x = index
            avatar.pos_y = index + 1
            avatar.gender.value = "male"
            avatar.current_action = None
            avatars[avatar.id] = avatar

        mock_world = MagicMock()
        mock_world.month_stamp.get_year.return_value = 100
        mock_world.month_stamp.get_month.return_value = MagicMock(value=2)
        mock_world.avatar_manager.avatars = avatars
        mock_world.event_manager = None
        mock_world.current_phenomenon = None
        main.game_instance["world"] = mock_world

        client = TestClient(main.app)
        with patch.object(main, "resolve_avatar_pic_id", return_value=1):
            response = client.get("/api/v1/query/world/state")

        assert response.status_code == 200
        returned_ids = {avatar["id"] for avatar in response.json()["data"]["avatars"]}
        assert returned_ids == set(avatars)
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_game_pause_and_drain_use_ok_envelope():
    original = _reset_state()
    try:
        main.game_instance["is_paused"] = False
        client = TestClient(main.app)

        response = client.post("/api/v1/command/game/pause-and-drain")

        assert response.status_code == 200
        assert response.json()["ok"] is True
        assert main.game_instance["is_paused"] is True
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_game_start_uses_lifecycle_service_and_ok_envelope():
    original = _reset_state()
    try:
        client = TestClient(main.app)
        with patch.object(main, "init_game_async", new_callable=AsyncMock):
            response = client.post(
                "/api/v1/command/game/start",
                json={
                    "init_npc_num": 10,
                    "sect_num": 2,
                    "npc_awakening_rate_per_month": 0.01,
                    "world_lore": "Some worldview and history",
                },
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["data"]["status"] == "ok"
        assert main.game_instance["init_status"] == "pending"
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_rankings_uses_ok_envelope():
    original = _reset_state()
    try:
        mock_ranking_manager = MagicMock()
        mock_ranking_manager.heaven_ranking = []
        mock_ranking_manager.earth_ranking = []
        mock_ranking_manager.human_ranking = []
        mock_ranking_manager.sect_ranking = []
        mock_ranking_manager.get_rankings_data.return_value = {
            "heaven": [],
            "earth": [],
            "human": [],
            "sect": [],
        }
        mock_world = MagicMock()
        mock_world.ranking_manager = mock_ranking_manager
        mock_world.avatar_manager.get_living_avatars.return_value = []
        main.game_instance["world"] = mock_world

        client = TestClient(main.app)
        response = client.get("/api/v1/query/rankings")

        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["data"] == {"heaven": [], "earth": [], "human": [], "sect": []}
        mock_ranking_manager.update_rankings_with_world.assert_called_once()
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_meta_game_data_uses_ok_envelope():
    original = _reset_state()
    try:
        client = TestClient(main.app)
        response = client.get("/api/v1/query/meta/game-data")

        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert "sects" in payload["data"]
        assert "personas" in payload["data"]
        assert "realms" in payload["data"]
        assert payload["data"]["avatar_creation"]["age"] == {
            "min": 16,
            "max_by_realm": {
                "QI_REFINEMENT": 65,
                "FOUNDATION_ESTABLISHMENT": 109,
                "CORE_FORMATION": 159,
                "NASCENT_SOUL": 459,
            },
        }
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_avatar_adjust_options_uses_ok_envelope():
    original = _reset_state()
    try:
        client = TestClient(main.app)
        response = client.get("/api/v1/query/meta/avatar-adjust-options")

        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert "techniques" in payload["data"]
        assert "weapons" in payload["data"]
        assert "goldfingers" in payload["data"]
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_avatar_meta_uses_ok_envelope():
    original = _reset_state()
    try:
        main.AVATAR_ASSETS["human"] = {"male": [1, 2], "female": [3, 4]}
        client = TestClient(main.app)
        response = client.get("/api/v1/query/meta/avatars")

        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["data"] == {"human": {"male": [1, 2], "female": [3, 4]}}
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_phenomena_list_uses_ok_envelope():
    original = _reset_state()
    try:
        client = TestClient(main.app)
        response = client.get("/api/v1/query/meta/phenomena")

        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert "phenomena" in payload["data"]
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_sect_territories_returns_empty_ok_envelope_when_world_missing():
    original = _reset_state()
    try:
        client = TestClient(main.app)
        response = client.get("/api/v1/query/sects/territories")

        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["data"] == {"sects": []}
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_mortal_overview_uses_ok_envelope_when_world_missing():
    original = _reset_state()
    try:
        client = TestClient(main.app)
        response = client.get("/api/v1/query/mortals/overview")

        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["data"]["summary"]["tracked_mortal_count"] == 0
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_dynasty_queries_use_ok_envelope_when_world_missing():
    original = _reset_state()
    try:
        client = TestClient(main.app)

        overview = client.get("/api/v1/query/dynasty/overview")
        assert overview.status_code == 200
        assert overview.json()["ok"] is True
        assert overview.json()["data"]["name"] == ""

        detail = client.get("/api/v1/query/dynasty/detail")
        assert detail.status_code == 200
        assert detail.json()["ok"] is True
        assert detail.json()["data"]["overview"]["name"] == ""
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_saves_query_uses_ok_envelope(temp_save_dir):
    original = _reset_state()
    try:
        game_map = _create_test_map()
        world = World(map=game_map, month_stamp=create_month_stamp(Year(100), Month.JANUARY))
        sim = main.Simulator(world)
        save_path = temp_save_dir / "v1_list.json"
        main.save_game(world, sim, [], save_path, custom_name="v1 list")

        with patch.object(main.CONFIG.paths, "saves", temp_save_dir):
            client = TestClient(main.app)
            response = client.get("/api/v1/query/saves")

        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["data"]["saves"]
        assert payload["data"]["saves"][0]["filename"].endswith(".json")
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_save_command_uses_ok_envelope(temp_save_dir):
    original = _reset_state()
    try:
        game_map = _create_test_map()
        world = World(map=game_map, month_stamp=create_month_stamp(Year(100), Month.JANUARY))
        sim = main.Simulator(world)
        main.game_instance["world"] = world
        main.game_instance["sim"] = sim

        with patch.object(main.CONFIG.paths, "saves", temp_save_dir):
            client = TestClient(main.app)
            response = client.post("/api/v1/command/game/save", json={"custom_name": "v1save"})

        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["data"]["status"] == "ok"
        assert "v1save" in payload["data"]["filename"]
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_delete_save_command_uses_ok_envelope(temp_save_dir):
    original = _reset_state()
    try:
        save_path = temp_save_dir / "delete_me.json"
        save_path.write_text(json.dumps({"meta": {}}), encoding="utf-8")
        db_path = main.get_events_db_path(save_path)
        db_path.write_text("", encoding="utf-8")

        with patch.object(main.CONFIG.paths, "saves", temp_save_dir):
            client = TestClient(main.app)
            response = client.post("/api/v1/command/game/delete-save", json={"filename": "delete_me.json"})

        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["data"]["status"] == "ok"
        assert not save_path.exists()
        assert not db_path.exists()
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_load_command_uses_ok_envelope():
    original = _reset_state()
    try:
        client = TestClient(main.app)
        with patch("src.server.main.load_game_into_runtime", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = {"status": "ok", "message": "Game loaded"}
            response = client.post("/api/v1/command/game/load", json={"filename": "demo.json"})

        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["data"]["status"] == "ok"
        mock_load.assert_awaited_once()
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_create_avatar_returns_ok_envelope(base_world):
    original = _reset_state()
    try:
        main.game_instance["world"] = base_world
        client = TestClient(main.app)
        response = client.post(
            "/api/v1/command/avatar/create",
            json={"given_name": "Yunzhou", "gender": "male", "age": 18, "level": 1},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["data"]["status"] == "ok"
        assert payload["data"]["avatar_id"]
        assert payload["data"]["avatar"] == {
            "id": payload["data"]["avatar_id"],
            "name": "Yunzhou",
            "x": payload["data"]["avatar"]["x"],
            "y": payload["data"]["avatar"]["y"],
            "action": payload["data"]["avatar"]["action"],
            "action_emoji": payload["data"]["avatar"]["action_emoji"],
            "gender": "male",
            "race": "human",
            "pic_id": payload["data"]["avatar"]["pic_id"],
            "realm": "QI_REFINEMENT",
            "is_dead": False,
        }
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_create_avatar_rejects_age_above_selected_realm_limit(base_world):
    original = _reset_state()
    try:
        main.game_instance["world"] = base_world
        client = TestClient(main.app)

        response = client.post(
            "/api/v1/command/avatar/create",
            json={"given_name": "Overage", "gender": "male", "age": 66, "level": 1},
        )

        assert response.status_code == 400
        assert "maximum 65" in response.json()["detail"]
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_world_secret_meta_uses_ok_envelope():
    original = _reset_state()
    try:
        client = TestClient(main.app)
        response = client.get("/api/v1/query/meta/world-secrets")

        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["data"]["options"][0] == {"id": "none", "title": "None"}
        assert payload["data"]["options"][1] == {"id": "random", "title": "Random"}
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_world_secret_meta_localizes_special_options():
    original = _reset_state()
    original_language = str(main.language_manager)
    try:
        main.apply_runtime_content_locale("en-US")
        data = main.query_service.get_world_secret_meta()

        assert data["options"][0] == {"id": "none", "title": "None"}
        assert data["options"][1] == {"id": "random", "title": "Random"}
    finally:
        main.language_manager.set_language(original_language)
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_world_secret_overview_uses_ok_envelope(base_world):
    original = _reset_state()
    try:
        from src.systems.world_secret import initialize_world_secret

        initialize_world_secret(base_world, "none")
        main.game_instance["world"] = base_world
        client = TestClient(main.app)
        response = client.get("/api/v1/query/world-secrets/overview")

        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["data"]["active_secret"]["id"] == "none"
        assert payload["data"]["fragments"] == []
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_map_presets_accepts_ui_locale_without_switching_runtime_language():
    original = _reset_state()
    original_language = str(main.language_manager)
    try:
        main.language_manager.set_language("en-US")
        client = TestClient(main.app)

        response = client.get("/api/v1/query/world/map-presets?locale=en-US")

        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        maps = {item["id"]: item for item in payload["data"]["maps"]}
        assert maps["classic"]["name"] == "Central Nine Provinces"
        assert maps["island_seas"]["desc"] == (
            "Open seas divide the isles, giving the world a broader sense of space."
        )
        assert str(main.language_manager) == "en-US"
    finally:
        main.language_manager.set_language(original_language)
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_update_avatar_adjustment_returns_ok_envelope(base_world):
    original = _reset_state()
    try:
        avatar = _make_avatar(base_world)
        main.game_instance["world"] = base_world
        weapon_id = next(iter(main.weapons_by_id.keys()))

        client = TestClient(main.app)
        response = client.post(
            "/api/v1/command/avatar/update-adjustment",
            json={
                "avatar_id": avatar.id,
                "category": "weapon",
                "target_id": weapon_id,
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["data"]["status"] == "ok"
        assert avatar.weapon is not None
        assert avatar.weapon.id == weapon_id
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_delete_avatar_returns_ok_envelope(base_world):
    original = _reset_state()
    try:
        avatar = _make_avatar(base_world)
        main.game_instance["world"] = base_world
        client = TestClient(main.app)
        response = client.post(
            "/api/v1/command/avatar/delete",
            json={"avatar_id": avatar.id},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["data"]["status"] == "ok"
        assert avatar.id not in base_world.avatar_manager.avatars
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_cleanup_events_returns_ok_envelope(tmp_path):
    original = _reset_state()
    try:
        world = World.create_with_db(
            map=_create_test_map(),
            month_stamp=create_month_stamp(Year(100), Month.JANUARY),
            events_db_path=tmp_path / "events.db",
        )
        world.event_manager.add_event(
            main.Event(
                month_stamp=create_month_stamp(Year(100), Month.JANUARY),
                content="minor",
            )
        )
        world.event_manager.add_event(
            main.Event(
                month_stamp=create_month_stamp(Year(100), Month.FEBRUARY),
                content="major",
                is_major=True,
            )
        )
        main.game_instance["world"] = world

        client = TestClient(main.app)
        response = client.delete("/api/v1/command/events/cleanup")

        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["data"]["deleted"] == 1
        assert world.event_manager.count() == 1
    finally:
        world = main.game_instance.get("world")
        if world is not None and getattr(world, "event_manager", None) is not None:
            world.event_manager.close()
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_generate_custom_content_uses_ok_envelope():
    client = TestClient(main.app)

    with patch(
        "src.server.main.generate_custom_content_draft",
        new_callable=AsyncMock,
    ) as mock_generate:
        mock_generate.return_value = {
            "category": "weapon",
            "realm": "CORE_FORMATION",
            "name": "Blazing Sun Sky-Patrol Sword",
            "is_custom": True,
        }

        response = client.post(
            "/api/v1/command/avatar/generate-custom-content",
            json={
                "category": "weapon",
                "realm": "CORE_FORMATION",
                "user_prompt": "I want a burst-focused Core Formation sword",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["status"] == "ok"
    assert payload["data"]["draft"]["name"] == "Blazing Sun Sky-Patrol Sword"
    assert mock_generate.await_count == 1


def test_v1_create_custom_content_uses_ok_envelope():
    from src.classes.custom_content import CustomContentRegistry

    original = _reset_state()
    CustomContentRegistry.reset()
    try:
        client = TestClient(main.app)
        response = client.post(
            "/api/v1/command/avatar/create-custom-content",
            json={
                "category": "technique",
                "draft": {
                    "category": "technique",
                    "name": "Nine Luminaries Breath-Burning Art",
                    "desc": "A fire-element breathing technique",
                    "effects": {
                        "extra_respire_exp_multiplier": 0.2,
                        "extra_breakthrough_success_rate": 0.1,
                    },
                    "attribute": "FIRE",
                    "grade": "UPPER",
                },
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["data"]["status"] == "ok"
        assert payload["data"]["item"]["is_custom"] is True
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_deceased_list_returns_ok_envelope_when_world_missing():
    """GET /api/v1/query/deceased returns 503 before the world is initialized."""
    original = _reset_state()
    try:
        client = TestClient(main.app)
        response = client.get("/api/v1/query/deceased")

        assert response.status_code == 503
        detail = response.json()["detail"]
        assert detail["code"] == "WORLD_NOT_READY"
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_deceased_list_returns_ok_with_world():
    """GET /api/v1/query/deceased returns ok + the deceased list once the world is initialized."""
    original = _reset_state()
    try:
        mock_world = MagicMock()
        mock_world.deceased_manager.get_all_records.return_value = []
        main.game_instance["world"] = mock_world

        client = TestClient(main.app)
        response = client.get("/api/v1/query/deceased")

        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert "deceased" in payload["data"]
        assert isinstance(payload["data"]["deceased"], list)
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_roleplay_start_and_session_query_use_ok_envelope():
    original = _reset_state()
    try:
        game_map = _create_test_map()
        world = World(map=game_map, month_stamp=create_month_stamp(Year(100), Month.JANUARY))
        avatar = _make_avatar(world)
        world.runtime = main.runtime
        main.game_instance["world"] = world
        main.game_instance["sim"] = main.Simulator(world)
        main.game_instance["is_paused"] = False

        client = TestClient(main.app)
        response = client.post("/api/v1/command/roleplay/start", json={"avatar_id": avatar.id})

        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["data"]["controlled_avatar_id"] == avatar.id
        assert payload["data"]["status"] == "awaiting_decision"

        session_response = client.get("/api/v1/query/roleplay/session")
        assert session_response.status_code == 200
        session_payload = session_response.json()
        assert session_payload["ok"] is True
        assert session_payload["data"]["controlled_avatar_id"] == avatar.id
        assert session_payload["data"]["pending_request"]["avatar_id"] == avatar.id
        assert session_payload["data"]["interaction_history"] == []
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_roleplay_submit_decision_loads_plans():
    original = _reset_state()
    try:
        game_map = _create_test_map()
        world = World(map=game_map, month_stamp=create_month_stamp(Year(100), Month.JANUARY))
        avatar = _make_avatar(world)
        world.runtime = main.runtime
        main.game_instance["world"] = world
        main.game_instance["sim"] = main.Simulator(world)
        main.game_instance["is_paused"] = False

        client = TestClient(main.app)
        start_response = client.post("/api/v1/command/roleplay/start", json={"avatar_id": avatar.id})
        request_id = start_response.json()["data"]["pending_request"]["request_id"]

        with patch("src.server.services.roleplay_service.call_llm_with_task_name", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                avatar.name: {
                    "avatar_thinking": "I will regulate my breath first, then explore.",
                    "current_emotion": "emotion_calm",
                    "short_term_objective": "Recover and seek opportunities",
                    "action_name_params_pairs": [
                        ["Respire", {}],
                    ],
                }
            }
            submit_response = client.post(
                "/api/v1/command/roleplay/submit-decision",
                json={
                    "avatar_id": avatar.id,
                    "request_id": request_id,
                    "command_text": "Regulate breath and recover first",
                },
            )

        assert submit_response.status_code == 200
        payload = submit_response.json()
        assert payload["ok"] is True
        assert payload["data"]["planned_action_count"] == 1
        assert len(avatar.planned_actions) == 1
        assert main.runtime.get_roleplay_session()["status"] == "observing"
        session_payload = client.get("/api/v1/query/roleplay/session").json()["data"]
        assert len(session_payload["interaction_history"]) == 2
        assert session_payload["interaction_history"][0]["type"] == "command"
        assert session_payload["interaction_history"][0]["text"] == "Regulate breath and recover first"
        assert session_payload["interaction_history"][1]["type"] == "action_chain"
        assert session_payload["interaction_history"][1]["actions"][0]["tokens"][0]["text"]
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_roleplay_submit_decision_records_failed_resolution():
    original = _reset_state()
    try:
        game_map = _create_test_map()
        world = World(map=game_map, month_stamp=create_month_stamp(Year(100), Month.JANUARY))
        avatar = _make_avatar(world)
        world.runtime = main.runtime
        main.game_instance["world"] = world
        main.game_instance["sim"] = main.Simulator(world)
        main.game_instance["is_paused"] = False

        client = TestClient(main.app)
        start_response = client.post("/api/v1/command/roleplay/start", json={"avatar_id": avatar.id})
        request_id = start_response.json()["data"]["pending_request"]["request_id"]

        with patch("src.server.services.roleplay_service.call_llm_with_task_name", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                avatar.name: {
                    "avatar_thinking": "Let me look around more.",
                    "action_name_params_pairs": [],
                }
            }
            submit_response = client.post(
                "/api/v1/command/roleplay/submit-decision",
                json={
                    "avatar_id": avatar.id,
                    "request_id": request_id,
                    "command_text": "Go somewhere even I do not know",
                },
            )

        assert submit_response.status_code == 422
        session_payload = client.get("/api/v1/query/roleplay/session").json()["data"]
        assert [item["type"] for item in session_payload["interaction_history"]] == ["command", "error"]
        assert session_payload["interaction_history"][0]["text"] == "Go somewhere even I do not know"
        assert "Failed to generate a valid action plan from this command" in session_payload["interaction_history"][1]["text"]
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_roleplay_stop_clears_session():
    original = _reset_state()
    try:
        game_map = _create_test_map()
        world = World(map=game_map, month_stamp=create_month_stamp(Year(100), Month.JANUARY))
        avatar = _make_avatar(world)
        world.runtime = main.runtime
        main.game_instance["world"] = world
        main.game_instance["sim"] = main.Simulator(world)
        main.game_instance["is_paused"] = False

        client = TestClient(main.app)
        start_response = client.post("/api/v1/command/roleplay/start", json={"avatar_id": avatar.id})
        assert start_response.status_code == 200

        stop_response = client.post("/api/v1/command/roleplay/stop", json={"avatar_id": avatar.id})

        assert stop_response.status_code == 200
        payload = stop_response.json()
        assert payload["ok"] is True
        assert payload["data"]["status"] == "inactive"
        assert main.runtime.get_roleplay_session()["controlled_avatar_id"] is None
        assert main.runtime.get("roleplay_auto_paused") is False
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_roleplay_submit_choice_resolves_pending_future():
    original = _reset_state()
    loop = asyncio.new_event_loop()
    try:
        game_map = _create_test_map()
        world = World(map=game_map, month_stamp=create_month_stamp(Year(100), Month.JANUARY))
        avatar = _make_avatar(world)
        world.runtime = main.runtime
        main.game_instance["world"] = world
        main.game_instance["sim"] = main.Simulator(world)
        main.game_instance["is_paused"] = False

        pending_future = loop.create_future()
        main.runtime.set_roleplay_auto_paused(True)
        session = main.runtime.get_roleplay_session()
        session.clear()
        session.update(
            {
                    "controlled_avatar_id": avatar.id,
                    "status": "awaiting_choice",
                    "pending_request": {
                        "request_id": "choice-test-1",
                        "type": "choice",
                        "avatar_id": avatar.id,
                        "title": "choice",
                        "description": "desc",
                        "options": [
                            {"key": "Accept", "title": "Accept", "description": "Accept"},
                            {"key": "Reject", "title": "Reject", "description": "Reject"},
                        ],
                    },
                    "last_prompt_context": None,
                    "conversation_session": None,
                    "interaction_history": [
                        {"type": "choice_prompt", "text": "desc", "created_at": 1.0},
                    ],
                    "_choice_future": pending_future,
            }
        )

        client = TestClient(main.app)
        submit_response = client.post(
            "/api/v1/command/roleplay/submit-choice",
            json={
                "avatar_id": avatar.id,
                "request_id": "choice-test-1",
                "selected_key": "Reject",
            },
        )

        assert submit_response.status_code == 200
        payload = submit_response.json()
        assert payload["ok"] is True
        assert payload["data"]["selected_key"] == "Reject"
        assert pending_future.done() is True
        assert pending_future.result() == "Reject"
        assert main.runtime.get_roleplay_session()["status"] == "submitting"
        session_payload = client.get("/api/v1/query/roleplay/session").json()["data"]
        assert session_payload["interaction_history"][-2]["type"] == "choice_prompt"
        assert session_payload["interaction_history"][-2]["text"] == "desc"
        assert session_payload["interaction_history"][-1]["type"] == "choice"
        assert "Reject" in session_payload["interaction_history"][-1]["text"]
    finally:
        loop.close()
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_roleplay_conversation_send_and_end_updates_session():
    original = _reset_state()
    try:
        game_map = _create_test_map()
        world = World(map=game_map, month_stamp=create_month_stamp(Year(100), Month.JANUARY))
        avatar = _make_avatar(world)
        target = _make_avatar(world)
        target.name = "Conversation Target"
        world.runtime = main.runtime
        main.game_instance["world"] = world
        main.game_instance["sim"] = main.Simulator(world)
        main.game_instance["is_paused"] = False

        session = main.runtime.get_roleplay_session()
        session["controlled_avatar_id"] = avatar.id
        session["status"] = "conversing"
        session["pending_request"] = {
            "request_id": "conversation-test-1",
            "type": "conversation",
            "avatar_id": avatar.id,
            "target_avatar_id": target.id,
            "title": "In conversation",
            "description": "Waiting to speak",
            "messages": [],
            "can_end": True,
        }
        session["conversation_session"] = {
            "session_id": "conversation-test-1",
            "request_id": "conversation-test-1",
            "avatar_id": avatar.id,
            "target_avatar_id": target.id,
            "initiator_avatar_id": avatar.id,
            "status": "awaiting_player",
            "messages": [],
            "started_at": 1.0,
            "last_summary": None,
            "last_ai_thinking": "",
        }
        session["interaction_history"] = []
        main.runtime.set_roleplay_auto_paused(True)

        client = TestClient(main.app)
        with patch("src.server.services.roleplay_service.call_llm_with_task_name", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = [
                {
                    target.name: {
                        "reply_content": "I can hear out why you came.",
                        "speaker_thinking": "Hear what he has to say first.",
                    }
                },
                {
                    "summary": "The two briefly exchanged their intentions, leaving room for future contact.",
                    "relation_hint": "relations eased slightly",
                    "story_hint": "",
                },
            ]
            send_response = client.post(
                "/api/v1/command/roleplay/conversation/send",
                json={
                    "avatar_id": avatar.id,
                    "request_id": "conversation-test-1",
                    "message": "I would like to talk with you.",
                },
            )
            end_response = client.post(
                "/api/v1/command/roleplay/conversation/end",
                json={
                    "avatar_id": avatar.id,
                    "request_id": "conversation-test-1",
                },
            )

        assert send_response.status_code == 200
        send_payload = send_response.json()
        assert send_payload["ok"] is True
        assert send_payload["data"]["reply"] == "I can hear out why you came."
        assert len(send_payload["data"]["messages"]) == 2
        session_payload_after_send = client.get("/api/v1/query/roleplay/session").json()["data"]
        history_types_after_send = [item["type"] for item in session_payload_after_send["interaction_history"]]
        assert "conversation_player" in history_types_after_send
        assert "conversation_assistant" in history_types_after_send

        assert end_response.status_code == 200
        end_payload = end_response.json()
        assert end_payload["ok"] is True
        assert "exchanged their intentions" in end_payload["data"]["summary"]
        assert main.runtime.get_roleplay_session()["pending_request"] is None
        assert main.runtime.get_roleplay_session()["conversation_session"]["status"] == "completed"
        session_payload_after_end = client.get("/api/v1/query/roleplay/session").json()["data"]
        assert session_payload_after_end["interaction_history"][-1]["type"] == "conversation_summary"
        assert "exchanged their intentions" in session_payload_after_end["interaction_history"][-1]["text"]
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_roleplay_start_rejects_when_another_avatar_is_controlled():
    original = _reset_state()
    try:
        game_map = _create_test_map()
        world = World(map=game_map, month_stamp=create_month_stamp(Year(100), Month.JANUARY))
        avatar_1 = _make_avatar(world)
        avatar_2 = _make_avatar(world)
        world.runtime = main.runtime
        main.game_instance["world"] = world
        main.game_instance["sim"] = main.Simulator(world)
        main.game_instance["is_paused"] = False

        client = TestClient(main.app)
        first_response = client.post("/api/v1/command/roleplay/start", json={"avatar_id": avatar_1.id})
        assert first_response.status_code == 200

        second_response = client.post("/api/v1/command/roleplay/start", json={"avatar_id": avatar_2.id})

        assert second_response.status_code == 409
        assert second_response.json()["detail"] == "There is already another avatar under roleplay control"
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_roleplay_submit_choice_rejects_stale_request_after_stop():
    original = _reset_state()
    try:
        game_map = _create_test_map()
        world = World(map=game_map, month_stamp=create_month_stamp(Year(100), Month.JANUARY))
        avatar = _make_avatar(world)
        world.runtime = main.runtime
        main.game_instance["world"] = world
        main.game_instance["sim"] = main.Simulator(world)
        main.game_instance["is_paused"] = False

        loop = asyncio.new_event_loop()
        pending_future = loop.create_future()
        main.runtime.set_roleplay_auto_paused(True)
        session = main.runtime.get_roleplay_session()
        session.clear()
        session.update(
            {
                    "controlled_avatar_id": avatar.id,
                    "status": "awaiting_choice",
                    "pending_request": {
                        "request_id": "choice-stale-1",
                        "type": "choice",
                        "avatar_id": avatar.id,
                        "title": "choice",
                        "description": "desc",
                        "options": [{"key": "Accept", "title": "Accept", "description": "Accept"}],
                    },
                    "last_prompt_context": None,
                    "_choice_future": pending_future,
            }
        )

        client = TestClient(main.app)
        stop_response = client.post("/api/v1/command/roleplay/stop", json={"avatar_id": avatar.id})
        assert stop_response.status_code == 200

        submit_response = client.post(
            "/api/v1/command/roleplay/submit-choice",
            json={
                "avatar_id": avatar.id,
                "request_id": "choice-stale-1",
                "selected_key": "Accept",
            },
        )

        assert submit_response.status_code == 409
        assert submit_response.json()["detail"] == "Roleplay target does not match"
        assert pending_future.cancelled() is True
        loop.close()
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_avatar_overview_returns_structured_error_when_world_missing():
    original = _reset_state()
    try:
        client = TestClient(main.app)
        response = client.get("/api/v1/query/avatars/overview")

        assert response.status_code == 503
        detail = response.json()["detail"]
        assert detail["code"] == "WORLD_NOT_READY"
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)


def test_v1_avatar_overview_returns_ok_with_world():
    original = _reset_state()
    try:
        mock_record = MagicMock()
        mock_record.to_dict.return_value = {
            "id": "dead-1",
            "name": "Fallen One",
            "gender": "male",
            "age_at_death": 88,
            "realm_at_death": "Core Formation",
            "stage_at_death": "Early Stage",
            "death_reason": "Killed in battle",
            "death_time": 35,
            "sect_name_at_death": "Azure Cloud Sect",
            "alignment_at_death": "Righteous",
            "backstory": None,
            "custom_pic_id": None,
        }
        living_avatar = MagicMock()
        living_avatar.cultivation_progress.realm = Realm.Qi_Refinement
        living_avatar.sect = MagicMock()
        rogue_avatar = MagicMock()
        rogue_avatar.cultivation_progress.realm = Realm.Qi_Refinement
        rogue_avatar.sect = None

        mock_world = MagicMock()
        mock_world.avatar_manager.avatars = {"a1": living_avatar, "a2": rogue_avatar}
        mock_world.deceased_manager.get_all_records.return_value = [mock_record]
        main.game_instance["world"] = mock_world

        client = TestClient(main.app)
        response = client.get("/api/v1/query/avatars/overview")

        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["data"]["summary"]["total_count"] == 3
        assert payload["data"]["summary"]["alive_count"] == 2
        assert payload["data"]["summary"]["dead_count"] == 1
        assert payload["data"]["summary"]["sect_member_count"] == 1
        assert payload["data"]["summary"]["rogue_count"] == 1
        assert payload["data"]["realm_distribution"][0] == {
            "realm": "Qi Refinement",
            "realm_id": "QI_REFINEMENT",
            "count": 2,
        }
    finally:
        main.game_instance.clear()
        main.game_instance.update(original)
