import json

from agentproof.audit import audit_events
from agentproof.models import AuditReport, Claim, Event, Finding, FindingStatus
from agentproof.policy import evaluate_policy
from agentproof.verifier import verify_claims


def event(event_type, timestamp="2026-09-29T23:00:00Z", run_id="target", **data):
    if run_id is not None:
        data = {**data, "run_id": run_id}
    return Event(event_type, timestamp, data, "test-v3")


def structured(kind, expected):
    return "AGENTPROOF_CLAIM " + json.dumps(
        {"kind": kind, "expected": expected}, sort_keys=True
    )


def test_equal_time_conflicting_artifacts_fail_closed():
    claim = Claim("C1", "file_created", "bundle", {"path": "out.json"})
    events = [
        event("artifact", path="out.json", exists=False),
        event("artifact", path="out.json", exists=True, sha256="a" * 64),
    ]
    finding = verify_claims([claim], events)[0]
    assert finding.status == FindingStatus.CONTRADICTED
    assert set(finding.evidence_event_indexes) == {0, 1}


def test_equal_time_equivalent_successes_can_verify():
    claim = Claim("C1", "file_created", "bundle", {"path": "out.json"})
    events = [
        event("artifact", path="out.json", exists=True, sha256="a" * 64),
        event("artifact", path="out.json", exists=True, sha256="a" * 64),
    ]
    finding = verify_claims([claim], events)[0]
    assert finding.status == FindingStatus.VERIFIED


def test_later_timestamp_wins_over_earlier_observation():
    claim = Claim("C1", "file_created", "bundle", {"path": "out.json"})
    events = [
        event(
            "artifact",
            "2026-09-29T23:00:00Z",
            path="out.json",
            exists=True,
            sha256="a" * 64,
        ),
        event(
            "artifact",
            "2026-09-29T23:01:00Z",
            path="out.json",
            exists=False,
        ),
    ]
    finding = verify_claims([claim], events)[0]
    assert finding.status == FindingStatus.CONTRADICTED
    assert finding.evidence_event_indexes == (1,)


def test_policy_cannot_use_success_from_equal_time_conflict():
    claim = Claim("C1", "file_created", "bundle", {"path": "out.json"})
    report = AuditReport(
        "target",
        [Finding(claim, FindingStatus.VERIFIED, "synthetic")],
        2,
        True,
    )
    events = [
        event("artifact", path="out.json", exists=False),
        event("artifact", path="out.json", exists=True, sha256="a" * 64),
    ]
    result = evaluate_policy(
        report,
        events,
        {
            "required_events": [
                {
                    "event_type": "artifact",
                    "where": {"path": "out.json", "exists": True},
                }
            ]
        },
    )
    assert result.passed is False
    assert any(check.name == "event:artifact" and not check.passed for check in result.checks)


def test_attested_model_field_is_observed_route_when_actual_model_absent():
    claim = Claim(
        "C1",
        "model_used",
        "route",
        {"provider": "openai", "model": "gpt-5.6"},
    )
    events = [
        event(
            "model_call",
            provider="openai",
            model="gpt-5.6",
            attested=True,
            status_code=200,
        )
    ]
    finding = verify_claims([claim], events)[0]
    assert finding.status == FindingStatus.VERIFIED


def test_explicit_actual_model_overrides_model_alias_and_conflicts():
    claim = Claim(
        "C1",
        "model_used",
        "route",
        {"provider": "openai", "model": "gpt-5.6"},
    )
    events = [
        event(
            "model_call",
            provider="openai",
            model="gpt-5.6",
            actual_model="fallback-small",
            attested=True,
            status_code=200,
        )
    ]
    finding = verify_claims([claim], events)[0]
    assert finding.status == FindingStatus.CONTRADICTED


def test_attested_model_without_http_status_is_not_verified():
    claim = Claim(
        "C1",
        "model_used",
        "route",
        {"provider": "openai", "model": "gpt-5.6"},
    )
    finding = verify_claims(
        [claim],
        [event("model_call", provider="openai", model="gpt-5.6", attested=True)],
    )[0]
    assert finding.status == FindingStatus.PARTIAL


def test_suite_identity_blocks_shadow_suite_success():
    claim = Claim(
        "C1",
        "all_tests_passed",
        "matrix",
        {"suite": "release-matrix"},
    )
    events = [
        event(
            "test_summary",
            "2026-09-29T23:00:00Z",
            suite="release-matrix",
            total=10,
            passed=9,
            failed=1,
            errors=0,
            exit_code=1,
        ),
        event(
            "test_summary",
            "2026-09-29T23:01:00Z",
            suite="release-matrix-shadow",
            total=10,
            passed=10,
            failed=0,
            errors=0,
            exit_code=0,
        ),
    ]
    finding = verify_claims([claim], events)[0]
    assert finding.status == FindingStatus.CONTRADICTED
    assert finding.evidence_event_indexes == (0,)


def test_suite_identity_verifies_matching_suite():
    report = audit_events(
        [
            event(
                "test_summary",
                suite="release-matrix",
                total=10,
                passed=10,
                failed=0,
                errors=0,
                exit_code=0,
            )
        ],
        structured("all_tests_passed", {"suite": "release-matrix"}),
        run_id="target",
    )
    assert report.findings[0].status == FindingStatus.VERIFIED
