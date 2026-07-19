from agentproof.security import capture_text, redact_text, safe_environment_metadata


def test_redacts_common_secret_forms():
    text = "Authorization: Bearer abcdefghijklmnop api_key=supersecret ghp_abcdefghijklmnop"
    redacted, count = redact_text(text)
    assert "abcdefghijklmnop" not in redacted
    assert "supersecret" not in redacted
    assert count >= 3


def test_capture_bounds_output_and_preserves_digest():
    captured = capture_text("x" * 5000, max_bytes=512)
    assert captured.truncated is True
    assert captured.original_bytes == 5000
    assert captured.captured_bytes <= 512
    assert len(captured.sha256) == 64
    assert "full_sha256" in captured.text


def test_environment_metadata_never_exposes_secret_like_values():
    payload = safe_environment_metadata(
        {"API_TOKEN": "secret-value", "CI": "true"},
        allowed_names=["API_TOKEN", "CI"],
    )
    entries = {item["name"]: item for item in payload["variables"]}
    assert "value" not in entries["API_TOKEN"]
    assert entries["CI"]["value"] == "true"
