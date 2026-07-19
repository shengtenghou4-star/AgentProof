from __future__ import annotations

import json
import re
from typing import Any

from .models import Claim

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "all_tests_passed",
        re.compile(
            r"\b(?:(?:all|every)\s+(?:one\s+of\s+)?(?:the\s+)?tests?|the\s+entire\s+test\s+suite)\s+"
            r"(?:have\s+|has\s+)?passed\b",
            re.I,
        ),
    ),
    (
        "deployed",
        re.compile(
            r"\b(?:api|service|application|app)\s+(?:has\s+been\s+|is\s+)?deployed\b",
            re.I,
        ),
    ),
    (
        "completed",
        re.compile(
            r"\b(?:task|work|implementation|project)\s+(?:is|has\s+been)\s+(?:fully\s+)?completed\b",
            re.I,
        ),
    ),
]

_METRIC = re.compile(
    r"\b(?P<name>roc[- ]?auc|auc|accuracy|f1|precision|recall)\s*"
    r"(?:=|:|of|reached|is|was)?\s*(?P<value>0(?:\.\d+)?|1(?:\.0+)?)\b",
    re.I,
)
_MODEL = re.compile(
    r"\b(?:used|called|ran|invoked)\s+"
    r"(?:(?P<provider>[A-Za-z0-9_.-]+)[/:])?(?P<model>[A-Za-z][A-Za-z0-9_.-]{2,})\b",
    re.I,
)
_FILE = re.compile(
    r"\b(?:created|generated|wrote)\s+(?:the\s+)?(?:file\s+)?"
    r"[`'\"]?(?P<path>[\w./-]+\.[A-Za-z0-9]+)[`'\"]?",
    re.I,
)
_STRUCTURED = re.compile(r"^\s*AGENTPROOF_CLAIM\s+(?P<payload>\{.*\})\s*$", re.M)
_NEGATION = re.compile(
    r"(?:\bnot\b|\bnever\b|\bno\b|\bdid(?:\s+not|n't)\b|\bhas(?:\s+not|n't)\b|\bfailed\s+to\b)\s*$",
    re.I,
)
_ALLOWED_STRUCTURED_KINDS = {
    "all_tests_passed",
    "check_succeeded",
    "completed",
    "deployed",
    "file_created",
    "metric",
    "model_used",
}


def extract_claims(text: str) -> list[Claim]:
    """Extract conservative, independently testable claims from final agent text."""

    claims: list[Claim] = []

    def add(kind: str, matched_text: str, expected: dict[str, object] | None = None) -> None:
        claims.append(
            Claim(
                claim_id=f"C{len(claims) + 1}",
                kind=kind,
                text=matched_text.strip(),
                expected=expected or {},
            )
        )

    for match in _STRUCTURED.finditer(text):
        payload = _parse_structured_claim(match.group("payload"))
        add(payload["kind"], match.group(0), payload["expected"])

    for kind, pattern in _PATTERNS:
        for match in pattern.finditer(text):
            if not _is_negated(text, match.start()):
                add(kind, match.group(0))

    for match in _METRIC.finditer(text):
        if _is_negated(text, match.start()):
            continue
        add(
            "metric",
            match.group(0),
            {
                "name": match.group("name")
                .lower()
                .replace(" ", "-")
                .replace("roc-auc", "auc"),
                "value": float(match.group("value")),
            },
        )

    for match in _MODEL.finditer(text):
        if _is_negated(text, match.start()):
            continue
        add(
            "model_used",
            match.group(0),
            {"provider": match.group("provider"), "model": match.group("model")},
        )

    for match in _FILE.finditer(text):
        if not _is_negated(text, match.start()):
            add("file_created", match.group(0), {"path": match.group("path")})

    return _deduplicate(claims)


def _parse_structured_claim(raw: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid AGENTPROOF_CLAIM JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError("AGENTPROOF_CLAIM payload must be an object")
    kind = payload.get("kind")
    expected = payload.get("expected", {})
    if kind not in _ALLOWED_STRUCTURED_KINDS:
        raise ValueError(f"unsupported structured claim kind: {kind}")
    if not isinstance(expected, dict):
        raise ValueError("structured claim expected must be an object")
    return {"kind": str(kind), "expected": dict(expected)}


def _is_negated(text: str, start: int) -> bool:
    window = text[max(0, start - 48) : start]
    sentence = re.split(r"[.!?\n;]", window)[-1]
    return bool(_NEGATION.search(sentence))


def _deduplicate(claims: list[Claim]) -> list[Claim]:
    seen: set[tuple[str, tuple[tuple[str, object], ...]]] = set()
    output: list[Claim] = []
    for claim in claims:
        key = (claim.kind, _hashable_items(claim.expected))
        if key in seen:
            continue
        seen.add(key)
        output.append(
            Claim(
                claim_id=f"C{len(output) + 1}",
                kind=claim.kind,
                text=claim.text,
                expected=claim.expected,
            )
        )
    return output


def _hashable_items(value: dict[str, object]) -> tuple[tuple[str, object], ...]:
    return tuple(
        sorted(
            (key, json.dumps(item, sort_keys=True, default=str))
            for key, item in value.items()
        )
    )
