from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .manifest import build_manifest, verify_manifest
from .signing import sign_bundle, verify_bundle


def build_evidence_bundle(
    *,
    trace: Path,
    response: Path,
    artifacts: list[Path],
    root: Path,
    signing_key: bytes | None = None,
    key_id: str = "default",
) -> dict[str, Any]:
    root = root.resolve()
    trace_abs = trace.resolve()
    response_abs = response.resolve()
    trace_bytes = trace_abs.read_bytes()
    response_bytes = response_abs.read_bytes()
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "trace": {
            "path": _relative_path(trace_abs, root),
            "sha256": hashlib.sha256(trace_bytes).hexdigest(),
            "bytes": len(trace_bytes),
        },
        "response": {
            "path": _relative_path(response_abs, root),
            "sha256": hashlib.sha256(response_bytes).hexdigest(),
            "bytes": len(response_bytes),
        },
        "artifacts": build_manifest(artifacts, root=root),
    }
    return sign_bundle(payload, signing_key, key_id=key_id) if signing_key else payload


def verify_evidence_bundle(payload: dict[str, Any], *, root: Path, signing_key: bytes | None = None) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != "1.0":
        errors.append("unsupported bundle schema version")
    if signing_key is not None and not verify_bundle(payload, signing_key):
        errors.append("bundle signature is invalid")

    root = root.resolve()
    for label in ("trace", "response"):
        descriptor = payload.get(label)
        if not isinstance(descriptor, dict):
            errors.append(f"missing {label} descriptor")
            continue
        path_value = descriptor.get("path")
        expected_hash = descriptor.get("sha256")
        expected_bytes = descriptor.get("bytes")
        if not isinstance(path_value, str):
            errors.append(f"invalid {label} path")
            continue
        path = (root / path_value).resolve()
        if root not in (path, *path.parents):
            errors.append(f"{label} path escapes verification root")
            continue
        if not path.is_file():
            errors.append(f"missing {label} file: {path_value}")
            continue
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != expected_hash:
            errors.append(f"{label} hash mismatch: {path_value}")
        if len(content) != expected_bytes:
            errors.append(f"{label} byte-size mismatch: {path_value}")

    manifest = payload.get("artifacts")
    if not isinstance(manifest, dict):
        errors.append("missing artifact manifest")
    else:
        errors.extend(f"artifact: {error}" for error in verify_manifest(manifest, root=root))
    return errors


def write_bundle(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _relative_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError as exc:
        raise ValueError(f"path is outside bundle root: {path}") from exc
