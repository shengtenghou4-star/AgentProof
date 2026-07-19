from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from ..models import Event


def convert_otlp_json(payload: dict[str, Any]) -> list[Event]:
    """Convert common OTLP/JSON span shapes into AgentProof events.

    The adapter accepts both the standard ``resourceSpans`` envelope and a flat
    ``spans`` list, keeping unknown spans as generic ``span`` evidence.
    """

    return [_convert_span(span) for span in _iter_spans(payload)]


def _iter_spans(payload: dict[str, Any]) -> Iterable[dict[str, Any]]:
    flat = payload.get("spans")
    if isinstance(flat, list):
        yield from (span for span in flat if isinstance(span, dict))
    resources = payload.get("resourceSpans", [])
    if not isinstance(resources, list):
        return
    for resource in resources:
        if not isinstance(resource, dict):
            continue
        scopes = resource.get("scopeSpans") or resource.get("instrumentationLibrarySpans") or []
        if not isinstance(scopes, list):
            continue
        for scope in scopes:
            if not isinstance(scope, dict):
                continue
            spans = scope.get("spans", [])
            if isinstance(spans, list):
                yield from (span for span in spans if isinstance(span, dict))


def _convert_span(span: dict[str, Any]) -> Event:
    attributes = _attributes(span.get("attributes", []))
    name = str(span.get("name", "unnamed-span"))
    timestamp = _timestamp(span.get("startTimeUnixNano") or span.get("start_time"))

    model = _first(attributes, "gen_ai.request.model", "gen_ai.response.model", "llm.request.model")
    provider = _first(attributes, "gen_ai.provider.name", "gen_ai.system", "llm.provider")
    if model:
        return Event(
            "model_call",
            timestamp,
            {
                "provider": provider,
                "model": model,
                "request_id": _first(attributes, "gen_ai.response.id", "request.id"),
                "span_name": name,
                "trace_id": span.get("traceId") or span.get("trace_id"),
                "span_id": span.get("spanId") or span.get("span_id"),
            },
            "otel",
        )

    tool_name = _first(attributes, "gen_ai.tool.name", "tool.name")
    if tool_name or name.startswith("tool"):
        return Event(
            "tool_call",
            timestamp,
            {
                "tool": tool_name or name,
                "arguments": _first(attributes, "gen_ai.tool.call.arguments", "tool.arguments"),
                "result": _first(attributes, "gen_ai.tool.call.result", "tool.result"),
                "status": _status(span),
                "trace_id": span.get("traceId") or span.get("trace_id"),
                "span_id": span.get("spanId") or span.get("span_id"),
            },
            "otel",
        )

    return Event(
        "span",
        timestamp,
        {
            "name": name,
            "attributes": attributes,
            "status": _status(span),
            "trace_id": span.get("traceId") or span.get("trace_id"),
            "span_id": span.get("spanId") or span.get("span_id"),
        },
        "otel",
    )


def _attributes(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    output: dict[str, Any] = {}
    if not isinstance(raw, list):
        return output
    for item in raw:
        if not isinstance(item, dict) or "key" not in item:
            continue
        output[str(item["key"])] = _otel_value(item.get("value"))
    return output


def _otel_value(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    for key in ("stringValue", "intValue", "doubleValue", "boolValue", "bytesValue"):
        if key in value:
            return value[key]
    if "arrayValue" in value:
        values = value["arrayValue"].get("values", []) if isinstance(value["arrayValue"], dict) else []
        return [_otel_value(item) for item in values]
    if "kvlistValue" in value:
        values = value["kvlistValue"].get("values", []) if isinstance(value["kvlistValue"], dict) else []
        return _attributes(values)
    return value


def _first(attributes: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if attributes.get(key) not in (None, ""):
            return attributes[key]
    return None


def _status(span: dict[str, Any]) -> str | None:
    status = span.get("status")
    if not isinstance(status, dict):
        return None
    return str(status.get("code") or status.get("message") or "") or None


def _timestamp(raw: Any) -> str:
    if raw is None:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(raw, str) and not raw.isdigit():
        return raw
    try:
        nanoseconds = int(raw)
    except (TypeError, ValueError):
        return str(raw)
    return datetime.fromtimestamp(nanoseconds / 1_000_000_000, tz=timezone.utc).isoformat().replace("+00:00", "Z")
