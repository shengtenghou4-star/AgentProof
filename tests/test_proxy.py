import json

import pytest

from agentproof.audit import audit_run
from agentproof.io import load_events
from agentproof.proxy import (
    ProxyConfig,
    build_target,
    extract_model,
    extract_request_id,
    record_route_evidence,
    sanitize_request_headers,
)


def test_proxy_config_validates_upstream(tmp_path):
    with pytest.raises(ValueError, match="absolute"):
        ProxyConfig(upstream="api.example.com", trace=tmp_path / "trace.jsonl")


def test_build_target_and_model_extraction():
    assert build_target("https://api.example.com/v1", "/chat/completions?x=1") == (
        "https://api.example.com/v1/chat/completions?x=1"
    )
    assert extract_model(b'{"model":"gpt-5.6","messages":[]}') == "gpt-5.6"
    assert extract_model(b"not-json") is None


def test_headers_forward_auth_but_never_log_values():
    headers = sanitize_request_headers(
        {
            "Authorization": "Bearer secret-token",
            "Host": "localhost:9000",
            "Connection": "keep-alive",
            "Content-Type": "application/json",
        }
    )
    assert headers["Authorization"] == "Bearer secret-token"
    assert "Host" not in headers
    assert "Connection" not in headers


def test_request_id_normalization():
    assert extract_request_id({"X-Request-Id": "req_123"}) == "req_123"
    assert extract_request_id({"OpenAI-Request-ID": "req_456"}) == "req_456"


def test_route_evidence_records_actual_model_without_secrets(tmp_path):
    trace = tmp_path / "route.jsonl"
    config = ProxyConfig(
        upstream="https://gateway.example.com/v1",
        trace=trace,
        provider="gateway",
    )
    record_route_evidence(
        config,
        method="POST",
        target="https://gateway.example.com/v1/chat/completions",
        path="/chat/completions",
        request_body=b'{"model":"premium-model","messages":[]}',
        response_body=b'{"id":"x","model":"economy-model"}',
        request_headers={"Authorization": "Bearer never-record-this"},
        response_headers={"X-Request-Id": "req_abc"},
        requested_model="premium-model",
        actual_model="economy-model",
        request_id="req_abc",
        status_code=200,
        duration_ms=12,
        error=None,
    )

    raw = trace.read_text(encoding="utf-8")
    assert "never-record-this" not in raw
    event = load_events(trace)[0]
    assert event.data["requested_model"] == "premium-model"
    assert event.data["actual_model"] == "economy-model"
    assert event.data["model"] == "economy-model"
    assert event.data["attested"] is True
    assert event.data["route_mismatch"] is True
    assert event.data["request_header_names"] == ["authorization"]


def test_audit_detects_attested_route_substitution(tmp_path):
    trace = tmp_path / "route.jsonl"
    trace.write_text(
        json.dumps(
            {
                "event_type": "model_call",
                "timestamp": "t",
                "source": "route-proxy",
                "data": {
                    "provider": "gateway",
                    "model": "economy-model",
                    "requested_model": "premium-model",
                    "actual_model": "economy-model",
                    "attested": True,
                    "route_mismatch": True,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    report = audit_run(trace, "I used gateway/premium-model.")
    kinds = {finding.claim.kind: finding.status.value for finding in report.findings}
    assert kinds["model_used"] == "contradicted"
    assert kinds["model_route_substitution"] == "contradicted"
