from agentproof.models import AuditReport, Claim, Event, Finding, FindingStatus
from agentproof.policy import evaluate_policy


def report(status=FindingStatus.VERIFIED, *, integrity=True):
    claim = Claim("C1", "all_tests_passed", "All tests passed")
    finding = Finding(claim, status, "reason")
    return AuditReport("run", [finding], 1, integrity, [] if integrity else ["broken"])


def test_policy_passes_strict_evidence():
    events = [
        Event("test_summary", "t", {"total": 10, "passed": 10, "failed": 0, "errors": 0, "exit_code": 0}),
        Event("artifact", "t", {"path": "report.json", "exists": True, "sha256": "abc"}),
    ]
    policy = {
        "minimum_score": 100,
        "max_unsupported_ratio": 0,
        "required_claims": [{"kind": "all_tests_passed", "status": "verified"}],
        "required_events": [
            {"event_type": "test_summary", "where": {"total": {"gt": 0}, "failed": 0, "exit_code": 0}},
            {"event_type": "artifact", "where": {"exists": True}},
        ],
    }
    result = evaluate_policy(report(), events, policy)
    assert result.passed is True


def test_policy_fails_contradiction_and_missing_event():
    policy = {
        "minimum_score": 50,
        "required_events": [{"event_type": "healthcheck", "where": {"status_code": {"gte": 200, "lt": 300}}}],
    }
    result = evaluate_policy(report(FindingStatus.CONTRADICTED), [], policy)
    assert result.passed is False
    assert any(check.name == "no_contradictions" and not check.passed for check in result.checks)
    assert any(check.name == "event:healthcheck" and not check.passed for check in result.checks)


def test_policy_source_filter():
    events = [Event("metric", "t", {"name": "auc", "value": 0.8}, source="runtime")]
    policy = {"required_events": [{"event_type": "metric", "source": "independent"}]}
    result = evaluate_policy(report(), events, policy)
    assert result.passed is False
