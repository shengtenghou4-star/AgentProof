from agentproof.adapters import convert_otlp_json


def attr(key, value):
    return {"key": key, "value": {"stringValue": value}}


def test_converts_model_span():
    payload = {
        "resourceSpans": [
            {
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "name": "chat",
                                "traceId": "trace",
                                "spanId": "span",
                                "startTimeUnixNano": "1000000000",
                                "attributes": [
                                    attr("gen_ai.provider.name", "openai"),
                                    attr("gen_ai.request.model", "gpt-5.6"),
                                ],
                            }
                        ]
                    }
                ]
            }
        ]
    }
    event = convert_otlp_json(payload)[0]
    assert event.event_type == "model_call"
    assert event.data["provider"] == "openai"
    assert event.data["model"] == "gpt-5.6"
    assert event.source == "otel"


def test_converts_tool_span_and_keeps_unknown_span():
    payload = {
        "spans": [
            {"name": "tool.execute", "attributes": {"tool.name": "shell", "tool.arguments": "pytest"}},
            {"name": "planning", "attributes": {"custom": 1}},
        ]
    }
    events = convert_otlp_json(payload)
    assert [event.event_type for event in events] == ["tool_call", "span"]
    assert events[0].data["tool"] == "shell"
