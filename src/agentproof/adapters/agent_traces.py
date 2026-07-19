from __future__ import annotations

from typing import Any, Iterable

from ..models import Event
from .common import content_digest, parse_json_records, utc_timestamp


def convert_agent_traces(
    source: str | bytes | Iterable[dict[str, Any]],
) -> list[Event]:
    """Normalize OpenAI Agents SDK, LangGraph, and callback-style JSON traces.

    This adapter focuses on stable semantic fields: model invocations, tool calls,
    tool results, errors, and final outputs. Unknown records remain hashed spans.
    """

    events: list[Event] = []
    for record in parse_json_records(source):
        event_name = str(
            record.get("event")
            or record.get("type")
            or record.get("name")
            or "unknown"
        )
        timestamp = utc_timestamp(
            record.get("timestamp") or record.get("time") or record.get("start_time")
        )
        data = record.get("data") if isinstance(record.get("data"), dict) else record
        metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
        run_id = _first(record.get("run_id"), data.get("run_id"), metadata.get("run_id"))
        parent_run_id = _first(
            record.get("parent_run_id"),
            data.get("parent_run_id"),
            metadata.get("parent_run_id"),
        )

        lowered = event_name.lower()
        if any(token in lowered for token in ("chat_model", "model", "generation")):
            model = _first(
                data.get("model"),
                metadata.get("model"),
                metadata.get("ls_model_name"),
                _nested(data, "response", "model"),
            )
            provider = _first(
                data.get("provider"),
                metadata.get("provider"),
                metadata.get("ls_provider"),
                "unknown",
            )
            events.append(
                Event(
                    "model_call",
                    timestamp,
                    {
                        "provider": str(provider),
                        "model": str(model or "unknown"),
                        "run_id": run_id,
                        "parent_run_id": parent_run_id,
                        "input_sha256": content_digest(_first(data.get("input"), data.get("messages"))),
                        "output_sha256": content_digest(_first(data.get("output"), data.get("response"))),
                        "source_type": event_name,
                    },
                    "agent-traces",
                )
            )
            continue

        if "tool" in lowered and any(token in lowered for token in ("start", "call", "invoke")):
            arguments = _first(data.get("input"), data.get("arguments"), data.get("args"))
            events.append(
                Event(
                    "tool_call",
                    timestamp,
                    {
                        "tool": _first(data.get("tool"), data.get("name"), record.get("name")),
                        "call_id": _first(data.get("call_id"), data.get("id"), run_id),
                        "arguments_sha256": content_digest(arguments),
                        "run_id": run_id,
                        "parent_run_id": parent_run_id,
                    },
                    "agent-traces",
                )
            )
            continue

        if "tool" in lowered and any(token in lowered for token in ("end", "result", "complete")):
            output = _first(data.get("output"), data.get("result"), data.get("content"))
            events.append(
                Event(
                    "tool_result",
                    timestamp,
                    {
                        "call_id": _first(data.get("call_id"), data.get("id"), run_id),
                        "result_sha256": content_digest(output),
                        "is_error": bool(data.get("error") or data.get("is_error", False)),
                        "run_id": run_id,
                        "parent_run_id": parent_run_id,
                    },
                    "agent-traces",
                )
            )
            continue

        if any(token in lowered for token in ("error", "exception", "failed")):
            error = _first(data.get("error"), data.get("exception"), data.get("message"))
            events.append(
                Event(
                    "runtime_error",
                    timestamp,
                    {
                        "error_sha256": content_digest(error),
                        "run_id": run_id,
                        "parent_run_id": parent_run_id,
                        "source_type": event_name,
                    },
                    "agent-traces",
                )
            )
            continue

        if any(token in lowered for token in ("agent_end", "run_end", "response.completed", "final")):
            output = _first(data.get("output"), data.get("result"), data.get("final_output"))
            events.append(
                Event(
                    "agent_result",
                    timestamp,
                    {
                        "result_sha256": content_digest(output),
                        "run_id": run_id,
                        "parent_run_id": parent_run_id,
                        "source_type": event_name,
                    },
                    "agent-traces",
                )
            )
            continue

        events.append(
            Event(
                "span",
                timestamp,
                {
                    "name": event_name,
                    "record_sha256": content_digest(record),
                    "run_id": run_id,
                    "parent_run_id": parent_run_id,
                },
                "agent-traces",
            )
        )
    return events


def _nested(value: dict[str, Any], *keys: str) -> Any:
    current: Any = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _first(*values: Any) -> Any:
    return next((value for value in values if value not in (None, "")), None)
