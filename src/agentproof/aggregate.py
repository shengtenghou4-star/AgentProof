from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


_STATUSES = ("verified", "partial", "unsupported", "contradicted")


def aggregate_reports(paths: list[Path]) -> dict[str, Any]:
    if not paths:
        raise ValueError("at least one audit report is required")

    reports = [_load_report(path) for path in paths]
    scores = [float(report.get("score", 0)) for report in reports]
    status_counts: Counter[str] = Counter()
    by_kind_counts: dict[str, Counter[str]] = defaultdict(Counter)
    contradictions: list[dict[str, str]] = []

    for report in reports:
        run_id = str(report.get("run_id", "unknown"))
        findings = report.get("findings", [])
        if not isinstance(findings, list):
            raise ValueError(f"report {run_id} has invalid findings")
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            status = str(finding.get("status", "unsupported"))
            claim = finding.get("claim", {})
            kind = str(claim.get("kind", "unknown")) if isinstance(claim, dict) else "unknown"
            status_counts[status] += 1
            by_kind_counts[kind][status] += 1
            if status == "contradicted":
                contradictions.append(
                    {
                        "run_id": run_id,
                        "kind": kind,
                        "text": str(claim.get("text", "")) if isinstance(claim, dict) else "",
                        "reason": str(finding.get("reason", "")),
                    }
                )

    total_findings = sum(status_counts.values())
    integrity_passes = sum(bool(report.get("integrity_ok", False)) for report in reports)
    by_kind: dict[str, Any] = {}
    for kind, counts in sorted(by_kind_counts.items()):
        total = sum(counts.values())
        by_kind[kind] = {
            "findings": total,
            "verified_rate": round(counts["verified"] / total, 4) if total else 0.0,
            "contradiction_rate": round(counts["contradicted"] / total, 4) if total else 0.0,
            "status_counts": {status: counts[status] for status in _STATUSES},
        }

    return {
        "runs": len(reports),
        "score": {
            "mean": round(mean(scores), 2),
            "minimum": round(min(scores), 2),
            "maximum": round(max(scores), 2),
        },
        "integrity_pass_rate": round(integrity_passes / len(reports), 4),
        "findings": total_findings,
        "verified_rate": round(status_counts["verified"] / total_findings, 4) if total_findings else 0.0,
        "contradiction_rate": round(status_counts["contradicted"] / total_findings, 4) if total_findings else 0.0,
        "status_counts": {status: status_counts[status] for status in _STATUSES},
        "by_kind": by_kind,
        "contradictions": contradictions,
    }


def _load_report(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or "findings" not in payload:
        raise ValueError(f"not an AgentProof audit report: {path}")
    return payload
