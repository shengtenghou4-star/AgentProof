from agentproof.integrity import verify_hash_chain
from agentproof.io import load_events
from agentproof.recorder import TraceRecorder, parse_pytest_summary


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


def test_pytest_summary_parser():
    summary = parse_pytest_summary(
        "2 failed, 41 passed, 3 skipped, 1 xfailed in 2.3s",
        exit_code=1,
    )
    assert summary == {
        "total": 47,
        "passed": 41,
        "failed": 2,
        "errors": 0,
        "skipped": 3,
        "xfailed": 1,
        "xpassed": 0,
        "exit_code": 1,
    }


def test_recorder_emits_test_summary_from_command_output(tmp_path):
    trace = tmp_path / "trace.jsonl"
    result = TraceRecorder(trace).run_command(
        ["python", "-c", "print('35 passed, 2 skipped in 0.10s')"]
    )
    assert result.returncode == 0
    events = load_events(trace)
    assert [event.event_type for event in events] == ["command", "test_summary"]
    assert events[1].data["passed"] == 35
    assert events[1].data["skipped"] == 2
    assert events[1].data["total"] == 37
