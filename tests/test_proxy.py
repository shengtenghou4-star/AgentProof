import json
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from agentproof.audit import audit_run
from agentproof.io import load_events
from agentproof.proxy import (
    ProxyConfig,
    build_target,
    extract_model,
    extract_request_id,
    make_handler,
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


def test_proxy_forwards_request_and_attests_returned_model(tmp_path):
    class UpstreamHandler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            self.rfile.read(length)
            body = b'{"id":"resp","model":"economy-model","choices":[]}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("X-Request-Id", "req_live")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format, *args):
            return

    upstream = ThreadingHTTPServer(("127.0.0.1", 0), UpstreamHandler)
    upstream_thread = threading.Thread(target=upstream.serve_forever, daemon=True)
    upstream_thread.start()

    trace = tmp_path / "proxy.jsonl"
    config = ProxyConfig(
        upstream=f"http://127.0.0.1:{upstream.server_port}/v1",
        trace=trace,
        provider="fake-provider",
    )
    proxy = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(config))
    proxy_thread = threading.Thread(target=proxy.serve_forever, daemon=True)
    proxy_thread.start()

    try:
        request = urllib.request.Request(
            f"http://127.0.0.1:{proxy.server_port}/chat/completions",
            data=b'{"model":"premium-model","messages":[]}',
            headers={
                "Authorization": "Bearer integration-secret",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read())
        assert payload["model"] == "economy-model"
    finally:
        proxy.shutdown()
        upstream.shutdown()
        proxy.server_close()
        upstream.server_close()
        proxy_thread.join(timeout=5)
        upstream_thread.join(timeout=5)

    raw = trace.read_text(encoding="utf-8")
    assert "integration-secret" not in raw
    event = load_events(trace)[0]
    assert event.data["request_id"] == "req_live"
    assert event.data["requested_model"] == "premium-model"
    assert event.data["actual_model"] == "economy-model"
    assert event.data["route_mismatch"] is True
