import json

from agentproof.audit import audit_run


def test_end_to_end_audit(tmp_path):
    trace = tmp_path / "trace.jsonl"
    rows = [
        {"event_type": "test_summary", "timestamp": "t1", "data": {"total": 2, "passed": 2, "failed": 0, "errors": 0, "exit_code": 0}},
        {"event_type": "metric", "timestamp": "t2", "data": {"name": "auc", "value": 0.8, "independently_computed": True}},
    ]
    trace.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    report = audit_run(trace, "All tests passed. AUC is 0.8.", run_id="test")
    assert report.score == 100.0
    assert report.integrity_ok
    assert report.verified_count == 2
