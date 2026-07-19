from __future__ import annotations

import html
import json
from pathlib import Path

from .models import AuditReport


def write_json(report: AuditReport, path: str | Path) -> None:
    Path(path).write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True), encoding="utf-8")


def write_html(report: AuditReport, path: str | Path) -> None:
    rows = []
    for finding in report.findings:
        rows.append(
            "<tr>"
            f"<td>{html.escape(finding.claim.claim_id)}</td>"
            f"<td>{html.escape(finding.claim.text)}</td>"
            f"<td><strong>{html.escape(finding.status.value)}</strong></td>"
            f"<td>{html.escape(finding.reason)}</td>"
            "</tr>"
        )
    integrity = "PASS" if report.integrity_ok else "FAIL"
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AgentProof audit {html.escape(report.run_id)}</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:1100px;margin:40px auto;padding:0 20px;color:#18202a}}
header{{display:flex;gap:30px;align-items:end;flex-wrap:wrap}} .score{{font-size:56px;font-weight:800}}
table{{border-collapse:collapse;width:100%;margin-top:24px}} th,td{{padding:12px;border-bottom:1px solid #ddd;text-align:left;vertical-align:top}}
small{{color:#667}} code{{background:#f3f5f7;padding:2px 5px;border-radius:4px}}
</style></head><body>
<header><div><h1>AgentProof Audit</h1><small>Run <code>{html.escape(report.run_id)}</code></small></div>
<div><div class="score">{report.score:.1f}</div><small>evidence score / 100</small></div>
<div><strong>{integrity}</strong><br><small>trace integrity</small></div>
<div><strong>{report.event_count}</strong><br><small>observed events</small></div></header>
<table><thead><tr><th>ID</th><th>Claim</th><th>Status</th><th>Reason</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
</body></html>"""
    Path(path).write_text(document, encoding="utf-8")
