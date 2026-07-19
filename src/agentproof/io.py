from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .models import Event


def load_events(path: str | Path) -> list[Event]:
    """Load newline-delimited JSON events with strict shape checks."""

    items: list[Any] = []
    source_path = Path(path)
    with source_path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            if not raw.strip():
                continue
            try:
                items.append(json.loads(raw))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}: {exc.msg}") from exc
    return parse_events(items)


def parse_events(items: Any) -> list[Event]:
    if not isinstance(items, list):
        raise ValueError("events must be a JSON array")
    events: list[Event] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Event {index} must be a JSON object")
        if "event_type" not in item or "timestamp" not in item:
            raise ValueError(f"Event {index} lacks event_type or timestamp")
        data = item.get("data", {})
        if not isinstance(data, dict):
            raise ValueError(f"Event data {index} must be an object")
        events.append(
            Event(
                event_type=str(item["event_type"]),
                timestamp=str(item["timestamp"]),
                data=data,
                source=str(item.get("source", "runtime")),
            )
        )
    return events


def dump_events(events: Iterable[Event], path: str | Path) -> None:
    with Path(path).open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(
                json.dumps(
                    {
                        "event_type": event.event_type,
                        "timestamp": event.timestamp,
                        "data": event.data,
                        "source": event.source,
                    },
                    sort_keys=True,
                )
                + "\n"
            )
