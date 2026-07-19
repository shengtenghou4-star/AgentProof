from pathlib import Path

import pytest

from agentproof.bundle import build_evidence_bundle
from agentproof.signing import load_key, sign_bundle, verify_bundle


def test_sign_and_verify_bundle():
    key = b"k" * 32
    payload = {"value": 7, "nested": {"ok": True}}
    signed = sign_bundle(payload, key, key_id="test")
    assert verify_bundle(signed, key) is True
    signed["value"] = 8
    assert verify_bundle(signed, key) is False


def test_build_bundle_hashes_inputs(tmp_path):
    trace = tmp_path / "trace.jsonl"
    response = tmp_path / "response.txt"
    artifact = tmp_path / "artifact.bin"
    trace.write_text("{}\n", encoding="utf-8")
    response.write_text("done", encoding="utf-8")
    artifact.write_bytes(b"artifact")

    bundle = build_evidence_bundle(
        trace=trace,
        response=response,
        artifacts=[artifact],
        root=tmp_path,
        signing_key=b"x" * 32,
    )

    assert bundle["trace"]["bytes"] == 3
    assert bundle["response"]["bytes"] == 4
    assert verify_bundle(bundle, b"x" * 32) is True


def test_load_key_rejects_short_key(tmp_path):
    path = tmp_path / "key"
    path.write_bytes(b"short")
    with pytest.raises(ValueError, match="at least 32"):
        load_key(path)
