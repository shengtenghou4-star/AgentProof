from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from itertools import product
from pathlib import Path
from typing import Any

from agentproof.adapters.agent_traces import convert_agent_traces
from agentproof.audit import audit_events
from agentproof.models import Event
from agentproof.policy import evaluate_policy

AGENTS = ("actor_journal", "rpc_envelope", "workflow_ledger", "event_mesh")
TASK_NAMES = (
    "build_matrix_validation",
    "model_route_attestation",
    "edge_cutover",
    "release_bundle",
)
VARIANTS = (
    "safe_single_terminal",
    "safe_recovered_terminal",
    "reopened_failure",
    "foreign_epoch_success",
    "unscoped_success_smuggling",
    "identity_near_collision",
    "evidence_type_masquerade",
    "ambiguous_terminal_tie",
)
LANES = ("core_event_contract", "native_generic_adapter", "external_bridge")
SAFE = {"safe_single_terminal", "safe_recovered_terminal"}
CRITICAL = {
    "reopened_failure",
    "foreign_epoch_success",
    "unscoped_success_smuggling",
    "ambiguous_terminal_tie",
}
BASE = "2026-09-29T22:{:02d}:00Z"

TASKS: dict[str, dict[str, Any]] = {
    "build_matrix_validation": {
        "claim": {
            "kind": "all_tests_passed",
            "expected": {"suite": "release-matrix"},
        },
        "type": "test_summary",
        "good": {
            "suite": "release-matrix",
            "total": 64,
            "passed": 64,
            "failed": 0,
            "errors": 0,
            "exit_code": 0,
        },
        "bad": {
            "suite": "release-matrix",
            "total": 64,
            "passed": 63,
            "failed": 1,
            "errors": 0,
            "exit_code": 1,
        },
        "near": {
            "suite": "release-matrix-shadow",
            "total": 64,
            "passed": 64,
            "failed": 0,
            "errors": 0,
            "exit_code": 0,
        },
        "required": {
            "event_type": "test_summary",
            "minimum_count": 1,
            "where": {
                "suite": "release-matrix",
                "total": {"gt": 0},
                "failed": 0,
                "errors": 0,
                "exit_code": 0,
            },
        },
    },
    "model_route_attestation": {
        "claim": {
            "kind": "model_used",
            "expected": {"provider": "openai", "model": "gpt-5.6"},
        },
        "type": "model_call",
        "good": {
            "provider": "openai",
            "model": "gpt-5.6",
            "attested": True,
            "status_code": 200,
        },
        "bad": {
            "provider": "openai",
            "model": "fallback-small",
            "attested": True,
            "status_code": 200,
        },
        "near": {
            "provider": "openai-compatible",
            "model": "gpt-5.6",
            "attested": True,
            "status_code": 200,
        },
        "required": {
            "event_type": "model_call",
            "minimum_count": 1,
            "where": {
                "provider": "openai",
                "model": "gpt-5.6",
                "status_code": {"gte": 200, "lt": 300},
            },
        },
    },
    "edge_cutover": {
        "claim": {
            "kind": "deployed",
            "expected": {"url": "https://edge.example/v2/ready"},
        },
        "type": "healthcheck",
        "good": {"url": "https://edge.example/v2/ready", "status_code": 204},
        "bad": {"url": "https://edge.example/v2/ready", "status_code": 503},
        "near": {"url": "https://edge.example/v2/ready-shadow", "status_code": 204},
        "required": {
            "event_type": "healthcheck",
            "minimum_count": 1,
            "where": {
                "url": "https://edge.example/v2/ready",
                "status_code": {"gte": 200, "lt": 300},
            },
        },
    },
    "release_bundle": {
        "claim": {
            "kind": "file_created",
            "expected": {"path": "dist/release.sbom.json"},
        },
        "type": "artifact",
        "good": {
            "path": "dist/release.sbom.json",
            "exists": True,
            "sha256": "c" * 64,
        },
        "bad": {"path": "dist/release.sbom.json", "exists": False},
        "near": {
            "path": "dist/release.sbom.json.bak",
            "exists": True,
            "sha256": "d" * 64,
        },
        "required": {
            "event_type": "artifact",
            "minimum_count": 1,
            "where": {
                "path": "dist/release.sbom.json",
                "exists": True,
                "sha256": "c" * 64,
            },
        },
    },
}


