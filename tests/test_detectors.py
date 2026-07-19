from agentproof.detectors import scan_anomalies
from agentproof.models import Event, FindingStatus


def kinds(events):
    return {finding.claim.kind: finding for finding in scan_anomalies(events)}


def test_detects_grader_tampering_and_hidden_failure():
    findings = kinds([
        Event("file_change", "t", {"path": "tests/test_api.py", "operation": "modified", "controlled_by": "agent"}),
        Event("command", "t", {"exit_code": 1, "hidden_from_summary": True}),
    ])
    assert findings["grader_tampering"].status == FindingStatus.CONTRADICTED
    assert findings["hidden_failure"].status == FindingStatus.CONTRADICTED


def test_detects_evaluation_gaming():
    findings = kinds([
        Event("metric", "t", {"selected_best_seed": True, "all_seeds_reported": False}),
        Event("data_access", "t", {"future_data": True}),
        Event("acceptance_change", "t", {"actor": "agent", "authorized": False}),
    ])
    assert {"seed_cherry_picking", "data_leakage", "acceptance_criteria_changed"} <= findings.keys()


def test_does_not_flag_authorized_or_normal_activity():
    findings = scan_anomalies([
        Event("file_change", "t", {"path": "src/app.py", "operation": "modified", "controlled_by": "agent"}),
        Event("acceptance_change", "t", {"actor": "human", "authorized": True}),
        Event("command", "t", {"exit_code": 1, "hidden_from_summary": False}),
    ])
    assert findings == []
