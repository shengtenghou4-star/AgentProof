from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Iterable, Mapping

_DEFAULT_SECRET_NAMES = {
    "api_key",
    "apikey",
    "authorization",
    "access_token",
    "auth_token",
    "client_secret",
    "password",
    "passwd",
    "private_key",
    "secret",
    "token",
}

_SECRET_PATTERNS = (
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{12,}"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{8,}"),
    re.compile(
        r"(?i)(?P<name>api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|password|passwd|secret|token)"
        r"(?P<sep>\s*[:=]\s*)(?P<value>[^\s,;]+)"
    ),
)


@dataclass(frozen=True)
class CapturedText:
    text: str
    sha256: str
    original_bytes: int
    captured_bytes: int
    truncated: bool
    redactions: int

    def to_dict(self) -> dict[str, object]:
        return {
            "text": self.text,
            "sha256": self.sha256,
            "original_bytes": self.original_bytes,
            "captured_bytes": self.captured_bytes,
            "truncated": self.truncated,
            "redactions": self.redactions,
        }


def capture_text(value: str | bytes | None, *, max_bytes: int = 65536) -> CapturedText:
    """Redact common secret forms and bound evidence size while preserving a full digest."""

    if max_bytes < 256:
        raise ValueError("max_bytes must be at least 256")
    if value is None:
        raw = b""
        text = ""
    elif isinstance(value, bytes):
        raw = value
        text = value.decode("utf-8", errors="replace")
    else:
        text = value
        raw = value.encode("utf-8", errors="replace")

    digest = hashlib.sha256(raw).hexdigest()
    redacted, redactions = redact_text(text)
    encoded = redacted.encode("utf-8")
    if len(encoded) <= max_bytes:
        captured = redacted
        truncated = False
    else:
        marker = f"\n...[truncated; full_sha256={digest}]...\n".encode("utf-8")
        remaining = max_bytes - len(marker)
        head_size = remaining // 2
        tail_size = remaining - head_size
        captured = (
            encoded[:head_size].decode("utf-8", errors="ignore")
            + marker.decode("utf-8")
            + encoded[-tail_size:].decode("utf-8", errors="ignore")
        )
        truncated = True

    return CapturedText(
        text=captured,
        sha256=digest,
        original_bytes=len(raw),
        captured_bytes=len(captured.encode("utf-8")),
        truncated=truncated,
        redactions=redactions,
    )


def redact_text(text: str) -> tuple[str, int]:
    redactions = 0
    output = text
    for pattern in _SECRET_PATTERNS:
        if "name" in pattern.groupindex:
            output, count = pattern.subn(
                lambda match: f"{match.group('name')}{match.group('sep')}[REDACTED]",
                output,
            )
        else:
            output, count = pattern.subn("[REDACTED]", output)
        redactions += count
    return output, redactions


def safe_environment_metadata(
    environment: Mapping[str, str],
    *,
    allowed_names: Iterable[str] = (),
) -> dict[str, object]:
    """Return environment names and digests without exposing values."""

    allowed = {name for name in allowed_names}
    entries: list[dict[str, object]] = []
    for name in sorted(environment):
        value = environment[name]
        lowered = name.lower()
        secret_like = any(part in lowered for part in _DEFAULT_SECRET_NAMES)
        entry: dict[str, object] = {
            "name": name,
            "present": True,
            "secret_like": secret_like,
            "value_sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
            "length": len(value),
        }
        if name in allowed and not secret_like:
            entry["value"] = value
        entries.append(entry)
    return {"variables": entries, "count": len(entries)}
