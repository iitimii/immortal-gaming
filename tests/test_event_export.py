"""Tests for GET /api/v1/query/events/export (event chronicle export)."""

import json
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.classes.core.world import World
from src.classes.environment.map import Map
from src.classes.environment.tile import TileType
from src.classes.event import Event
from src.server.services.event_export import (
    collect_export_entries,
    parse_export_filters,
)
from src.sim.managers.event_manager import EventManager
from src.systems.time import Month, Year, create_month_stamp

EXPORT_URL = "/api/v1/query/events/export"


def _make_map() -> Map:
    game_map = Map(width=4, height=4)
    for x in range(4):
        for y in range(4):
            game_map.create_tile(x, y, TileType.PLAIN)
    return game_map


def _event(year, month, content, avatars=None, *, is_major=False, is_story=False) -> Event:
    return Event(
        month_stamp=create_month_stamp(Year(year), Month(month)),
        content=content,
        related_avatars=avatars,
        is_major=is_major,
        is_story=is_story,
    )


def _make_world(tmp_path, events=()) -> World:
    world = World.create_with_db(
        map=_make_map(),
        month_stamp=create_month_stamp(Year(112), Month(3)),
        events_db_path=tmp_path / "events.db",
    )
    world.run_config_snapshot = {"map_id": "classic"}
    for event in events:
        world.event_manager.add_event(event)
    return world


@pytest.fixture
def history_world(tmp_path):
    world = _make_world(
        tmp_path,
        [
            _event(100, 1, "Alice arrived at the mountain.", ["a1"]),
            _event(100, 2, "Bob sparred with Carol.", ["a2", "a3"]),
            _event(100, 2, "The duel lasted until dusk.\n\nBoth bowed in respect.", ["a2", "a3"], is_story=True),
            _event(105, 6, "Alice broke through to Foundation Establishment.", ["a1"], is_major=True),
            _event(105, 6, "Heaven and earth trembled.", ["a1"], is_story=True),
            _event(110, 9, "Bob founded a cave abode.", ["a2"]),
            _event(112, 1, "Alice and Bob became Dao companions.", ["a1", "a2"], is_major=True),
        ],
    )
    yield world
    world.event_manager.close()


@pytest.fixture
def make_client():
    from src.server import main

    original = dict(main.game_instance)

    def _factory(world):
        main.game_instance["world"] = world
        main.game_instance["sim"] = MagicMock()
        main.game_instance["is_paused"] = True
        return TestClient(main.app)

    yield _factory
    main.game_instance.clear()
    main.game_instance.update(original)


def _json_export(client, **params):
    response = client.get(EXPORT_URL, params={"format": "json", **params})
    assert response.status_code == 200, response.text
    return json.loads(response.content.decode("utf-8"))


def test_markdown_is_default_and_downloads_as_attachment(history_world, make_client):
    client = make_client(history_world)
    response = client.get(EXPORT_URL)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.headers["content-disposition"] == (
        'attachment; filename="chronicle-year-100-to-112.md"'
    )
    assert response.headers["cache-control"] == "no-store"


def test_markdown_orders_years_and_quotes_stories(history_world, make_client):
    client = make_client(history_world)
    text = client.get(EXPORT_URL, params={"format": "markdown"}).content.decode("utf-8")
    lines = text.splitlines()

    assert lines[0] == "# Chronicle of the Cultivation World"
    assert "- Exported at: Year 112 Month 3" in lines
    assert "- Map: classic" in lines
    assert "- Events: 7" in lines

    headings = [line for line in lines if line.startswith("## ")]
    assert headings == ["## Year 100", "## Year 105", "## Year 110", "## Year 112"]

    year_100 = lines.index("## Year 100")
    assert lines[year_100 + 2 : year_100 + 7] == [
        "- Month 1: Alice arrived at the mountain.",
        "- Month 2: Bob sparred with Carol.",
        "  > The duel lasted until dusk.",
        "  >",
        "  > Both bowed in respect.",
    ]
    assert "- Month 6: **Alice broke through to Foundation Establishment.**" in lines
    breakthrough = lines.index("- Month 6: **Alice broke through to Foundation Establishment.**")
    assert lines[breakthrough + 1] == "  > Heaven and earth trembled."
    assert lines[-1] == "- Month 1: **Alice and Bob became Dao companions.**"


def test_story_without_preceding_event_gets_its_own_month_bullet(tmp_path, make_client):
    world = _make_world(tmp_path, [_event(100, 4, "A lone legend was told.", is_story=True)])
    try:
        lines = make_client(world).get(EXPORT_URL).content.decode("utf-8").splitlines()
        index = lines.index("- Month 4:")
        assert lines[index + 1] == "  > A lone legend was told."
    finally:
        world.event_manager.close()


def test_json_shape_and_metadata(history_world, make_client):
    client = make_client(history_world)
    response = client.get(EXPORT_URL, params={"format": "json"})

    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["content-disposition"] == (
        'attachment; filename="chronicle-year-100-to-112.json"'
    )
    payload = json.loads(response.content.decode("utf-8"))
    metadata = payload["metadata"]
    assert metadata["title"] == "Chronicle of the Cultivation World"
    assert metadata["map_id"] == "classic"
    assert metadata["world_month_stamp"] == int(create_month_stamp(Year(112), Month(3)))
    assert metadata["event_count"] == 7
    assert metadata["from_year"] == 100
    assert metadata["to_year"] == 112
    assert metadata["filters"] == {
        "avatar_id": None,
        "avatar_name": None,
        "major_only": False,
        "from_year": None,
        "to_year": None,
    }

    events = payload["events"]
    assert [event["month_stamp"] for event in events] == sorted(event["month_stamp"] for event in events)
    assert events[0] == {
        "year": 100,
        "month": 1,
        "month_stamp": int(create_month_stamp(Year(100), Month(1))),
        "content": "Alice arrived at the mountain.",
        "is_major": False,
        "is_story": False,
        "related_avatar_ids": ["a1"],
    }
    # Same-month events keep insertion order (fact event before its story).
    assert [event["content"] for event in events[1:3]] == [
        "Bob sparred with Carol.",
        "The duel lasted until dusk.\n\nBoth bowed in respect.",
    ]
    assert events[2]["is_story"] is True


