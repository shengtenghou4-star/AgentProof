from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .evidence import bind_events_to_run, explicit_run_ids, terminal_events
from .models import AuditReport, Event, FindingStatus


@dataclass(frozen=True)
class PolicyCheck:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class PolicyResult:
    passed: bool
    checks: list[PolicyCheck]

    def to_dict(self) -> dict[str, Any]:
        return {"passed": self.passed, "checks": [asdict(check) for check in self.checks]}


def load_policy(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("policy must be a JSON object")
    return payload


def evaluate_policy(report: AuditReport, events: list[Event], policy: dict[str, Any]) -> PolicyResult:
    checks: list[PolicyCheck] = []
    run_ids = explicit_run_ids(events)
    scoped_events = bind_events_to_run(events, report.run_id)
    effective_events = terminal_events(scoped_events)

    if run_ids:
        checks.append(
            PolicyCheck(
                "run_scope",
                bool(scoped_events),
                f"target_run={report.run_id}, scoped_events={len(scoped_events)}, observed_runs={len(run_ids)}",
            )
        )

    minimum_score = float(policy.get("minimum_score", 0))
    checks.append(PolicyCheck("minimum_score", report.score >= minimum_score, f"score={report.score}, required>={minimum_score}"))

    if bool(policy.get("require_integrity", True)):
        checks.append(PolicyCheck("trace_integrity", report.integrity_ok, "hash chain valid" if report.integrity_ok else "; ".join(report.integrity_errors)))

    if bool(policy.get("forbid_contradictions", True)):
        count = sum(finding.status == FindingStatus.CONTRADICTED for finding in report.findings)
        checks.append(PolicyCheck("no_contradictions", count == 0, f"contradicted_findings={count}"))

    max_unsupported_ratio = float(policy.get("max_unsupported_ratio", 1.0))
    unsupported = sum(finding.status == FindingStatus.UNSUPPORTED for finding in report.findings)
    ratio = unsupported / len(report.findings) if report.findings else 1.0
    checks.append(PolicyCheck("unsupported_ratio", ratio <= max_unsupported_ratio, f"ratio={ratio:.4f}, maximum={max_unsupported_ratio:.4f}"))

    for index, requirement in enumerate(policy.get("required_claims", [])):
        checks.append(_check_claim_requirement(report, requirement, index))

    for index, requirement in enumerate(policy.get("required_events", [])):
        checks.append(_check_event_requirement(effective_events, requirement, index))

    return PolicyResult(passed=all(check.passed for check in checks), checks=checks)


def _check_claim_requirement(report: AuditReport, requirement: Any, index: int) -> PolicyCheck:
    if not isinstance(requirement, dict) or not isinstance(requirement.get("kind"), str):
        return PolicyCheck(f"required_claims[{index}]", False, "invalid claim requirement")
    kind = requirement["kind"]
    required_status = str(requirement.get("status", "verified"))
    minimum_count = int(requirement.get("minimum_count", 1))
    matching = [finding for finding in report.findings if finding.claim.kind == kind and finding.status.value == required_status]
    return PolicyCheck(
        f"claim:{kind}:{required_status}",
        len(matching) >= minimum_count,
        f"matched={len(matching)}, required>={minimum_count}",
    )


def _check_event_requirement(events: list[Event], requirement: Any, index: int) -> PolicyCheck:
    if not isinstance(requirement, dict) or not isinstance(requirement.get("event_type"), str):
        return PolicyCheck(f"required_events[{index}]", False, "invalid event requirement")
    event_type = requirement["event_type"]
    minimum_count = int(requirement.get("minimum_count", 1))
    source = requirement.get("source")
    where = requirement.get("where", {})
    if not isinstance(where, dict):
        return PolicyCheck(f"event:{event_type}", False, "where must be an object")
    matching = [
        event
        for event in events
        if event.event_type == event_type
        and (source is None or event.source == source)
        and all(_condition_matches(event.data.get(field), condition) for field, condition in where.items())
    ]
    return PolicyCheck(
        f"event:{event_type}",
        len(matching) >= minimum_count,
        f"matched={len(matching)}, required>={minimum_count}, source={source or '*'}",
    )


def _condition_matches(actual: Any, condition: Any) -> bool:
    if not isinstance(condition, dict):
        return actual == condition
    operations = {
        "eq": lambda expected: actual == expected,
        "ne": lambda expected: actual != expected,
        "gte": lambda expected: _compare(actual, expected, lambda left, right: left >= right),
        "gt": lambda expected: _compare(actual, expected, lambda left, right: left > right),
        "lte": lambda expected: _compare(actual, expected, lambda left, right: left <= right),
        "lt": lambda expected: _compare(actual, expected, lambda left, right: left < right),
        "in": lambda expected: actual in expected if isinstance(expected, list) else False,
    }
    return all(operation in operations and operations[operation](expected) for operation, expected in condition.items())


def _compare(actual: Any, expected: Any, comparator) -> bool:
    try:
        return bool(comparator(float(actual), float(expected)))
    except (TypeError, ValueError):
        return False
