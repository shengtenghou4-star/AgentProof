from agentproof.adapters import convert_agent_traces, convert_codex


def test_codex_adapter_normalizes_model_command_and_result():
    events = convert_codex(
        [
            {"type": "turn.started", "model": "gpt-test", "run_id": "r1"},
            {
                "type": "item.completed",
                "data": {
                    "item": {
                        "type": "command_execution",
                        "command": ["pytest"],
                        "exit_code": 0,
                        "aggregated_output": "2 passed",
                    }
                },
            },
            {"type": "response.completed", "data": {"result": "done"}},
        ]
    )
    types = [event.event_type for event in events]
    assert "model_call" in types
    assert "command" in types
    assert "agent_result" in types
    command = next(event for event in events if event.event_type == "command")
    assert command.data["exit_code"] == 0
    assert len(command.data["stdout_sha256"]) == 64


def test_generic_agent_trace_adapter_normalizes_tools_and_errors():
    events = convert_agent_traces(
        [
            {
                "event": "on_chat_model_end",
                "metadata": {"ls_provider": "openai", "ls_model_name": "gpt-test"},
                "data": {"input": ["hello"], "output": "world"},
            },
            {"event": "tool_start", "data": {"name": "shell", "input": {"cmd": "pwd"}}},
            {"event": "tool_end", "data": {"call_id": "c1", "output": "ok"}},
            {"event": "runtime_error", "data": {"error": "boom"}},
        ]
    )
    assert [event.event_type for event in events] == [
        "model_call",
        "tool_call",
        "tool_result",
        "runtime_error",
    ]
    assert events[0].data["model"] == "gpt-test"
