from __future__ import annotations

from typing import Any, Iterable

from ..models import Event
from .common import content_digest, parse_json_records, utc_timestamp


def convert_openai_responses(
    source: str | bytes | Iterable[dict[str, Any]],
) -> list[Event]:
    """Convert OpenAI Responses API objects or event streams into evidence."""

    events: list[Event] = []
    for record in parse_json_records(source):
        event_type = str(record.get("type", "response"))
        timestamp = utc_timestamp(record.get("timestamp") or record.get("created_at"))
        response = record.get("response")
        response_dict = response if isinstance(response, dict) else record
        response_id = response_dict.get("id") or record.get("response_id")
        model = response_dict.get("model") or record.get("model")

        if model:
            events.append(
                Event(
                    "model_call",
                    timestamp,
                    {
                        "provider": "openai",
                        "model": str(model),
                        "request_id": response_id,
                        "source_type": event_type,
                    },
                    "openai-responses",
                )
            )

        item = record.get("item")
        if isinstance(item, dict):
            tool_event = _tool_event(item, timestamp, response_id)
            if tool_event is not None:
                events.append(tool_event)

        if event_type == "response.function_call_arguments.done":
            arguments = record.get("arguments")
            events.append(
                Event(
                    "tool_call",
                    timestamp,
                    {
                        "tool": record.get("name"),
                        "call_id": record.get("item_id") or record.get("call_id"),
                        "arguments_sha256": content_digest(arguments),
                        "status": "arguments_complete",
                        "request_id": response_id,
                    },
                    "openai-responses",
                )
            )

        if event_type in {"response.completed", "response.failed", "response.cancelled"}:
            output = response_dict.get("output")
            usage = response_dict.get("usage")
            events.append(
                Event(
                    "agent_result",
                    timestamp,
                    {
                        "status": response_dict.get("status") or event_type.rsplit(".", 1)[-1],
                        "request_id": response_id,
                        "output_sha256": content_digest(output) if output is not None else None,
                        "usage": _safe_usage(usage),
                        "error_sha256": content_digest(response_dict.get("error"))
                        if response_dict.get("error") is not None
                        else None,
                    },
                    "openai-responses",
                )
            )
        elif not model and not isinstance(item, dict):
            events.append(
                Event(
                    "span",
                    timestamp,
                    {
                        "name": event_type,
                        "record_sha256": content_digest(record),
                        "request_id": response_id,
                    },
                    "openai-responses",
                )
            )
    return events


def _tool_event(
    item: dict[str, Any],
    timestamp: str,
    response_id: Any,
) -> Event | None:
    item_type = str(item.get("type", ""))
    if item_type not in {"function_call", "computer_call", "web_search_call", "file_search_call"}:
        return None
    arguments = item.get("arguments") or item.get("action") or item.get("query")
    return Event(
        "tool_call",
        timestamp,
        {
            "tool": item.get("name") or item_type,
            "call_id": item.get("call_id") or item.get("id"),
            "arguments_sha256": content_digest(arguments),
            "status": item.get("status"),
            "request_id": response_id,
        },
        "openai-responses",
    )


def _safe_usage(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    allowed = {
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "input_tokens_details",
        "output_tokens_details",
    }
    return {key: value[key] for key in allowed if key in value}
