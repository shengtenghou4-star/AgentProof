from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Iterable


def parse_json_records(source: str | bytes | Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(source, bytes):
        source = source.decode("utf-8")
    if isinstance(source, str):
        stripped = source.strip()
        if not stripped:
            return []
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            records: list[dict[str, Any]] = []
            for line_number, line in enumerate(stripped.splitlines(), start=1):
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"invalid JSON record on line {line_number}: {exc.msg}"
                    ) from exc
                if not isinstance(item, dict):
                    raise ValueError(f"record on line {line_number} must be an object")
                records.append(item)
            return records
        if isinstance(payload, dict):
            return [payload]
        if isinstance(payload, list) and all(isinstance(item, dict) for item in payload):
            return list(payload)
        raise ValueError("JSON input must be an object, object list, or JSONL")
    return [dict(item) for item in source]


def utc_timestamp(value: Any = None) -> str:
    if value not in (None, ""):
        return str(value)
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def content_digest(value: Any) -> str:
    if isinstance(value, bytes):
        payload = value
    elif isinstance(value, str):
        payload = value.encode("utf-8")
    else:
        payload = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
