from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any

from .models import Event

_STATEFUL_IDENTITIES: dict[str, tuple[str, ...]] = {
    "artifact": ("path",),
    "check_result": ("name",),
    "healthcheck": ("url",),
    "metric": ("name",),
    "model_call": ("provider",),
    "test_summary": ("suite",),
    "tool_call": ("call_id",),
    "tool_result": ("call_id",),
}
_NON_STATE_FIELDS = {
    "run_id",
    "parent_run_id",
    "prev_hash",
    "event_hash",
    "source_type",
}


def explicit_run_ids(events: Iterable[Event]) -> set[str]:
    return {
        str(event.data["run_id"])
        for event in events
        if event.data.get("run_id") not in (None, "")
    }


def bind_events_to_run(events: list[Event], run_id: str) -> list[Event]:
    """Return evidence for one execution when the trace carries explicit run IDs.

    Legacy traces with no explicit run IDs are treated as one already-isolated run.
    Once any explicit run ID is present, untagged and sibling-run events are not
    eligible to support or contradict the target execution.
    """

    if not explicit_run_ids(events):
        return list(events)
    target = str(run_id)
    return [
        event
        for event in events
        if event.data.get("run_id") not in (None, "")
        and str(event.data.get("run_id")) == target
    ]


def terminal_candidates(
    candidates: list[tuple[int, Event]],
) -> list[tuple[int, Event]]:
    """Return all observations tied at the maximal execution timestamp."""

    if not candidates:
        return []
    max_key = max(_timestamp_key(event.timestamp) for _, event in candidates)
    return [
        (index, event)
        for index, event in candidates
        if _timestamp_key(event.timestamp) == max_key
    ]


def terminal_conflict(candidates: list[tuple[int, Event]]) -> bool:
    """Return True when maximal-time observations disagree materially."""

    terminal = terminal_candidates(candidates)
    states = {_freeze(_material_state(event)) for _, event in terminal}
    return len(states) > 1


def terminal_events(events: list[Event]) -> list[Event]:
    """Collapse stateful evidence by execution time and fail closed on equal-time ties.

    For each stateful evidence identity, only observations at the maximal execution
    timestamp are eligible. If those maximal-time observations disagree materially,
    none of them is returned, so policy requirements cannot be satisfied by arrival
    order. Equivalent equal-time duplicates collapse to one representative event.
    """

    grouped: dict[tuple[str, tuple[Any, ...]], list[tuple[int, Event]]] = {}
    for index, event in enumerate(events):
        fields = _STATEFUL_IDENTITIES.get(event.event_type)
        if fields is None:
            continue
        identity = tuple(
            _identity_value(event.event_type, field, event.data.get(field))
            for field in fields
        )
        grouped.setdefault((event.event_type, identity), []).append((index, event))

    keep: set[int] = set()
    for candidates in grouped.values():
        terminal = terminal_candidates(candidates)
        if terminal_conflict(terminal):
            continue
        keep.add(terminal[-1][0])

    return [
        event
        for index, event in enumerate(events)
        if event.event_type not in _STATEFUL_IDENTITIES or index in keep
    ]


def _timestamp_key(value: str) -> tuple[int, Any]:
    text = str(value)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return (0, text)
    return (1, parsed.timestamp())


def _material_state(event: Event) -> dict[str, Any]:
    return {
        key: value
        for key, value in event.data.items()
        if key not in _NON_STATE_FIELDS
    }


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple(sorted((key, _freeze(item)) for key, item in value.items()))
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return tuple(sorted(_freeze(item) for item in value))
    return value


def _identity_value(event_type: str, field: str, value: Any) -> Any:
    if event_type == "metric" and field == "name":
        return str(value or "").lower().replace("roc-auc", "auc")
    if isinstance(value, str):
        return value.strip()
    return value
