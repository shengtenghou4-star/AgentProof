from agentproof.manifest import build_manifest, verify_manifest


def test_manifest_detects_artifact_tampering(tmp_path):
    artifact = tmp_path / "model.bin"
    artifact.write_bytes(b"original")
    manifest = build_manifest([artifact], root=tmp_path)
    assert verify_manifest(manifest, root=tmp_path) == []
    artifact.write_bytes(b"changed")
    errors = verify_manifest(manifest, root=tmp_path)
    assert any("mismatch" in error for error in errors)


def test_manifest_rejects_outside_root(tmp_path):
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    try:
        build_manifest([outside], root=tmp_path)
    except ValueError as exc:
        assert "outside manifest root" in str(exc)
    else:
        raise AssertionError("expected ValueError")