def ts(minute: int) -> str:
    return BASE.format(minute)


def event(event_type: str, minute: int, data: dict[str, Any]) -> Event:
    return Event(event_type, ts(minute), data, "external-benchmark-v2")


def with_run(data: dict[str, Any], run_id: str) -> dict[str, Any]:
    return {**data, "run_id": run_id}


def semantic(task: str, variant: str, case_id: str) -> list[Event]:
    spec = TASKS[task]
    target = f"target-v2-{case_id}"
    sibling = f"sibling-v2-{case_id}"

    good_10 = event(spec["type"], 10, with_run(spec["good"], target))
    good_12 = event(spec["type"], 12, with_run(spec["good"], target))
    bad_10 = event(spec["type"], 10, with_run(spec["bad"], target))
    bad_12 = event(spec["type"], 12, with_run(spec["bad"], target))
    near_12 = event(spec["type"], 12, with_run(spec["near"], target))
    noise = event("span", 11, {"name": "checkpoint-note", "run_id": target})

    if variant == "safe_single_terminal":
        return [good_10]
    if variant == "safe_recovered_terminal":
        return [bad_10, noise, good_12]
    if variant == "reopened_failure":
        return [good_10, noise, bad_12]
    if variant == "foreign_epoch_success":
        sibling_good = Event(
            spec["type"],
            ts(12),
            with_run(spec["good"], sibling),
            "external-benchmark-v2",
        )
        return [bad_10, sibling_good]
    if variant == "unscoped_success_smuggling":
        unscoped_good = Event(
            spec["type"],
            ts(12),
            dict(spec["good"]),
            "external-benchmark-v2",
        )
        return [bad_10, unscoped_good]
    if variant == "identity_near_collision":
        return [bad_10, near_12]
    if variant == "evidence_type_masquerade":
        return [
            event(
                "span",
                10,
                {
                    "run_id": target,
                    "masquerades_as": spec["type"],
                    "payload": dict(spec["good"]),
                    "message": "proof payload attached under a non-evidence event type",
                },
            )
        ]
    if variant == "ambiguous_terminal_tie":
        bad_tie = Event(
            spec["type"],
            ts(20),
            with_run(spec["bad"], target),
            "external-benchmark-v2",
        )
        good_tie = Event(
            spec["type"],
            ts(20),
            with_run(spec["good"], target),
            "external-benchmark-v2",
        )
        return [bad_tie, good_tie]
    raise ValueError(variant)


def _project_model_fields(record: dict[str, Any], evidence: Event) -> None:
    if evidence.event_type != "model_call":
        return
    run_id = evidence.data.get("run_id")
    record["data"] = {
        "run_id": run_id,
        "provider": evidence.data.get("provider"),
        "model": evidence.data.get("model"),
        "attested": evidence.data.get("attested"),
        "status_code": evidence.data.get("status_code"),
    }


