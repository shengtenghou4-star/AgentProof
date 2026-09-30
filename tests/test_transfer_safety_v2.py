import json

from agentproof.audit import audit_events
from agentproof.models import AuditReport, Claim, Event, Finding, FindingStatus
from agentproof.policy import evaluate_policy
from agentproof.verifier import verify_claims


def event(event_type, n=0, run_id=None, **data):
    if run_id is not None:
        data = {**data, "run_id": run_id}
    return Event(event_type, f"2026-09-29T20:{n:02d}:00Z", data, "test")


def structured(kind, expected):
    return "AGENTPROOF_CLAIM " + json.dumps({"kind": kind, "expected": expected}, sort_keys=True)


def test_audit_binds_claim_evidence_to_target_run():
    events = [
        event("check_result", 1, "target", name="ready", exit_code=2, passed=False),
        event("check_result", 2, "sibling", name="ready", exit_code=0, passed=True),
    ]
    report = audit_events(events, structured("check_succeeded", {"name": "ready", "exit_code": 0}), run_id="target")
    assert report.findings[0].status == FindingStatus.CONTRADICTED
    assert report.event_count == 1


def test_policy_does_not_borrow_required_event_from_sibling_run():
    claim = Claim("C1", "check_succeeded", "ready", {"name": "ready", "exit_code": 0})
    report = AuditReport("target", [Finding(claim, FindingStatus.VERIFIED, "synthetic")], 1, True)
    events = [event("check_result", 1, "sibling", name="ready", exit_code=0, passed=True)]
    policy = {"required_events": [{"event_type": "check_result", "where": {"name": "ready", "exit_code": 0, "passed": True}}]}
    result = evaluate_policy(report, events, policy)
    assert result.passed is False
    assert any(check.name == "run_scope" and not check.passed for check in result.checks)


def test_file_verifier_uses_terminal_state():
    claim = Claim("C1", "file_created", "file", {"path": "out.pdf"})
    events = [
        event("artifact", 1, "target", path="out.pdf", exists=True, sha256="a" * 64),
        event("artifact", 2, "target", path="out.pdf", exists=False),
    ]
    result = verify_claims([claim], events)[0]
    assert result.status == FindingStatus.CONTRADICTED
    assert result.evidence_event_indexes == (1,)


def test_policy_required_event_uses_terminal_state():
    claim = Claim("C1", "file_created", "file", {"path": "out.pdf"})
    report = AuditReport("target", [Finding(claim, FindingStatus.VERIFIED, "synthetic")], 2, True)
    events = [
        event("artifact", 1, "target", path="out.pdf", exists=True, sha256="a" * 64),
        event("artifact", 2, "target", path="out.pdf", exists=False),
    ]
    policy = {"required_events": [{"event_type": "artifact", "where": {"path": "out.pdf", "exists": True}}]}
    result = evaluate_policy(report, events, policy)
    assert result.passed is False
    assert any(check.name == "event:artifact" and not check.passed for check in result.checks)


def test_deployment_verifier_requires_target_url():
    claim = Claim("C1", "deployed", "deployed", {"url": "https://prod.example/health"})
    result = verify_claims([claim], [event("healthcheck", 1, "target", url="https://staging.example/health", status_code=200)])[0]
    assert result.status == FindingStatus.UNSUPPORTED


def test_deployment_without_url_fails_closed():
    claim = Claim("C1", "deployed", "deployed", {})
    result = verify_claims([claim], [event("healthcheck", 1, "target", url="https://prod.example/health", status_code=200)])[0]
    assert result.status == FindingStatus.UNSUPPORTED


def test_deployment_terminal_failure_overrides_earlier_success():
    claim = Claim("C1", "deployed", "deployed", {"url": "https://prod.example/health"})
    events = [
        event("healthcheck", 1, "target", url="https://prod.example/health", status_code=200),
        event("healthcheck", 2, "target", url="https://prod.example/health", status_code=503),
    ]
    result = verify_claims([claim], events)[0]
    assert result.status == FindingStatus.CONTRADICTED


def test_model_terminal_route_overrides_earlier_success():
    claim = Claim("C1", "model_used", "model", {"provider": "openai", "model": "gpt-5.6"})
    events = [
        event("model_call", 1, "target", provider="openai", model="gpt-5.6"),
        event("model_call", 2, "target", provider="openai", model="small-model"),
    ]
    result = verify_claims([claim], events)[0]
    assert result.status == FindingStatus.CONTRADICTED
