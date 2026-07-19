from __future__ import annotations

from typing import Any, Iterable

from ..models import Event
from .common import content_digest, parse_json_records, utc_timestamp


def convert_claude_code(
    source: str | bytes | Iterable[dict[str, Any]],
) -> list[Event]:
    """Convert Claude Code JSON or stream-json output into AgentProof events.

    Content is represented by SHA-256 digests rather than copied into evidence.
    """

    events: list[Event] = []
    for record in parse_json_records(source):
        record_type = str(record.get("type", "unknown"))
        timestamp = utc_timestamp(record.get("timestamp"))
        message = record.get("message")
        message_dict = message if isinstance(message, dict) else {}
        model = message_dict.get("model") or record.get("model")
        session_id = record.get("session_id") or message_dict.get("session_id")

        if model:
            events.append(
                Event(
                    "model_call",
                    timestamp,
                    {
                        "provider": "anthropic",
                        "model": str(model),
                        "session_id": session_id,
                        "source_type": record_type,
                    },
                    "claude-code",
                )
            )

        if record_type == "assistant":
            events.extend(_assistant_events(message_dict, timestamp, session_id))
            continue
        if record_type == "user":
            events.extend(_tool_result_events(message_dict, timestamp, session_id))
            continue
        if record_type == "result":
            result_text = record.get("result")
            events.append(
                Event(
                    "agent_result",
                    timestamp,
                    {
                        "subtype": record.get("subtype"),
                        "is_error": bool(record.get("is_error", False)),
                        "duration_ms": record.get("duration_ms"),
                        "duration_api_ms": record.get("duration_api_ms"),
                        "num_turns": record.get("num_turns"),
                        "total_cost_usd": record.get("total_cost_usd"),
                        "session_id": session_id,
                        "result_sha256": content_digest(result_text)
                        if result_text is not None
                        else None,
                    },
                    "claude-code",
                )
            )
            continue
        if record_type not in {"assistant", "user", "result"}:
            events.append(
                Event(
                    "span",
                    timestamp,
                    {
                        "name": record_type,
                        "record_sha256": content_digest(record),
                        "session_id": session_id,
                    },
                    "claude-code",
                )
            )
    return events


def _assistant_events(
    message: dict[str, Any],
    timestamp: str,
    session_id: Any,
) -> list[Event]:
    content = message.get("content", [])
    if not isinstance(content, list):
        return []
    events: list[Event] = []
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "tool_use":
            continue
        arguments = block.get("input")
        events.append(
            Event(
                "tool_call",
                timestamp,
                {
                    "tool": block.get("name"),
                    "call_id": block.get("id"),
                    "arguments_sha256": content_digest(arguments),
                    "status": "started",
                    "session_id": session_id,
                },
                "claude-code",
            )
        )
    return events


def _tool_result_events(
    message: dict[str, Any],
    timestamp: str,
    session_id: Any,
) -> list[Event]:
    content = message.get("content", [])
    if not isinstance(content, list):
        return []
    events: list[Event] = []
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "tool_result":
            continue
        result = block.get("content")
        events.append(
            Event(
                "tool_result",
                timestamp,
                {
                    "call_id": block.get("tool_use_id"),
                    "is_error": bool(block.get("is_error", False)),
                    "result_sha256": content_digest(result),
                    "session_id": session_id,
                },
                "claude-code",
            )
        )
    return events
