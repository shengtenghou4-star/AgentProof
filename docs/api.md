# Local API and dashboard

Start the dependency-free local server:

```bash
agentproof serve --host 127.0.0.1 --port 8080
```

Endpoints:

- `GET /` — interactive audit dashboard;
- `GET /health` — health check;
- `POST /api/audit` — audit inline events and a final response;
- `POST /api/gate` — audit and enforce an inline policy.

Example request:

```json
{
  "run_id": "trial-1",
  "response": "All tests passed.",
  "events": [
    {"event_type": "test_summary", "timestamp": "now", "data": {"total": 5, "passed": 4, "failed": 1, "errors": 0, "exit_code": 1}}
  ]
}
```

The server binds to localhost by default, suppresses request logs, limits request bodies to 2 MiB, and never executes uploaded commands. It is a local demonstration and integration API, not an internet-facing hardened service.
