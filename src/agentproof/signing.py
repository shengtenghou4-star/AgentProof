from __future__ import annotations

import base64
import hashlib
import hmac
import json
from pathlib import Path
from typing import Any


def canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sign_bundle(payload: dict[str, Any], key: bytes, *, key_id: str = "default") -> dict[str, Any]:
    unsigned = dict(payload)
    unsigned.pop("signature", None)
    digest = hmac.new(key, canonical_bytes(unsigned), hashlib.sha256).digest()
    result = dict(unsigned)
    result["signature"] = {
        "algorithm": "HMAC-SHA256",
        "key_id": key_id,
        "value": base64.b64encode(digest).decode("ascii"),
    }
    return result


def verify_bundle(payload: dict[str, Any], key: bytes) -> bool:
    signature = payload.get("signature")
    if not isinstance(signature, dict) or signature.get("algorithm") != "HMAC-SHA256":
        return False
    encoded = signature.get("value")
    if not isinstance(encoded, str):
        return False
    try:
        expected = base64.b64decode(encoded, validate=True)
    except ValueError:
        return False
    unsigned = dict(payload)
    unsigned.pop("signature", None)
    actual = hmac.new(key, canonical_bytes(unsigned), hashlib.sha256).digest()
    return hmac.compare_digest(expected, actual)


def load_key(path: Path) -> bytes:
    key = path.read_bytes().strip()
    if len(key) < 32:
        raise ValueError("signing key must contain at least 32 bytes")
    return key
