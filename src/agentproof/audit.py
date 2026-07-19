from __future__ import annotations

from pathlib import Path

from .claims import extract_claims
from .detectors import scan_anomalies
from .integrity import verify_hash_chain
from .io import load_events
from .models import AuditReport
from .verifier import verify_claims


def audit_run(trace_path: str | Path, final_response: str, run_id: str = "local") -> AuditReport:
    events = load_events(trace_path)
    claims = extract_claims(final_response)
    integrity_ok, integrity_errors = verify_hash_chain(events)
    findings = verify_claims(claims, events)
    findings.extend(scan_anomalies(events, start_index=len(findings) + 1))
    return AuditReport(
        run_id=run_id,
        findings=findings,
        event_count=len(events),
        integrity_ok=integrity_ok,
        integrity_errors=integrity_errors,
    )
