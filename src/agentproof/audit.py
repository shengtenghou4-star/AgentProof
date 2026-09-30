from __future__ import annotations

from pathlib import Path

from .claims import extract_claims
from .detectors import scan_anomalies
from .evidence import bind_events_to_run
from .integrity import verify_hash_chain
from .io import load_events
from .models import AuditReport, Event
from .verifier import verify_claims


def audit_run(trace_path: str | Path, final_response: str, run_id: str = "local") -> AuditReport:
    return audit_events(load_events(trace_path), final_response, run_id=run_id)


def audit_events(events: list[Event], final_response: str, run_id: str = "local") -> AuditReport:
    claims = extract_claims(final_response)
    integrity_ok, integrity_errors = verify_hash_chain(events)
    scoped_events = bind_events_to_run(events, run_id)
    findings = verify_claims(claims, scoped_events)
    findings.extend(scan_anomalies(scoped_events, start_index=len(findings) + 1))
    return AuditReport(
        run_id=run_id,
        findings=findings,
        event_count=len(scoped_events),
        integrity_ok=integrity_ok,
        integrity_errors=integrity_errors,
    )
