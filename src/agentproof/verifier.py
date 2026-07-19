from __future__ import annotations

from math import isclose

from .models import Claim, Event, Finding, FindingStatus


def verify_claims(claims: list[Claim], events: list[Event]) -> list[Finding]:
    return [_verify_one(claim, events) for claim in claims]


def _verify_one(claim: Claim, events: list[Event]) -> Finding:
    if claim.kind == "all_tests_passed":
        return _verify_tests(claim, events)
    if claim.kind == "metric":
        return _verify_metric(claim, events)
    if claim.kind == "model_used":
        return _verify_model(claim, events)
    if claim.kind == "file_created":
        return _verify_file(claim, events)
    if claim.kind == "deployed":
        return _verify_deployment(claim, events)
    if claim.kind == "completed":
        return _verify_completion(claim, events)
    return Finding(claim, FindingStatus.UNSUPPORTED, "No verifier exists for this claim type")


def _indexes(events: list[Event], event_type: str) -> list[int]:
    return [i for i, event in enumerate(events) if event.event_type == event_type]


def _verify_tests(claim: Claim, events: list[Event]) -> Finding:
    indexes = _indexes(events, "test_summary")
    if not indexes:
        return Finding(claim, FindingStatus.UNSUPPORTED, "No test_summary event was recorded")
    latest = events[indexes[-1]].data
    failed = int(latest.get("failed", 0))
    errors = int(latest.get("errors", 0))
    exit_code = latest.get("exit_code")
    total = int(latest.get("total", latest.get("passed", 0) + failed + errors))
    if total == 0:
        return Finding(claim, FindingStatus.UNSUPPORTED, "A zero-test run cannot prove all tests passed", (indexes[-1],))
    if failed == 0 and errors == 0 and exit_code == 0:
        return Finding(claim, FindingStatus.VERIFIED, f"{total} tests passed with exit code 0", (indexes[-1],))
    return Finding(
        claim,
        FindingStatus.CONTRADICTED,
        f"Recorded test run has failed={failed}, errors={errors}, exit_code={exit_code}",
        (indexes[-1],),
    )


def _verify_metric(claim: Claim, events: list[Event]) -> Finding:
    expected_name = str(claim.expected["name"]).lower()
    expected_value = float(claim.expected["value"])
    candidates: list[tuple[int, Event]] = []
    for index, event in enumerate(events):
        if event.event_type != "metric":
            continue
        actual_name = str(event.data.get("name", "")).lower().replace("roc-auc", "auc")
        if actual_name == expected_name:
            candidates.append((index, event))
    if not candidates:
        return Finding(claim, FindingStatus.UNSUPPORTED, f"No metric event for {expected_name}")
    index, event = candidates[-1]
    actual = float(event.data["value"])
    independently_computed = bool(event.data.get("independently_computed", False))
    if not isclose(actual, expected_value, rel_tol=1e-4, abs_tol=1e-4):
        return Finding(
            claim,
            FindingStatus.CONTRADICTED,
            f"Claimed {expected_value:.4f}, recorded {actual:.4f}",
            (index,),
        )
    status = FindingStatus.VERIFIED if independently_computed else FindingStatus.PARTIAL
    reason = "Metric matched an independent recomputation" if independently_computed else "Metric matched, but no independent recomputation was recorded"
    return Finding(claim, status, reason, (index,))


def _verify_model(claim: Claim, events: list[Event]) -> Finding:
    indexes = _indexes(events, "model_call")
    expected_model = str(claim.expected.get("model", "")).lower()
    expected_provider = claim.expected.get("provider")
    for index in reversed(indexes):
        data = events[index].data
        model_matches = str(data.get("model", "")).lower() == expected_model
        provider_matches = not expected_provider or str(data.get("provider", "")).lower() == str(expected_provider).lower()
        if model_matches and provider_matches:
            return Finding(claim, FindingStatus.VERIFIED, "Runtime model_call matched the claimed provider/model", (index,))
    if indexes:
        seen = [f"{events[i].data.get('provider')}/{events[i].data.get('model')}" for i in indexes]
        return Finding(claim, FindingStatus.CONTRADICTED, f"Observed model calls were: {', '.join(seen)}", tuple(indexes))
    return Finding(claim, FindingStatus.UNSUPPORTED, "No model_call event was recorded")


def _verify_file(claim: Claim, events: list[Event]) -> Finding:
    expected_path = str(claim.expected["path"])
    for index, event in enumerate(events):
        if event.event_type != "artifact":
            continue
        if event.data.get("path") == expected_path:
            exists = bool(event.data.get("exists", False))
            digest = event.data.get("sha256")
            if exists and digest:
                return Finding(claim, FindingStatus.VERIFIED, "Artifact exists and has a recorded SHA-256 digest", (index,))
            if exists:
                return Finding(claim, FindingStatus.PARTIAL, "Artifact exists but has no integrity digest", (index,))
            return Finding(claim, FindingStatus.CONTRADICTED, "Artifact event reports that the file does not exist", (index,))
    return Finding(claim, FindingStatus.UNSUPPORTED, f"No artifact event for {expected_path}")


def _verify_deployment(claim: Claim, events: list[Event]) -> Finding:
    indexes = _indexes(events, "healthcheck")
    if not indexes:
        return Finding(claim, FindingStatus.UNSUPPORTED, "No deployment healthcheck was recorded")
    index = indexes[-1]
    status_code = int(events[index].data.get("status_code", 0))
    if 200 <= status_code < 300:
        return Finding(claim, FindingStatus.VERIFIED, f"Healthcheck returned HTTP {status_code}", (index,))
    return Finding(claim, FindingStatus.CONTRADICTED, f"Healthcheck returned HTTP {status_code}", (index,))


def _verify_completion(claim: Claim, events: list[Event]) -> Finding:
    evidence_types = {"command", "tool_call", "artifact", "test_summary", "metric", "healthcheck"}
    indexes = [i for i, event in enumerate(events) if event.event_type in evidence_types]
    if len(indexes) >= 2:
        return Finding(claim, FindingStatus.PARTIAL, "Execution evidence exists, but completion criteria were not explicitly defined", tuple(indexes))
    return Finding(claim, FindingStatus.UNSUPPORTED, "Insufficient execution evidence to support full completion", tuple(indexes))
