from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class FindingStatus(str, Enum):
    VERIFIED = "verified"
    PARTIAL = "partial"
    UNSUPPORTED = "unsupported"
    CONTRADICTED = "contradicted"


@dataclass(frozen=True)
class Event:
    """Observed fact emitted by an agent runtime or external verifier."""

    event_type: str
    timestamp: str
    data: dict[str, Any] = field(default_factory=dict)
    source: str = "runtime"


@dataclass(frozen=True)
class Claim:
    """Atomic claim extracted from an agent's final response."""

    claim_id: str
    kind: str
    text: str
    expected: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Finding:
    """Verification result for a single atomic claim."""

    claim: Claim
    status: FindingStatus
    reason: str
    evidence_event_indexes: tuple[int, ...] = ()
    confidence: float = 1.0


@dataclass
class AuditReport:
    run_id: str
    findings: list[Finding]
    event_count: int
    integrity_ok: bool
    integrity_errors: list[str] = field(default_factory=list)

    @property
    def verified_count(self) -> int:
        return sum(f.status == FindingStatus.VERIFIED for f in self.findings)

    @property
    def score(self) -> float:
        if not self.findings:
            return 0.0
        weights = {
            FindingStatus.VERIFIED: 1.0,
            FindingStatus.PARTIAL: 0.5,
            FindingStatus.UNSUPPORTED: 0.0,
            FindingStatus.CONTRADICTED: 0.0,
        }
        return round(100 * sum(weights[f.status] for f in self.findings) / len(self.findings), 1)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["score"] = self.score
        payload["verified_count"] = self.verified_count
        for item in payload["findings"]:
            item["status"] = item["status"].value if hasattr(item["status"], "value") else item["status"]
        return payload
