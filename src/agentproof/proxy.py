from __future__ import annotations

import hashlib
import json
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Mapping
from urllib.parse import urljoin, urlsplit

from .recorder import TraceRecorder

_HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}
_RESPONSE_BLOCKED = _HOP_BY_HOP | {"content-length", "content-encoding"}


@dataclass
class ProxyConfig:
    upstream: str
    trace: Path
    provider: str | None = None
    timeout_seconds: float = 120.0
    max_body_bytes: int = 20 * 1024 * 1024
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __post_init__(self) -> None:
        parsed = urlsplit(self.upstream)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("upstream must be an absolute http(s) URL")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.max_body_bytes < 1:
            raise ValueError("max_body_bytes must be positive")

    @property
    def provider_name(self) -> str:
        return self.provider or str(urlsplit(self.upstream).hostname or "unknown")


def serve_proxy(host: str, port: int, config: ProxyConfig) -> None:
    server = ThreadingHTTPServer((host, port), make_handler(config))
    try:
        server.serve_forever()
    finally:
        server.server_close()


def make_handler(config: ProxyConfig) -> type[BaseHTTPRequestHandler]:
    class RouteProxyHandler(BaseHTTPRequestHandler):
        server_version = "AgentProofRouteProxy/0.3"

        def do_POST(self) -> None:  # noqa: N802
            self._forward()

        def do_GET(self) -> None:  # noqa: N802
            self._forward()

        def do_OPTIONS(self) -> None:  # noqa: N802
            self._forward()

        def log_message(self, _format: str, *args: object) -> None:
            return

        def _forward(self) -> None:
            try:
                request_body = self._read_body()
            except ValueError as exc:
                self.send_error(413, str(exc))
                return

            target = build_target(config.upstream, self.path)
            request_model = extract_model(request_body)
            request_headers = sanitize_request_headers(dict(self.headers.items()))
            request = urllib.request.Request(
                target,
                data=request_body if self.command not in {"GET", "HEAD"} else None,
                headers=request_headers,
                method=self.command,
            )
            started = time.monotonic()
            status_code = 0
            response_body = b""
            response_headers: Mapping[str, str] = {}
            error: str | None = None

            try:
                with urllib.request.urlopen(request, timeout=config.timeout_seconds) as response:
                    status_code = int(response.status)
                    response_body = response.read(config.max_body_bytes + 1)
                    response_headers = dict(response.headers.items())
            except urllib.error.HTTPError as exc:
                status_code = int(exc.code)
                response_body = exc.read(config.max_body_bytes + 1)
                response_headers = dict(exc.headers.items()) if exc.headers else {}
            except urllib.error.URLError as exc:
                error = str(exc.reason)
                status_code = 502
                response_body = json.dumps(
                    {"error": {"message": "upstream request failed", "type": "proxy_error"}}
                ).encode("utf-8")
                response_headers = {"Content-Type": "application/json"}

            if len(response_body) > config.max_body_bytes:
                error = "upstream response exceeded configured size limit"
                status_code = 502
                response_body = json.dumps(
                    {"error": {"message": error, "type": "proxy_error"}}
                ).encode("utf-8")
                response_headers = {"Content-Type": "application/json"}

            duration_ms = int((time.monotonic() - started) * 1000)
            actual_model = extract_model(response_body)
            request_id = extract_request_id(response_headers)
            record_route_evidence(
                config,
                method=self.command,
                target=target,
                path=self.path,
                request_body=request_body,
                response_body=response_body,
                request_headers=request_headers,
                response_headers=response_headers,
                requested_model=request_model,
                actual_model=actual_model,
                request_id=request_id,
                status_code=status_code,
                duration_ms=duration_ms,
                error=error,
            )
            self._send_response(status_code, response_headers, response_body)

        def _read_body(self) -> bytes:
            raw_length = self.headers.get("Content-Length")
            if raw_length is None:
                return b""
            try:
                length = int(raw_length)
            except ValueError as exc:
                raise ValueError("invalid Content-Length") from exc
            if length < 0 or length > config.max_body_bytes:
                raise ValueError("request body exceeds configured size limit")
            return self.rfile.read(length)

        def _send_response(
            self,
            status_code: int,
            headers: Mapping[str, str],
            body: bytes,
        ) -> None:
            self.send_response(status_code)
            for name, value in headers.items():
                if name.lower() not in _RESPONSE_BLOCKED:
                    self.send_header(name, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

    return RouteProxyHandler


def build_target(upstream: str, request_path: str) -> str:
    return urljoin(upstream.rstrip("/") + "/", request_path.lstrip("/"))


def sanitize_request_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {
        name: value
        for name, value in headers.items()
        if name.lower() not in _HOP_BY_HOP | {"host", "content-length"}
    }


def extract_model(body: bytes) -> str | None:
    if not body:
        return None
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    model = payload.get("model")
    return str(model) if model not in (None, "") else None


def extract_request_id(headers: Mapping[str, str]) -> str | None:
    lowered = {name.lower(): value for name, value in headers.items()}
    for name in ("x-request-id", "request-id", "openai-request-id", "cf-ray"):
        if lowered.get(name):
            return str(lowered[name])
    return None


def record_route_evidence(
    config: ProxyConfig,
    *,
    method: str,
    target: str,
    path: str,
    request_body: bytes,
    response_body: bytes,
    request_headers: Mapping[str, str],
    response_headers: Mapping[str, str],
    requested_model: str | None,
    actual_model: str | None,
    request_id: str | None,
    status_code: int,
    duration_ms: int,
    error: str | None,
) -> None:
    selected_model = actual_model or requested_model or "unknown"
    route_mismatch = bool(
        requested_model and actual_model and requested_model.lower() != actual_model.lower()
    )
    data = {
        "provider": config.provider_name,
        "model": selected_model,
        "requested_model": requested_model,
        "actual_model": actual_model,
        "request_id": request_id,
        "upstream_host": urlsplit(target).hostname,
        "path": path,
        "method": method,
        "status_code": status_code,
        "duration_ms": duration_ms,
        "request_sha256": hashlib.sha256(request_body).hexdigest(),
        "response_sha256": hashlib.sha256(response_body).hexdigest(),
        "request_header_names": sorted(name.lower() for name in request_headers),
        "response_header_names": sorted(name.lower() for name in response_headers),
        "attested": True,
        "route_mismatch": route_mismatch,
        "error": error,
    }
    with config.lock:
        TraceRecorder(config.trace, source="route-proxy").emit("model_call", **data)
