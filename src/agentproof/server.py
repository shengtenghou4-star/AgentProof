from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .audit import audit_events
from .io import parse_events
from .policy import evaluate_policy

_MAX_BODY_BYTES = 2 * 1024 * 1024

_DASHBOARD = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AgentProof</title><style>
body{font-family:system-ui,sans-serif;max-width:1100px;margin:40px auto;padding:0 20px;background:#0b1020;color:#e9eefc}
h1{margin-bottom:4px}p{color:#aebbd9}label{display:block;margin:18px 0 6px;font-weight:700}
textarea{width:100%;min-height:150px;background:#111a31;color:#e9eefc;border:1px solid #35446a;border-radius:8px;padding:12px;box-sizing:border-box}
button{margin:18px 0;padding:10px 18px;border:0;border-radius:8px;font-weight:700;cursor:pointer}
pre{white-space:pre-wrap;background:#111a31;border:1px solid #35446a;border-radius:8px;padding:16px;min-height:100px}
</style></head><body><h1>AgentProof</h1><p>Verify agent claims against observable execution evidence.</p>
<label>Final response</label><textarea id="response">All tests passed.</textarea>
<label>Events JSON array</label><textarea id="events">[{"event_type":"test_summary","timestamp":"now","data":{"total":10,"passed":9,"failed":1,"errors":0,"exit_code":1}}]</textarea>
<button onclick="audit()">Audit run</button><pre id="result">Ready.</pre><script>
async function audit(){const out=document.getElementById('result');try{const body={response:document.getElementById('response').value,events:JSON.parse(document.getElementById('events').value)};const r=await fetch('/api/audit',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body)});out.textContent=JSON.stringify(await r.json(),null,2)}catch(e){out.textContent=String(e)}}
</script></body></html>"""


def handle_api_request(path: str, payload: Any) -> tuple[int, dict[str, Any]]:
    if not isinstance(payload, dict):
        return HTTPStatus.BAD_REQUEST, {"error": "request body must be a JSON object"}
    try:
        events = parse_events(payload.get("events"))
        response = payload.get("response")
        if not isinstance(response, str):
            raise ValueError("response must be a string")
        run_id = str(payload.get("run_id", "api"))
        report = audit_events(events, response, run_id=run_id)
        if path == "/api/audit":
            return HTTPStatus.OK, report.to_dict()
        if path == "/api/gate":
            policy = payload.get("policy")
            if not isinstance(policy, dict):
                raise ValueError("policy must be a JSON object")
            result = evaluate_policy(report, events, policy)
            return HTTPStatus.OK, {"audit": report.to_dict(), "policy": result.to_dict()}
        return HTTPStatus.NOT_FOUND, {"error": "unknown endpoint"}
    except (TypeError, ValueError) as exc:
        return HTTPStatus.BAD_REQUEST, {"error": str(exc)}


class AgentProofHandler(BaseHTTPRequestHandler):
    server_version = "AgentProof/0.1"

    def do_GET(self) -> None:
        if self.path == "/":
            body = _DASHBOARD.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("content-type", "text/html; charset=utf-8")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/health":
            self._json(HTTPStatus.OK, {"status": "ok"})
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:
        length = int(self.headers.get("content-length", "0"))
        if length <= 0 or length > _MAX_BODY_BYTES:
            self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "invalid body size"})
            return
        try:
            payload = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid JSON"})
            return
        status, response = handle_api_request(self.path, payload)
        self._json(status, response)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.send_header("x-content-type-options", "nosniff")
        self.end_headers()
        self.wfile.write(body)


def serve(host: str = "127.0.0.1", port: int = 8080) -> None:
    server = ThreadingHTTPServer((host, port), AgentProofHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