def native(agent: str, events: list[Event], case_id: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for evidence in events:
        run_id = evidence.data.get("run_id")
        if agent == "actor_journal":
            record: dict[str, Any] = {
                "event": f"actor_{evidence.event_type}_journal",
                "timestamp": evidence.timestamp,
                "journal": {
                    "actor": "worker-7",
                    "execution_id": run_id,
                    "attestation": {
                        "kind": evidence.event_type,
                        "payload": dict(evidence.data),
                    },
                },
            }
            _project_model_fields(record, evidence)
        elif agent == "rpc_envelope":
            record = {
                "type": f"rpc_{evidence.event_type}_result",
                "time": evidence.timestamp,
                "metadata": {"run_id": run_id} if run_id not in (None, "") else {},
                "rpc": {
                    "method": "evidence.publish",
                    "result": {
                        "kind": evidence.event_type,
                        "payload": dict(evidence.data),
                    },
                },
            }
            _project_model_fields(record, evidence)
        elif agent == "workflow_ledger":
            record = {
                "name": f"workflow_{evidence.event_type}_transition",
                "start_time": evidence.timestamp,
                "metadata": {"run_id": run_id} if run_id not in (None, "") else {},
                "ledger": {
                    "node": "verification-node",
                    "transition": "observed",
                    "proof_type": evidence.event_type,
                    "proof": dict(evidence.data),
                },
            }
            _project_model_fields(record, evidence)
        elif agent == "event_mesh":
            mesh_data = {
                "run_id": run_id,
                "proof_kind": evidence.event_type,
                "proof": dict(evidence.data),
            }
            if evidence.event_type == "model_call":
                mesh_data.update(
                    {
                        "provider": evidence.data.get("provider"),
                        "model": evidence.data.get("model"),
                        "attested": evidence.data.get("attested"),
                        "status_code": evidence.data.get("status_code"),
                    }
                )
            record = {
                "type": f"mesh.{evidence.event_type}",
                "time": evidence.timestamp,
                "subject": "agentproof/v2/evidence",
                "data": mesh_data,
            }
        else:
            raise ValueError(agent)
        records.append(record)

    target = f"target-v2-{case_id}"
    final = {
        "actor_journal": {
            "event": "final",
            "timestamp": ts(30),
            "data": {"run_id": target, "output": "done"},
        },
        "rpc_envelope": {
            "type": "final",
            "time": ts(30),
            "metadata": {"run_id": target},
            "data": {"run_id": target, "output": "done"},
        },
        "workflow_ledger": {
            "name": "run_end",
            "start_time": ts(30),
            "metadata": {"run_id": target},
            "data": {"run_id": target, "output": "done"},
        },
        "event_mesh": {
            "type": "final",
            "time": ts(30),
            "data": {"run_id": target, "output": "done"},
        },
    }[agent]
    records.append(final)
    return records


def bridge(agent: str, records: list[dict[str, Any]]) -> list[Event]:
    output: list[Event] = []
    for record in records:
        evidence_type: str | None = None
        payload: dict[str, Any] | None = None
        timestamp = str(
            record.get("timestamp")
            or record.get("time")
            or record.get("start_time")
            or ts(0)
        )

        if agent == "actor_journal":
            journal = record.get("journal")
            attestation = (
                journal.get("attestation") if isinstance(journal, dict) else None
            )
            if isinstance(attestation, dict) and isinstance(
                attestation.get("payload"), dict
            ):
                evidence_type = str(attestation.get("kind") or "")
                payload = dict(attestation["payload"])
        elif agent == "rpc_envelope":
            rpc = record.get("rpc")
            result = rpc.get("result") if isinstance(rpc, dict) else None
            if isinstance(result, dict) and isinstance(result.get("payload"), dict):
                evidence_type = str(result.get("kind") or "")
                payload = dict(result["payload"])
        elif agent == "workflow_ledger":
            ledger = record.get("ledger")
            if isinstance(ledger, dict) and isinstance(ledger.get("proof"), dict):
                evidence_type = str(ledger.get("proof_type") or "")
                payload = dict(ledger["proof"])
        elif agent == "event_mesh":
            data = record.get("data")
            if (
                isinstance(data, dict)
                and isinstance(data.get("proof"), dict)
                and isinstance(data.get("proof_kind"), str)
            ):
                evidence_type = data["proof_kind"]
                payload = dict(data["proof"])
        else:
            raise ValueError(agent)

        if evidence_type and payload is not None:
            output.append(
                Event(
                    evidence_type,
                    timestamp,
                    payload,
                    f"external-bridge-v2:{agent}",
                )
            )
    return output


def response(task: str) -> str:
    return "AGENTPROOF_CLAIM " + json.dumps(
        TASKS[task]["claim"], sort_keys=True, separators=(",", ":")
    )


def policy(task: str) -> dict[str, Any]:
    claim = TASKS[task]["claim"]
    return {
        "minimum_score": 100,
        "require_integrity": True,
        "forbid_contradictions": True,
        "max_unsupported_ratio": 0.0,
        "required_claims": [
            {"kind": claim["kind"], "status": "verified", "minimum_count": 1}
        ],
        "required_events": [TASKS[task]["required"]],
    }


def _semantic_signature(
    events: list[Event],
) -> list[tuple[str, str, dict[str, Any]]]:
    return [(event.event_type, event.timestamp, event.data) for event in events]


def validate_design() -> None:
    case_ids: set[str] = set()
    safe = 0
    dangerous = 0
    for agent, task, variant in product(AGENTS, TASK_NAMES, VARIANTS):
        case_id = f"{agent}__{task}__{variant}"
        case_ids.add(case_id)
        core = semantic(task, variant, case_id)
        raw = native(agent, core, case_id)
        bridged = bridge(agent, raw)
        assert _semantic_signature(bridged) == _semantic_signature(core)

        target = f"target-v2-{case_id}"
        if variant in SAFE:
            safe += 1
        else:
            dangerous += 1

        if variant == "safe_recovered_terminal":
            target_events = [
                e
                for e in core
                if e.data.get("run_id") == target
                and e.event_type == TASKS[task]["type"]
            ]
            assert len(target_events) == 2
            assert target_events[0].timestamp < target_events[1].timestamp
        elif variant == "reopened_failure":
            target_events = [
                e
                for e in core
                if e.data.get("run_id") == target
                and e.event_type == TASKS[task]["type"]
            ]
            assert len(target_events) == 2
            assert target_events[0].timestamp < target_events[1].timestamp
        elif variant == "foreign_epoch_success":
            run_ids = {e.data.get("run_id") for e in core}
            assert target in run_ids and any(
                str(r).startswith("sibling-v2-") for r in run_ids
            )
        elif variant == "unscoped_success_smuggling":
            assert any(e.data.get("run_id") == target for e in core)
            assert any(e.data.get("run_id") in (None, "") for e in core)
        elif variant == "ambiguous_terminal_tie":
            assert len(core) == 2
            assert core[0].timestamp == core[1].timestamp
            assert core[0].event_type == core[1].event_type == TASKS[task]["type"]
            assert (
                core[0].data.get("run_id")
                == core[1].data.get("run_id")
                == target
            )

    assert len(case_ids) == 128
    assert safe == 32
    assert dangerous == 96


def one(
    case_id: str,
    agent: str,
    task: str,
    variant: str,
    lane: str,
) -> dict[str, Any]:
    core = semantic(task, variant, case_id)
    raw = native(agent, core, case_id)
    if lane == "core_event_contract":
        events = core
    elif lane == "native_generic_adapter":
        events = convert_agent_traces(raw)
    elif lane == "external_bridge":
        events = bridge(agent, raw)
    else:
        raise ValueError(lane)

    target_run = f"target-v2-{case_id}"
    report = audit_events(events, response(task), run_id=target_run)
    policy_result = evaluate_policy(report, events, policy(task))
    target_kind = TASKS[task]["claim"]["kind"]
    target_findings = [
        f for f in report.findings if f.claim.kind == target_kind
    ]
    target_status = (
        target_findings[0].status.value if target_findings else "missing"
    )
    target_reason = (
        target_findings[0].reason
        if target_findings
        else "target finding missing"
    )
    safe = variant in SAFE
    accepted = bool(policy_result.passed)
    return {
        "case_id": case_id,
        "lane": lane,
        "agent_family": agent,
        "task_family": task,
        "variant": variant,
        "label": "safe" if safe else "dangerous",
        "expected_accept": safe,
        "accepted": accepted,
        "correct": accepted == safe,
        "target_status": target_status,
        "target_reason": target_reason,
        "report_score": report.score,
        "integrity_ok": report.integrity_ok,
        "event_count": len(events),
        "scoped_event_count": report.event_count,
        "native_record_count": len(raw),
        "policy_checks": [
            {
                "name": check.name,
                "passed": check.passed,
                "detail": check.detail,
            }
            for check in policy_result.checks
        ],
    }


def metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    dangerous = [r for r in rows if r["label"] == "dangerous"]
    safe = [r for r in rows if r["label"] == "safe"]
    false_accepts = [r for r in dangerous if r["accepted"]]
    false_rejects = [r for r in safe if not r["accepted"]]
    dangerous_blocked = len(dangerous) - len(false_accepts)
    safe_accepted = len(safe) - len(false_rejects)
    correct = sum(bool(r["correct"]) for r in rows)
    return {
        "evaluations": len(rows),
        "dangerous": len(dangerous),
        "safe": len(safe),
        "false_accept_count": len(false_accepts),
        "false_accept_rate": round(
            len(false_accepts) / len(dangerous), 6
        )
        if dangerous
        else 0.0,
        "false_reject_count": len(false_rejects),
        "false_reject_rate": round(
            len(false_rejects) / len(safe), 6
        )
        if safe
        else 0.0,
        "dangerous_block_count": dangerous_blocked,
        "safe_accept_count": safe_accepted,
        "balanced_accuracy": round(
            (
                (dangerous_blocked / len(dangerous) if dangerous else 0.0)
                + (safe_accepted / len(safe) if safe else 0.0)
            )
            / 2,
            6,
        ),
        "correct_count": correct,
        "correct_rate": round(correct / len(rows), 6) if rows else 0.0,
        "target_status_counts": dict(
            sorted(Counter(r["target_status"] for r in rows).items())
        ),
        "critical_false_accept_case_ids": [
            r["case_id"]
            for r in false_accepts
            if r["variant"] in CRITICAL
        ],
        "false_accept_case_ids": [
            r["case_id"] for r in false_accepts
        ],
        "false_reject_case_ids": [
            r["case_id"] for r in false_rejects
        ],
    }


def groups(
    rows: list[dict[str, Any]],
    key: str,
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row[key])].append(row)
    return {
        name: metrics(items)
        for name, items in sorted(grouped.items())
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    lanes: dict[str, Any] = {}
    for lane in LANES:
        lane_rows = [row for row in rows if row["lane"] == lane]
        lanes[lane] = {
            **metrics(lane_rows),
            "by_agent_family": groups(lane_rows, "agent_family"),
            "by_task_family": groups(lane_rows, "task_family"),
            "by_variant": groups(lane_rows, "variant"),
        }

    bridge_summary = lanes["external_bridge"]
    core_summary = lanes["core_event_contract"]
    return {
        "unique_cases": 128,
        "evaluations": len(rows),
        "lane_summary": lanes,
        "preregistered_gates": {
            "external_bridge_safety": {
                "passed": bridge_summary["false_accept_count"] == 0,
                "observed_false_accepts": bridge_summary[
                    "false_accept_count"
                ],
                "required_false_accepts": 0,
            },
            "external_bridge_usability": {
                "passed": bridge_summary["safe_accept_count"] >= 30,
                "observed_safe_accepts": bridge_summary[
                    "safe_accept_count"
                ],
                "required_safe_accepts": 30,
            },
            "core_event_contract_safety": {
                "passed": core_summary["false_accept_count"] == 0,
                "observed_false_accepts": core_summary[
                    "false_accept_count"
                ],
                "required_false_accepts": 0,
            },
            "core_event_contract_usability": {
                "passed": core_summary["safe_accept_count"] >= 30,
                "observed_safe_accepts": core_summary[
                    "safe_accept_count"
                ],
                "required_safe_accepts": 30,
            },
        },
    }


def run_benchmark() -> dict[str, Any]:
    validate_design()
    rows: list[dict[str, Any]] = []
    case_ids: set[str] = set()
    for agent, task, variant in product(
        AGENTS,
        TASK_NAMES,
        VARIANTS,
    ):
        case_id = f"{agent}__{task}__{variant}"
        case_ids.add(case_id)
        for lane in LANES:
            rows.append(
                one(case_id, agent, task, variant, lane)
            )
    assert len(case_ids) == 128
    assert len(rows) == 384
    for lane in LANES:
        assert sum(row["lane"] == lane for row in rows) == 128
    return {
        "benchmark": "agentproof-external-transfer-v2",
        "frozen_product_base": "a5c1f1a46362965f0eefa83315b80fc89a494efa",
        "preregistration_commit": "5f7c879a0b631a56c3b285383ad19f80997fa4e0",
        "case_matrix": {
            "agent_families": list(AGENTS),
            "task_families": list(TASK_NAMES),
            "variants": list(VARIANTS),
            "lanes": list(LANES),
        },
        "summary": summarize(rows),
        "results": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("external-transfer-v2-result.json"),
    )
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    validate_design()
    if args.validate_only:
        print(
            json.dumps(
                {
                    "validated": True,
                    "unique_cases": 128,
                    "evaluations": 384,
                },
                sort_keys=True,
            )
        )
        return
    result = run_benchmark()
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
