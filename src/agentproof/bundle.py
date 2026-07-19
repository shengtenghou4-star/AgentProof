from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .manifest import build_manifest
from .signing import sign_bundle


def build_evidence_bundle(
    *,
    trace: Path,
    response: Path,
    artifacts: list[Path],
    root: Path,
    signing_key: bytes | None = None,
    key_id: str = "default",
) -> dict[str, Any]:
    trace_bytes = trace.read_bytes()
    response_bytes = response.read_bytes()
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "trace": {
            "path": str(trace),
            "sha256": hashlib.sha256(trace_bytes).hexdigest(),
            "bytes": len(trace_bytes),
        },
        "response": {
            "path": str(response),
            "sha256": hashlib.sha256(response_bytes).hexdigest(),
            "bytes": len(response_bytes),
        },
        "artifacts": build_manifest(artifacts, root=root),
    }
    return sign_bundle(payload, signing_key, key_id=key_id) if signing_key else payload


def write_bundle(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
