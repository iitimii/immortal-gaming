from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.server import main


def test_generate_custom_content_api_uses_generation_service():
    client = TestClient(main.app)

    with patch(
        "src.server.main.generate_custom_content_draft",
        new_callable=AsyncMock,
    ) as mock_generate:
        mock_generate.return_value = {
            "category": "weapon",
            "realm": "CORE_FORMATION",
            "name": "Blazing Sky-Patrol Sword",
            "desc": "Test description",
            "effects": {"extra_battle_strength_points": 3},
            "effect_desc": "Extra battle strength +3",
            "weapon_type": "SWORD",
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
    payload = response.json()["data"]
    assert payload["status"] == "ok"
    assert payload["draft"]["name"] == "Blazing Sky-Patrol Sword"
    assert payload["draft"]["is_custom"] is True
    assert mock_generate.await_count == 1


def test_generate_custom_goldfinger_api_uses_generation_service():
    client = TestClient(main.app)

    with patch(
        "src.server.main.generate_custom_goldfinger_draft",
        new_callable=AsyncMock,
    ) as mock_generate:
        mock_generate.return_value = {
            "category": "goldfinger",
            "name": "Destiny Check-In Ledger",
            "desc": "A ledger of destiny whose pages turn only in your heart.",
            "story_prompt": "Focus on the feeling of daily check-ins and fate paying back.",
            "effects": {"extra_luck": 12},
            "effect_desc": "Luck +12",
            "mechanism_type": "effect_only",
            "is_custom": True,
        }

        response = client.post(
            "/api/v1/command/avatar/generate-custom-content",
            json={
                "category": "goldfinger",
                "user_prompt": "I want a check-in style goldfinger with slightly strong numbers",
            },
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["status"] == "ok"
    assert payload["draft"]["category"] == "goldfinger"
    assert payload["draft"]["is_custom"] is True
    assert mock_generate.await_count == 1


def test_create_custom_content_api_registers_new_item():
    from src.classes.custom_content import CustomContentRegistry

    CustomContentRegistry.reset()
    client = TestClient(main.app)
    response = client.post(
        "/api/v1/command/avatar/create-custom-content",
        json={
            "category": "technique",
            "draft": {
                "category": "technique",
                "name": "Nine Luminaries Flame Breath Art",
                "desc": "Fire-element respiration technique",
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
    payload = response.json()["data"]
    assert payload["status"] == "ok"
    assert payload["item"]["is_custom"] is True
    assert payload["item"]["id"] >= 900001


def test_create_custom_goldfinger_api_registers_new_item():
    from src.classes.custom_content import CustomContentRegistry

    CustomContentRegistry.reset()
    client = TestClient(main.app)
    response = client.post(
        "/api/v1/command/avatar/create-custom-content",
        json={
            "category": "goldfinger",
            "draft": {
                "category": "goldfinger",
                "name": "Myriad Tribulations Reversal Token",
                "desc": "An invisible token shields you; the worse your luck, the easier the comeback.",
                "story_prompt": "In dangerous situations, emphasize the comeback.",
                "effects": {
                    "extra_luck": 10,
                    "extra_breakthrough_success_rate": 0.1,
                },
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["status"] == "ok"
    assert payload["item"]["is_custom"] is True
    assert payload["item"]["id"] >= 930001


def test_create_custom_goldfinger_api_accepts_numeric_string_effect_values():
    from src.classes.custom_content import CustomContentRegistry

    CustomContentRegistry.reset()
    client = TestClient(main.app)
    response = client.post(
        "/api/v1/command/avatar/create-custom-content",
        json={
            "category": "goldfinger",
            "draft": {
                "category": "goldfinger",
                "name": "Echo of Heavenly Fortune",
                "desc": "You always scoop a little extra benefit from the echoes of fate.",
                "effects": {
                    "extra_luck": "14",
                    "extra_breakthrough_success_rate": "0.12",
                },
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["status"] == "ok"
    assert payload["item"]["is_custom"] is True
    assert payload["item"]["effect_desc"]


def test_create_custom_goldfinger_api_rejects_noncanonical_effect_keys():
    client = TestClient(main.app)
    response = client.post(
        "/api/v1/command/avatar/create-custom-content",
        json={
            "category": "goldfinger",
            "draft": {
                "category": "goldfinger",
                "name": "Favored by Fate",
                "desc": "You always scoop a little benefit from the cracks of fate.",
                "effects": {
                    "luck_boost": 15,
                },
            },
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported custom effect: luck_boost."


@pytest.mark.asyncio
async def test_generate_custom_goldfinger_draft_passes_allowed_effects_to_llm():
    from src.server.services.custom_goldfinger_service import generate_custom_goldfinger_draft

    with patch(
        "src.server.services.custom_goldfinger_service.call_llm_with_task_name",
        new_callable=AsyncMock,
    ) as mock_call:
        mock_call.return_value = {
            "name": "Destiny Check-In Ledger",
            "desc": "A ledger of destiny whose pages turn only in your heart.",
            "story_prompt": "Focus on the feeling of daily check-ins and fate paying back.",
            "effects": {"extra_luck": 12},
            "rarity": "SSR",
        }

        draft = await generate_custom_goldfinger_draft("I want a check-in style goldfinger with slightly strong numbers")

    assert draft["category"] == "goldfinger"
    assert mock_call.await_count == 1
    infos = mock_call.await_args.kwargs["infos"]
    assert "allowed_effects" in infos
    assert "extra_luck" in infos["allowed_effects"]
