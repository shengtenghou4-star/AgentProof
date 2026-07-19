import json
import sys

from agentproof.project_audit import audit_project


def test_project_audit_generates_provenance_and_ci_formats(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    profile = tmp_path / "profile.json"
    profile.write_text(
        json.dumps(
            {
                "name": "strict-demo",
                "allow_partial": False,
                "checks": [
                    {
                        "name": "smoke",
                        "command": [sys.executable, "-c", "print('ok')"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "output"
    result = audit_project(profile, source=source, output_dir=output)
    assert result.passed is True
    assert result.audit["score"] == 100.0
    assert result.provenance["fingerprint_sha256"]
    assert (output / "provenance.json").is_file()
    assert (output / "audit-report.sarif").is_file()
    assert (output / "audit-report.xml").is_file()


def test_expected_artifact_digest_is_enforced(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "result.txt").write_text("actual", encoding="utf-8")
    profile = tmp_path / "profile.json"
    profile.write_text(
        json.dumps(
            {
                "name": "digest-demo",
                "artifacts": [
                    {"path": "result.txt", "expected_sha256": "0" * 64}
                ],
            }
        ),
        encoding="utf-8",
    )
    result = audit_project(profile, source=source, output_dir=tmp_path / "output")
    assert result.passed is False
    assert result.artifacts[0]["digest_matches"] is False
