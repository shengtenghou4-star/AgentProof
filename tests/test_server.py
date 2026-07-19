from agentproof.server import handle_api_request


def test_audit_api_detects_false_completion():
    status, payload = handle_api_request(
        "/api/audit",
        {
            "run_id": "demo",
            "response": "All tests passed.",
            "events": [
                {
                    "event_type": "test_summary",
                    "timestamp": "t",
                    "data": {"total": 10, "passed": 9, "failed": 1, "errors": 0, "exit_code": 1},
                }
            ],
        },
    )
    assert status == 200
    assert payload["run_id"] == "demo"
    assert payload["findings"][0]["status"] == "contradicted"


def test_gate_api_returns_policy_result():
    status, payload = handle_api_request(
        "/api/gate",
        {
            "response": "All tests passed.",
            "events": [
                {
                    "event_type": "test_summary",
                    "timestamp": "t",
                    "data": {"total": 2, "passed": 2, "failed": 0, "errors": 0, "exit_code": 0},
                }
            ],
            "policy": {"minimum_score": 100, "required_claims": [{"kind": "all_tests_passed"}]},
        },
    )
    assert status == 200
    assert payload["policy"]["passed"] is True


def test_api_rejects_invalid_events():
    status, payload = handle_api_request("/api/audit", {"response": "done", "events": "bad"})
    assert status == 400
    assert "events" in payload["error"]
