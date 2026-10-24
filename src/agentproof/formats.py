from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import asdict

from .models import AuditReport, FindingStatus

_LEVELS = {
    FindingStatus.VERIFIED: "none",
    FindingStatus.PARTIAL: "warning",
    FindingStatus.UNSUPPORTED: "warning",
    FindingStatus.CONTRADICTED: "error",
}


def render_sarif(report: AuditReport) -> str:
    """Render audit findings as SARIF 2.1.0 for code-scanning ingestion."""

    rules: dict[str, dict[str, object]] = {}
    results: list[dict[str, object]] = []
    for finding in report.findings:
        rule_id = f"agentproof/{finding.claim.kind}"
        rules.setdefault(
            rule_id,
            {
                "id": rule_id,
                "shortDescription": {"text": f"Verify {finding.claim.kind} claim"},
                "fullDescription": {
                    "text": "Agent completion claims must be supported by observable execution evidence."
                },
                "help": {
                    "text": "Inspect the linked evidence events and rerun the declared acceptance checks."
                },
            },
        )
        result: dict[str, object] = {
            "ruleId": rule_id,
            "level": _LEVELS[finding.status],
            "message": {
                "text": f"{finding.status.value}: {finding.claim.text} — {finding.reason}"
            },
            "properties": {
                "claimId": finding.claim.claim_id,
                "claimKind": finding.claim.kind,
                "status": finding.status.value,
                "confidence": finding.confidence,
                "evidenceEventIndexes": list(finding.evidence_event_indexes),
            },
        }
        results.append(result)

    payload = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "AgentProof",
                        "informationUri": "https://github.com/shengtenghou4-star/AgentProof",
                        "rules": list(rules.values()),
                    }
                },
                "automationDetails": {"id": report.run_id},
                "results": results,
                "properties": {
                    "score": report.score,
                    "integrityOk": report.integrity_ok,
                    "eventCount": report.event_count,
                },
            }
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def render_junit(report: AuditReport) -> str:
    """Render one testcase per claim so CI systems can display audit failures."""

    failures = sum(f.status == FindingStatus.CONTRADICTED for f in report.findings)
    skipped = sum(f.status in {FindingStatus.PARTIAL, FindingStatus.UNSUPPORTED} for f in report.findings)
    suite = ET.Element(
        "testsuite",
        {
            "name": f"agentproof:{report.run_id}",
            "tests": str(len(report.findings)),
            "failures": str(failures),
            "errors": "0" if report.integrity_ok else "1",
            "skipped": str(skipped),
        },
    )
    properties = ET.SubElement(suite, "properties")
    ET.SubElement(properties, "property", {"name": "score", "value": str(report.score)})
    ET.SubElement(
        properties,
        "property",
        {"name": "integrity_ok", "value": str(report.integrity_ok).lower()},
    )

    if not report.integrity_ok:
        case = ET.SubElement(suite, "testcase", {"name": "evidence-integrity"})
        error = ET.SubElement(case, "error", {"message": "Evidence integrity check failed"})
        error.text = "\n".join(report.integrity_errors)

    for finding in report.findings:
        case = ET.SubElement(
            suite,
            "testcase",
            {
                "classname": f"agentproof.{finding.claim.kind}",
                "name": finding.claim.claim_id,
            },
        )
        detail = json.dumps(
            {
                "claim": asdict(finding.claim),
                "reason": finding.reason,
                "evidence_event_indexes": list(finding.evidence_event_indexes),
                "confidence": finding.confidence,
            },
            indent=2,
            sort_keys=True,
        )
        if finding.status == FindingStatus.CONTRADICTED:
            failure = ET.SubElement(case, "failure", {"message": finding.reason})
            failure.text = detail
        elif finding.status in {FindingStatus.PARTIAL, FindingStatus.UNSUPPORTED}:
            skipped_node = ET.SubElement(
                case,
                "skipped",
                {"message": f"{finding.status.value}: {finding.reason}"},
            )
            skipped_node.text = detail
        else:
            output = ET.SubElement(case, "system-out")
            output.text = detail

    return ET.tostring(suite, encoding="unicode", xml_declaration=True) + "\n"
