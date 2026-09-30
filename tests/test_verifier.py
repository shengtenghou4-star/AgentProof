from agentproof.claims import extract_claims
from agentproof.models import Event, FindingStatus
from agentproof.verifier import verify_claims


def event(event_type, **data):
    return Event(event_type, "2026-01-01T00:00:00Z", data)


def finding_for(text, events):
    claims = extract_claims(text)
    return verify_claims(claims, events)[0]


def test_all_tests_passed_requires_nonzero_clean_run():
    result = finding_for(
        "All tests passed",
        [event("test_summary", total=12, passed=12, failed=0, errors=0, exit_code=0)],
    )
    assert result.status == FindingStatus.VERIFIED


def test_all_tests_passed_detects_failure():
    result = finding_for(
        "All tests passed",
        [event("test_summary", total=12, passed=11, failed=1, errors=0, exit_code=1)],
    )
    assert result.status == FindingStatus.CONTRADICTED


def test_metric_without_independent_recompute_is_partial():
    result = finding_for("AUC reached 0.757", [event("metric", name="auc", value=0.757)])
    assert result.status == FindingStatus.PARTIAL


def test_metric_mismatch_is_contradicted():
    result = finding_for(
        "AUC reached 0.757",
        [event("metric", name="auc", value=0.701, independently_computed=True)],
    )
    assert result.status == FindingStatus.CONTRADICTED


def test_model_routing_is_verified_from_runtime():
    result = finding_for(
        "used openai/gpt-5.6",
        [event("model_call", provider="openai", model="gpt-5.6")],
    )
    assert result.status == FindingStatus.VERIFIED


def test_wrong_model_is_contradicted():
    result = finding_for(
        "used openai/gpt-5.6",
        [event("model_call", provider="other", model="small-model")],
    )
    assert result.status == FindingStatus.CONTRADICTED


def test_artifact_needs_digest_for_full_verification():
    result = finding_for(
        "created model.pkl",
        [event("artifact", path="model.pkl", exists=True)],
    )
    assert result.status == FindingStatus.PARTIAL


def test_failed_healthcheck_contradicts_deployment():
    result = finding_for(
        'AGENTPROOF_CLAIM {"kind":"deployed","expected":{"url":"https://api.example/health"}}',
        [event("healthcheck", url="https://api.example/health", status_code=503)],
    )
    assert result.status == FindingStatus.CONTRADICTED
