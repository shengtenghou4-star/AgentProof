from agentproof.integrity import verify_hash_chain
from agentproof.io import load_events
from agentproof.recorder import TraceRecorder


def test_recorder_builds_valid_hash_chain(tmp_path):
    trace = tmp_path / "trace.jsonl"
    recorder = TraceRecorder(trace)
    recorder.emit("tool_call", tool="example")
    recorder.record_metric("auc", 0.8, independently_computed=True)
    ok, errors = verify_hash_chain(load_events(trace))
    assert ok
    assert errors == []


def test_recorder_captures_command(tmp_path):
    trace = tmp_path / "trace.jsonl"
    result = TraceRecorder(trace).run_command(["python", "-c", "print('ok')"])
    assert result.returncode == 0
    event = load_events(trace)[0]
    assert event.event_type == "command"
    assert event.data["stdout"].strip() == "ok"