def test_avatar_filter_only_includes_related_events(history_world, make_client):
    client = make_client(history_world)
    payload = _json_export(client, avatar_id="a2")

    assert [event["content"] for event in payload["events"]] == [
        "Bob sparred with Carol.",
        "The duel lasted until dusk.\n\nBoth bowed in respect.",
        "Bob founded a cave abode.",
        "Alice and Bob became Dao companions.",
    ]
    assert all("a2" in event["related_avatar_ids"] for event in payload["events"])
    assert payload["metadata"]["filters"]["avatar_id"] == "a2"


def test_avatar_filter_uses_avatar_name_in_title_and_filename(history_world, make_client):
    avatar = MagicMock()
    avatar.name = "Bob Stone"
    history_world.avatar_manager.avatars["a2"] = avatar
    client = make_client(history_world)

    response = client.get(EXPORT_URL, params={"avatar_id": "a2"})
    assert response.headers["content-disposition"] == (
        'attachment; filename="chronicle-bob-stone-year-100-to-112.md"'
    )
    assert "- Related to: Bob Stone" in response.content.decode("utf-8").splitlines()


def test_major_only_excludes_minor_and_story_events(history_world, make_client):
    client = make_client(history_world)
    payload = _json_export(client, major_only="true")

    assert [event["content"] for event in payload["events"]] == [
        "Alice broke through to Foundation Establishment.",
        "Alice and Bob became Dao companions.",
    ]
    assert payload["metadata"]["filters"]["major_only"] is True

    response = client.get(EXPORT_URL, params={"major_only": "true"})
    assert response.headers["content-disposition"] == (
        'attachment; filename="chronicle-major-year-105-to-112.md"'
    )
    assert "- Major events only" in response.content.decode("utf-8").splitlines()


def test_year_range_is_inclusive(history_world, make_client):
    client = make_client(history_world)
    payload = _json_export(client, from_year="105", to_year="110")

    assert [event["year"] for event in payload["events"]] == [105, 105, 110]
    assert payload["metadata"]["from_year"] == 105
    assert payload["metadata"]["to_year"] == 110

    response = client.get(EXPORT_URL, params={"from_year": 105, "to_year": 105})
    assert response.headers["content-disposition"] == 'attachment; filename="chronicle-year-105.md"'


def test_filters_combine(history_world, make_client):
    client = make_client(history_world)
    payload = _json_export(client, avatar_id="a1", major_only="true", to_year="110")
    assert [event["content"] for event in payload["events"]] == [
        "Alice broke through to Foundation Establishment.",
    ]


@pytest.mark.parametrize(
    ("params", "code"),
    [
        ({"format": "pdf"}, "INVALID_EXPORT_FORMAT"),
        ({"from_year": "abc"}, "INVALID_EXPORT_YEAR"),
        ({"to_year": "-3"}, "INVALID_EXPORT_YEAR"),
        ({"from_year": "110", "to_year": "100"}, "INVALID_EXPORT_YEAR_RANGE"),
        ({"major_only": "maybe"}, "INVALID_EXPORT_MAJOR_ONLY"),
    ],
)
def test_invalid_params_return_public_error(history_world, make_client, params, code):
    client = make_client(history_world)
    response = client.get(EXPORT_URL, params=params)

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == code
    assert isinstance(detail["message"], str)


def test_requires_world(make_client):
    response = make_client(None).get(EXPORT_URL)
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "WORLD_NOT_READY"


def test_empty_world_history(tmp_path, make_client):
    world = _make_world(tmp_path)
    try:
        client = make_client(world)
        response = client.get(EXPORT_URL)
        assert response.status_code == 200
        assert response.headers["content-disposition"] == 'attachment; filename="chronicle-year-112.md"'
        text = response.content.decode("utf-8")
        assert "- Events: 0" in text
        assert "No events were recorded for this selection." in text
        assert "## Year" not in text

        payload = _json_export(client)
        assert payload["events"] == []
        assert payload["metadata"]["event_count"] == 0
    finally:
        world.event_manager.close()


def test_collect_walks_pages_and_stops_below_from_year():
    manager = EventManager.create_in_memory()
    for year in range(100, 110):
        manager.add_event(_event(year, 1, f"Event {year}"))

    calls = []
    original = manager.get_events_paginated

    def spy(**kwargs):
        calls.append(kwargs)
        return original(**kwargs)

    manager.get_events_paginated = spy
    filters = parse_export_filters(
        format="json", avatar_id=None, major_only=None, from_year="106", to_year="108"
    )
    entries = collect_export_entries(manager, filters, page_size=2)

    assert [entry.year for entry in entries] == [106, 107, 108]
    # Pages hold 109-108, 107-106, 105-104; the walk stops once it passes year 106.
    assert len(calls) == 3
    assert all(call["limit"] == 2 for call in calls)


def test_collect_reads_every_page_without_range():
    manager = EventManager.create_in_memory()
    for month in range(1, 13):
        manager.add_event(_event(100, month, f"Month {month}"))
    filters = parse_export_filters(
        format="markdown", avatar_id=None, major_only=False, from_year=None, to_year=None
    )
    entries = collect_export_entries(manager, filters, page_size=5)
    assert [entry.month for entry in entries] == list(range(1, 13))
