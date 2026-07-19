import json

from agentproof.aggregate import aggregate_reports


def write_report(path, run_id, score, statuses, integrity=True):
    findings = [
        {
            "claim": {"claim_id": f"C{index}", "kind": kind, "text": kind, "expected": {}},
            "status": status,
            "reason": "reason",
            "evidence_event_indexes": [],
            "confidence": 1.0,
        }
        for index, (kind, status) in enumerate(statuses, start=1)
    ]
    path.write_text(json.dumps({"run_id": run_id, "score": score, "integrity_ok": integrity, "findings": findings}), encoding="utf-8")


def test_aggregate_reports(tmp_path):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    write_report(first, "agent-a", 100, [("metric", "verified"), ("deployed", "verified")])
    write_report(second, "agent-b", 50, [("metric", "verified"), ("deployed", "contradicted")], integrity=False)

    result = aggregate_reports([first, second])

    assert result["runs"] == 2
    assert result["score"]["mean"] == 75
    assert result["integrity_pass_rate"] == 0.5
    assert result["contradiction_rate"] == 0.25
    assert result["by_kind"]["metric"]["verified_rate"] == 1.0
    assert result["contradictions"][0]["run_id"] == "agent-b"
