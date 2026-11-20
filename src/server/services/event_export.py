"""Event chronicle export.

Builds a downloadable chronicle (Markdown or JSON) of the world's event
history. Events are read through the same paginated ``EventManager`` API as
``GET /api/v1/query/events`` and are never fetched in one unbounded query.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from src.i18n import t
from src.server.services.public_api_contract import raise_public_error
from src.systems.time import MonthStamp, get_date_str

EXPORT_PAGE_SIZE = 500

_FORMATS: dict[str, tuple[str, str]] = {
    "markdown": ("md", "text/markdown; charset=utf-8"),
    "json": ("json", "application/json; charset=utf-8"),
}
_TRUE_VALUES = {"true", "1", "yes", "on"}
_FALSE_VALUES = {"false", "0", "no", "off", ""}


@dataclass(frozen=True, slots=True)
class EventExportFilters:
    format: str
    avatar_id: str | None
    major_only: bool
    from_year: int | None
    to_year: int | None


@dataclass(frozen=True, slots=True)
class EventExportEntry:
    year: int
    month: int
    month_stamp: int
    content: str
    is_major: bool
    is_story: bool
    related_avatar_ids: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "year": self.year,
            "month": self.month,
            "month_stamp": self.month_stamp,
            "content": self.content,
            "is_major": self.is_major,
            "is_story": self.is_story,
            "related_avatar_ids": list(self.related_avatar_ids),
        }


@dataclass(frozen=True, slots=True)
class EventExportFile:
    filename: str
    media_type: str
    content: str


def _parse_year(name: str, raw: str | None) -> int | None:
    if raw is None or str(raw).strip() == "":
        return None
    try:
        value = int(str(raw).strip())
    except ValueError:
        value = -1
    if value < 0:
        raise_public_error(
            status_code=400,
            code="INVALID_EXPORT_YEAR",
            message=f"{name} must be a non-negative integer",
            details={"param": name, "value": raw},
        )
    return value


def parse_export_filters(
    *,
    format: str | None,
    avatar_id: str | None,
    major_only: str | bool | None,
    from_year: str | int | None,
    to_year: str | int | None,
) -> EventExportFilters:
    normalized_format = (format or "markdown").strip().lower()
    if normalized_format not in _FORMATS:
        raise_public_error(
            status_code=400,
            code="INVALID_EXPORT_FORMAT",
            message="format must be one of: markdown, json",
            details={"format": format, "allowed": sorted(_FORMATS)},
        )

    if isinstance(major_only, bool):
        major = major_only
    else:
        raw_major = str(major_only or "").strip().lower()
        if raw_major in _TRUE_VALUES:
            major = True
        elif raw_major in _FALSE_VALUES:
            major = False
        else:
            raise_public_error(
                status_code=400,
                code="INVALID_EXPORT_MAJOR_ONLY",
                message="major_only must be true or false",
                details={"value": major_only},
            )

    start = _parse_year("from_year", None if from_year is None else str(from_year))
    end = _parse_year("to_year", None if to_year is None else str(to_year))
    if start is not None and end is not None and start > end:
        raise_public_error(
            status_code=400,
            code="INVALID_EXPORT_YEAR_RANGE",
            message="from_year must not be greater than to_year",
            details={"from_year": start, "to_year": end},
        )

    return EventExportFilters(
        format=normalized_format,
        avatar_id=(str(avatar_id).strip() or None) if avatar_id is not None else None,
        major_only=major,
        from_year=start,
        to_year=end,
    )


def _to_entry(event: Any) -> EventExportEntry:
    stamp = MonthStamp(int(getattr(event, "month_stamp", 0) or 0))
    return EventExportEntry(
        year=int(stamp.get_year()),
        month=int(stamp.get_month().value),
        month_stamp=int(stamp),
        content=str(getattr(event, "content", "") or ""),
        is_major=bool(getattr(event, "is_major", False)),
        is_story=bool(getattr(event, "is_story", False)),
        related_avatar_ids=[
            str(item) for item in (getattr(event, "related_avatars", None) or []) if item is not None
        ],
    )


def collect_export_entries(
    event_manager: Any,
    filters: EventExportFilters,
    *,
    page_size: int = EXPORT_PAGE_SIZE,
) -> list[EventExportEntry]:
    """Walk the paginated event storage and return matching entries oldest first.

    Pages arrive newest first, so the walk stops as soon as it passes below
    ``from_year`` and skips everything newer than ``to_year``.
    """
    collected: list[EventExportEntry] = []
    cursor: str | None = None
    major_scope = "major" if filters.major_only else "all"
    while True:
        events, next_cursor, has_more = event_manager.get_events_paginated(
            avatar_id=filters.avatar_id,
            major_scope=major_scope,
            cursor=cursor,
            limit=page_size,
        )
        reached_start = False
        for event in events:
            entry = _to_entry(event)
            if filters.to_year is not None and entry.year > filters.to_year:
                continue
            if filters.from_year is not None and entry.year < filters.from_year:
                reached_start = True
                break
            collected.append(entry)
        if reached_start or not has_more or not next_cursor:
            break
        cursor = next_cursor
    collected.reverse()
    return collected


def _resolve_avatar_name(world: Any, avatar_id: str | None) -> str | None:
    if not avatar_id:
        return None
    avatar_manager = getattr(world, "avatar_manager", None)
    avatar = avatar_manager.get_avatar(avatar_id) if avatar_manager is not None else None
    name = getattr(avatar, "name", None)
    if not name:
        deceased_manager = getattr(world, "deceased_manager", None)
        record = deceased_manager.get_record(avatar_id) if deceased_manager is not None else None
        name = getattr(record, "name", None)
    return str(name) if name else str(avatar_id)


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _year_span(
    entries: list[EventExportEntry], filters: EventExportFilters, current_year: int
) -> tuple[int, int]:
    start = filters.from_year if filters.from_year is not None else (entries[0].year if entries else current_year)
    end = filters.to_year if filters.to_year is not None else (entries[-1].year if entries else current_year)
    return start, end


def build_export_filename(
    *,
    filters: EventExportFilters,
    avatar_name: str | None,
    start_year: int,
    end_year: int,
) -> str:
    parts = ["chronicle"]
    if filters.avatar_id:
        parts.append(_slugify(avatar_name or "") or _slugify(filters.avatar_id) or "avatar")
    if filters.major_only:
        parts.append("major")
    if start_year == end_year:
        parts.append(f"year-{start_year}")
    else:
        parts.append(f"year-{start_year}-to-{end_year}")
    extension = _FORMATS[filters.format][0]
    return f"{'-'.join(parts)}.{extension}"


def _single_line(text: str) -> str:
    return " ".join(text.split())


def render_markdown(
    entries: list[EventExportEntry],
    *,
    world_date: str,
    map_id: str | None,
    avatar_name: str | None,
    filters: EventExportFilters,
    start_year: int,
    end_year: int,
) -> str:
    lines: list[str] = [f"# {t('event_export_title')}", ""]
    lines.append(f"- {t('event_export_world_date', date=world_date)}")
    if map_id:
        lines.append(f"- {t('event_export_map', map_id=map_id)}")
    if avatar_name:
        lines.append(f"- {t('event_export_scope_avatar', avatar=avatar_name)}")
    if filters.major_only:
        lines.append(f"- {t('event_export_scope_major')}")
    lines.append(f"- {t('event_export_scope_years', from_year=start_year, to_year=end_year)}")
    lines.append(f"- {t('event_export_event_count', count=len(entries))}")

    if not entries:
        lines.extend(["", f"_{t('event_export_empty')}_"])
        return "\n".join(lines) + "\n"

    current_year: int | None = None
    last_bullet_stamp: int | None = None
    for entry in entries:
        if entry.year != current_year:
            current_year = entry.year
            last_bullet_stamp = None
            lines.extend(["", f"## {t('event_export_year_heading', year=entry.year)}", ""])

        month_label = t("event_export_month_label", month=entry.month)
        if entry.is_story:
            if last_bullet_stamp != entry.month_stamp:
                lines.append(f"- {month_label}:")
                last_bullet_stamp = entry.month_stamp
            for paragraph in (part.strip() for part in entry.content.strip().splitlines()):
                lines.append(f"  > {paragraph}" if paragraph else "  >")
            continue

        text = _single_line(entry.content)
        if entry.is_major and text:
            text = f"**{text}**"
        lines.append(f"- {month_label}: {text}")
        last_bullet_stamp = entry.month_stamp

    return "\n".join(lines) + "\n"


def render_json(
    entries: list[EventExportEntry],
    *,
    world_month_stamp: int,
    world_date: str,
    map_id: str | None,
    avatar_name: str | None,
    filters: EventExportFilters,
    start_year: int,
    end_year: int,
) -> str:
    payload = {
        "metadata": {
            "title": str(t("event_export_title")),
            "world_month_stamp": world_month_stamp,
            "world_date": world_date,
            "map_id": map_id,
            "filters": {
                "avatar_id": filters.avatar_id,
                "avatar_name": avatar_name,
                "major_only": filters.major_only,
                "from_year": filters.from_year,
                "to_year": filters.to_year,
            },
            "from_year": start_year,
            "to_year": end_year,
            "event_count": len(entries),
        },
        "events": [entry.to_dict() for entry in entries],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_event_export(
    runtime: Any,
    *,
    format: str | None = "markdown",
    avatar_id: str | None = None,
    major_only: str | bool | None = None,
    from_year: str | int | None = None,
    to_year: str | int | None = None,
) -> EventExportFile:
    filters = parse_export_filters(
        format=format,
        avatar_id=avatar_id,
        major_only=major_only,
        from_year=from_year,
        to_year=to_year,
    )

    world = runtime.get("world")
    if world is None:
        raise_public_error(status_code=503, code="WORLD_NOT_READY", message="World not initialized")
    event_manager = getattr(world, "event_manager", None)
    if event_manager is None:
        raise_public_error(status_code=503, code="EVENTS_NOT_READY", message="Event manager not initialized")

    entries = collect_export_entries(event_manager, filters)

    world_stamp = int(getattr(world, "month_stamp", 0) or 0)
    current_year = int(MonthStamp(world_stamp).get_year())
    world_date = str(get_date_str(world_stamp))
    map_id = (getattr(world, "run_config_snapshot", None) or {}).get("map_id")
    avatar_name = _resolve_avatar_name(world, filters.avatar_id)
    start_year, end_year = _year_span(entries, filters, current_year)
    filename = build_export_filename(
        filters=filters, avatar_name=avatar_name, start_year=start_year, end_year=end_year
    )

    common = {
        "world_date": world_date,
        "map_id": str(map_id) if map_id else None,
        "avatar_name": avatar_name,
        "filters": filters,
        "start_year": start_year,
        "end_year": end_year,
    }
    if filters.format == "json":
        content = render_json(entries, world_month_stamp=world_stamp, **common)
    else:
        content = render_markdown(entries, **common)
    return EventExportFile(filename=filename, media_type=_FORMATS[filters.format][1], content=content)
