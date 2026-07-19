import json

from agentproof.adapters import convert_claude_code, convert_openai_responses


def test_claude_code_adapter_hashes_content_and_preserves_execution_metadata():
    source = "\n".join(
        [
            json.dumps(
                {
                    "type": "assistant",
                    "session_id": "session-1",
                    "message": {
                        "model": "claude-sonnet-4",
                        "content": [
                            {
                                "type": "tool_use",
                                "id": "tool-1",
                                "name": "Bash",
                                "input": {"command": "pytest -q"},
                            }
                        ],
                    },
                }
            ),
            json.dumps(
                {
                    "type": "user",
                    "session_id": "session-1",
                    "message": {
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": "tool-1",
                                "content": "42 passed",
                                "is_error": False,
                            }
                        ]
                    },
                }
            ),
            json.dumps(
                {
                    "type": "result",
                    "subtype": "success",
                    "session_id": "session-1",
                    "is_error": False,
                    "duration_ms": 100,
                    "num_turns": 2,
                    "result": "done with secret output",
                }
            ),
        ]
    )
    events = convert_claude_code(source)
    assert [event.event_type for event in events] == [
        "model_call",
        "tool_call",
        "tool_result",
        "agent_result",
    ]
    assert events[0].data["model"] == "claude-sonnet-4"
    assert events[1].data["tool"] == "Bash"
    assert "arguments_sha256" in events[1].data
    assert "42 passed" not in json.dumps([event.data for event in events])
    assert "secret output" not in json.dumps([event.data for event in events])


def test_openai_responses_adapter_extracts_model_tools_and_completion():
    source = [
        {
            "type": "response.created",
            "response": {"id": "resp_1", "model": "gpt-5.6", "status": "in_progress"},
        },
        {
            "type": "response.output_item.added",
            "response_id": "resp_1",
            "item": {
                "type": "function_call",
                "id": "item_1",
                "call_id": "call_1",
                "name": "shell",
                "arguments": '{"command":"pytest -q"}',
                "status": "in_progress",
            },
        },
        {
            "type": "response.completed",
            "response": {
                "id": "resp_1",
                "model": "gpt-5.6",
                "status": "completed",
                "output": [{"type": "message", "content": "private"}],
                "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
            },
        },
    ]
    events = convert_openai_responses(source)
    assert [event.event_type for event in events] == [
        "model_call",
        "tool_call",
        "model_call",
        "agent_result",
    ]
    assert events[0].data["provider"] == "openai"
    assert events[0].data["model"] == "gpt-5.6"
    assert events[1].data["tool"] == "shell"
    assert events[-1].data["usage"]["total_tokens"] == 15
    assert "private" not in json.dumps([event.data for event in events])


def test_adapters_reject_non_object_records():
    try:
        convert_claude_code('["not-an-object"]')
    except ValueError as exc:
        assert "object" in str(exc)
    else:
        raise AssertionError("expected invalid transcript to fail")
