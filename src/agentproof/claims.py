from __future__ import annotations

import re

from .models import Claim


_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "all_tests_passed",
        re.compile(
            r"\b(?:all|every(?:\s+one\s+of)?)\s+(?:the\s+)?tests?\s+(?:have\s+)?passed\b",
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
            r"\b(?:task|work|implementation|project)\s+(?:is|has been)\s+(?:fully\s+)?completed\b",
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
    r"(?:(?P<provider>[A-Za-z0-9_.-]+)[/:])?"
    r"(?P<model>[A-Za-z][A-Za-z0-9_.-]{2,})\b",
    re.I,
)
_FILE = re.compile(
    r"\b(?:created|generated|wrote)\s+(?:the\s+)?(?:file\s+)?"
    r"[`'\"]?(?P<path>[\w./-]+\.[A-Za-z0-9]+)[`'\"]?",
    re.I,
)


def extract_claims(text: str) -> list[Claim]:
    """Extract conservative, independently testable claims from final agent text."""

    claims: list[Claim] = []

    def add(
        kind: str,
        matched_text: str,
        expected: dict[str, object] | None = None,
    ) -> None:
        claims.append(
            Claim(
                claim_id=f"C{len(claims) + 1}",
                kind=kind,
                text=matched_text.strip(),
                expected=expected or {},
            )
        )

    for kind, pattern in _PATTERNS:
        for match in pattern.finditer(text):
            add(kind, match.group(0))

    for match in _METRIC.finditer(text):
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
        add(
            "model_used",
            match.group(0),
            {"provider": match.group("provider"), "model": match.group("model")},
        )

    for match in _FILE.finditer(text):
        add("file_created", match.group(0), {"path": match.group("path")})

    return _deduplicate(claims)


def _deduplicate(claims: list[Claim]) -> list[Claim]:
    seen: set[tuple[str, tuple[tuple[str, object], ...]]] = set()
    output: list[Claim] = []
    for claim in claims:
        key = (claim.kind, tuple(sorted(claim.expected.items())))
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
