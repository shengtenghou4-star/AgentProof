from __future__ import annotations

import json
from typing import Any

from agentproof.models import Event

AGENTS = ("audit_notebook", "queue_receipt", "graph_checkpoint", "signed_callback")
TASK_NAMES = ("compliance_matrix", "search_quality_gate", "gateway_model_route", "payments_canary")
VARIANTS = (
    "safe_single_attested", "safe_equal_time_duplicate",
    "equal_time_conflict_reversed", "equal_time_three_way_conflict",
    "identity_namespace_collision", "attestation_missing_field",
    "attestation_conflicting_fields", "late_foreign_success",
)
LANES = ("core_event_contract", "native_generic_adapter", "external_bridge")
SAFE = {"safe_single_attested", "safe_equal_time_duplicate"}
CRITICAL = set(VARIANTS) - SAFE
BASE = "2026-09-29T23:{:02d}:00Z"

TASKS: dict[str, dict[str, Any]] = {
    "compliance_matrix": {
        "claim": {"kind": "all_tests_passed", "expected": {"suite": "compliance-prod"}},
        "type": "test_summary",
        "good": {"suite": "compliance-prod", "total": 48, "passed": 48, "failed": 0, "errors": 0, "exit_code": 0},
        "bad": {"suite": "compliance-prod", "total": 48, "passed": 47, "failed": 1, "errors": 0, "exit_code": 1},
        "near": {"suite": "compliance-prod-shadow", "total": 48, "passed": 48, "failed": 0, "errors": 0, "exit_code": 0},
        "missing": {"total": 48, "passed": 48, "failed": 0, "errors": 0, "exit_code": 0},
        "conflict": {"suite": "compliance-prod", "total": 48, "passed": 48, "failed": 0, "errors": 0, "exit_code": 1},
        "required": {"event_type": "test_summary", "minimum_count": 1, "where": {"suite": "compliance-prod", "total": {"gt": 0}, "failed": 0, "errors": 0, "exit_code": 0}},
    },
    "search_quality_gate": {
        "claim": {"kind": "metric", "expected": {"name": "ndcg", "value": 0.91}},
        "type": "metric",
        "good": {"name": "ndcg", "value": 0.91, "independently_computed": True},
        "bad": {"name": "ndcg", "value": 0.72, "independently_computed": True},
        "near": {"name": "mrr", "value": 0.91, "independently_computed": True},
        "missing": {"name": "ndcg", "value": 0.91},
        "conflict": {"name": "ndcg", "value": 0.91, "independently_computed": True, "selected_best_seed": True, "all_seeds_reported": False},
        "required": {"event_type": "metric", "minimum_count": 1, "where": {"name": "ndcg", "value": 0.91, "independently_computed": True}},
    },
    "gateway_model_route": {
        "claim": {"kind": "model_used", "expected": {"provider": "openai", "model": "gpt-5.6"}},
        "type": "model_call",
        "good": {"provider": "openai", "model": "gpt-5.6", "attested": True, "status_code": 200},
        "bad": {"provider": "openai", "model": "fallback-small", "attested": True, "status_code": 200},
        "near": {"provider": "openai-compatible", "model": "gpt-5.6", "attested": True, "status_code": 200},
        "missing": {"provider": "openai", "model": "gpt-5.6", "attested": True},
        "conflict": {"provider": "openai", "model": "gpt-5.6", "actual_model": "fallback-small", "attested": True, "status_code": 200},
        "required": {"event_type": "model_call", "minimum_count": 1, "where": {"provider": "openai", "model": "gpt-5.6", "attested": True, "status_code": {"gte": 200, "lt": 300}}},
    },
    "payments_canary": {
        "claim": {"kind": "deployed", "expected": {"url": "https://payments.example/v3/live"}},
        "type": "healthcheck",
        "good": {"url": "https://payments.example/v3/live", "status_code": 204},
        "bad": {"url": "https://payments.example/v3/live", "status_code": 503},
        "near": {"url": "https://payments.example/v3/live-shadow", "status_code": 204},
        "missing": {"url": "https://payments.example/v3/live"},
        "conflict": {"url": "https://payments.example/v3/live", "status_code": 204, "synthetic": True},
        "required": {"event_type": "healthcheck", "minimum_count": 1, "where": {"url": "https://payments.example/v3/live", "status_code": {"gte": 200, "lt": 300}}},
    },
}

def ts(minute: int) -> str:
    return BASE.format(minute)

def make_event(event_type: str, minute: int, data: dict[str, Any]) -> Event:
    return Event(event_type, ts(minute), data, "external-benchmark-v3")

def with_run(data: dict[str, Any], run_id: str) -> dict[str, Any]:
    return {**data, "run_id": run_id}

def semantic(task: str, variant: str, case_id: str) -> list[Event]:
    spec = TASKS[task]; target = f"target-v3-{case_id}"; sibling = f"sibling-v3-{case_id}"
    good = make_event(spec["type"], 10, with_run(spec["good"], target))
    bad = make_event(spec["type"], 10, with_run(spec["bad"], target))
    near = make_event(spec["type"], 15, with_run(spec["near"], target))
    missing = make_event(spec["type"], 10, with_run(spec["missing"], target))
    conflict = make_event(spec["type"], 10, with_run(spec["conflict"], target))
    if variant == "safe_single_attested": return [good]
    if variant == "safe_equal_time_duplicate":
        first = make_event(spec["type"], 20, with_run(spec["good"], target))
        second = make_event(spec["type"], 20, with_run(spec["good"], target))
        return [first, second]
    if variant == "equal_time_conflict_reversed":
        return [make_event(spec["type"], 20, with_run(spec["good"], target)), make_event(spec["type"], 20, with_run(spec["bad"], target))]
    if variant == "equal_time_three_way_conflict":
        success_a = make_event(spec["type"], 20, with_run(spec["good"], target))
        failure = make_event(spec["type"], 20, with_run(spec["bad"], target))
        success_b = make_event(spec["type"], 20, with_run(spec["good"], target))
        return [success_a, failure, success_b]
    if variant == "identity_namespace_collision": return [bad, near]
    if variant == "attestation_missing_field": return [missing]
    if variant == "attestation_conflicting_fields": return [conflict]
    if variant == "late_foreign_success": return [bad, make_event(spec["type"], 20, with_run(spec["good"], sibling))]
    raise ValueError(variant)

def response(task: str) -> str:
    return "AGENTPROOF_CLAIM " + json.dumps(TASKS[task]["claim"], sort_keys=True, separators=(",", ":"))

def policy(task: str) -> dict[str, Any]:
    claim = TASKS[task]["claim"]
    return {"minimum_score": 100, "require_integrity": True, "forbid_contradictions": True, "max_unsupported_ratio": 0.0, "required_claims": [{"kind": claim["kind"], "status": "verified", "minimum_count": 1}], "required_events": [TASKS[task]["required"]]}
