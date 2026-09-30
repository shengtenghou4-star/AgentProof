from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .models import Event

_STATEFUL_IDENTITIES: dict[str, tuple[str, ...]] = {
    "artifact": ("path",),
    "check_result": ("name",),
    "healthcheck": ("url",),
    "metric": ("name",),
    "model_call": ("provider",),
    "test_summary": (),
    "tool_call": ("call_id",),
    "tool_result": ("call_id",),
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


def terminal_events(events: list[Event]) -> list[Event]:
    """Collapse repeated stateful evidence objects to their terminal observation."""

    latest: dict[tuple[str, tuple[Any, ...]], int] = {}
    for index, event in enumerate(events):
        fields = _STATEFUL_IDENTITIES.get(event.event_type)
        if fields is None:
            continue
        identity = tuple(
            _identity_value(event.event_type, field, event.data.get(field))
            for field in fields
        )
        latest[(event.event_type, identity)] = index

    keep = set(latest.values())
    return [
        event
        for index, event in enumerate(events)
        if event.event_type not in _STATEFUL_IDENTITIES or index in keep
    ]


def _identity_value(event_type: str, field: str, value: Any) -> Any:
    if event_type == "metric" and field == "name":
        return str(value or "").lower().replace("roc-auc", "auc")
    if isinstance(value, str):
        return value.strip()
    return value
