from __future__ import annotations

from typing import Any, Iterable

from ..models import Event
from .common import content_digest, parse_json_records, utc_timestamp


def convert_codex(
    source: str | bytes | Iterable[dict[str, Any]],
) -> list[Event]:
    """Normalize common Codex JSON/JSONL transcript records.

    The adapter intentionally accepts a small family of field aliases because Codex
    exports and wrappers differ. Content and command output are hashed rather than
    copied into the evidence trace.
    """

    events: list[Event] = []
    for record in parse_json_records(source):
        record_type = str(record.get("type") or record.get("event") or "unknown")
        timestamp = utc_timestamp(record.get("timestamp") or record.get("created_at"))
        payload = _payload(record)
        model = _first(record.get("model"), payload.get("model"), _nested(payload, "response", "model"))
        provider = _first(record.get("provider"), payload.get("provider"), "openai")
        run_id = _first(record.get("run_id"), record.get("thread_id"), payload.get("run_id"))

        if model:
            events.append(
                Event(
                    "model_call",
                    timestamp,
                    {
                        "provider": str(provider),
                        "model": str(model),
                        "run_id": run_id,
                        "source_type": record_type,
                    },
                    "codex",
                )
            )

        item = payload.get("item") if isinstance(payload.get("item"), dict) else payload
        item_type = str(item.get("type") or payload.get("item_type") or "")
        if item_type in {"command_execution", "command", "shell", "shell_command"}:
            command = _first(item.get("command"), item.get("argv"), item.get("cmd"))
            exit_code = _first(item.get("exit_code"), item.get("returncode"), item.get("status_code"))
            output = _first(item.get("aggregated_output"), item.get("output"), item.get("stdout"))
            error = item.get("stderr")
            events.append(
                Event(
                    "command",
                    timestamp,
                    {
                        "command": command,
                        "exit_code": int(exit_code) if exit_code is not None else None,
                        "stdout_sha256": content_digest(output) if output is not None else None,
                        "stderr_sha256": content_digest(error) if error is not None else None,
                        "status": item.get("status"),
                        "run_id": run_id,
                    },
                    "codex",
                )
            )
            continue

        if item_type in {"function_call", "tool_call", "mcp_tool_call"}:
            arguments = _first(item.get("arguments"), item.get("input"), item.get("params"))
            events.append(
                Event(
                    "tool_call",
                    timestamp,
                    {
                        "tool": _first(item.get("name"), item.get("tool"), item.get("server")),
                        "call_id": _first(item.get("id"), item.get("call_id")),
                        "arguments_sha256": content_digest(arguments),
                        "status": item.get("status"),
                        "run_id": run_id,
                    },
                    "codex",
                )
            )
            result = _first(item.get("result"), item.get("output"))
            if result is not None:
                events.append(
                    Event(
                        "tool_result",
                        timestamp,
                        {
                            "call_id": _first(item.get("id"), item.get("call_id")),
                            "result_sha256": content_digest(result),
                            "is_error": bool(item.get("is_error", False)),
                            "run_id": run_id,
                        },
                        "codex",
                    )
                )
            continue

        if item_type in {"message", "agent_message", "reasoning"} or record_type in {
            "response.completed",
            "turn.completed",
            "result",
        }:
            content = _first(item.get("content"), payload.get("content"), payload.get("result"))
            events.append(
                Event(
                    "agent_result",
                    timestamp,
                    {
                        "status": _first(item.get("status"), payload.get("status")),
                        "content_sha256": content_digest(content),
                        "run_id": run_id,
                        "source_type": record_type,
                    },
                    "codex",
                )
            )
            continue

        events.append(
            Event(
                "span",
                timestamp,
                {
                    "name": record_type,
                    "record_sha256": content_digest(record),
                    "run_id": run_id,
                },
                "codex",
            )
        )
    return events


def _payload(record: dict[str, Any]) -> dict[str, Any]:
    for key in ("data", "payload", "response"):
        value = record.get(key)
        if isinstance(value, dict):
            return value
    return record


def _nested(value: dict[str, Any], *keys: str) -> Any:
    current: Any = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _first(*values: Any) -> Any:
    return next((value for value in values if value not in (None, "")), None)
