from __future__ import annotations

from pathlib import Path

from .claims import extract_claims
from .detectors import scan_anomalies
from .integrity import verify_hash_chain
from .io import load_events
from .models import AuditReport, Event
from .verifier import verify_claims


def audit_run(trace_path: str | Path, final_response: str, run_id: str = "local") -> AuditReport:
    return audit_events(load_events(trace_path), final_response, run_id=run_id)


def audit_events(events: list[Event], final_response: str, run_id: str = "local") -> AuditReport:
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
