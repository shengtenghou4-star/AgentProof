from agentproof.provenance import collect_runtime_provenance


def test_runtime_provenance_has_stable_shape(tmp_path, monkeypatch):
    monkeypatch.setenv("CI", "true")
    payload = collect_runtime_provenance(
        root=tmp_path,
        distributions=["agentproof", "definitely-missing-package"],
        environment_names=["CI"],
    )
    assert payload["schema_version"] == "1.0"
    assert len(payload["fingerprint_sha256"]) == 64
    assert payload["python"]["version"]
    versions = {item["name"]: item["version"] for item in payload["distributions"]}
    assert versions["definitely-missing-package"] == "not-installed"
    environment = payload["environment"]["variables"]
    assert environment[0]["name"] == "CI"
    assert "value" not in environment[0]
