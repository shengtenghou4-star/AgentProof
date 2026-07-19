from __future__ import annotations

import hashlib
import json
from typing import Iterable

from .models import Event


def canonical_event_bytes(event: Event) -> bytes:
    payload = {
        "event_type": event.event_type,
        "timestamp": event.timestamp,
        "data": event.data,
        "source": event.source,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def event_hash(event: Event, previous_hash: str = "") -> str:
    return hashlib.sha256(previous_hash.encode("ascii") + canonical_event_bytes(event)).hexdigest()


def verify_hash_chain(events: Iterable[Event]) -> tuple[bool, list[str]]:
    """Verify optional prev_hash/hash fields without requiring them for legacy traces."""

    errors: list[str] = []
    previous = ""
    for index, event in enumerate(events):
        expected_previous = event.data.get("prev_hash")
        recorded = event.data.get("event_hash")
        if expected_previous is None and recorded is None:
            previous = event_hash(event, previous)
            continue
        if expected_previous != previous:
            errors.append(f"event {index}: prev_hash mismatch")
        data_without_hashes = {k: v for k, v in event.data.items() if k not in {"prev_hash", "event_hash"}}
        clean = Event(event.event_type, event.timestamp, data_without_hashes, event.source)
        calculated = event_hash(clean, previous)
        if recorded != calculated:
            errors.append(f"event {index}: event_hash mismatch")
        previous = calculated
    return not errors, errors
