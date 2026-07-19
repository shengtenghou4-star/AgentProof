from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from agentproof.project_audit import audit_project, load_project_profile


def _write_profile(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_project_audit_runs_checks_and_verifies_artifacts(tmp_path):
    source = tmp_path / "project"
    source.mkdir()
    profile = _write_profile(
        tmp_path / "profile.json",
        {
            "name": "fixture-project",
            "checks": [
                {
                    "name": "build",
                    "command": [
                        sys.executable,
                        "-c",
                        "from pathlib import Path; Path('result.json').write_text('{}')",
                    ],
                    "claim": "The task is fully completed.",
                }
            ],
            "artifacts": [
                {"path": "result.json", "claim": "Created result.json."}
            ],
        },
    )

    result = audit_project(profile, source=source, output_dir=tmp_path / "audit")

    assert result.passed is True
    assert result.checks[0]["passed"] is True
    assert result.artifacts[0]["exists"] is True
    statuses = {
        finding["claim"]["kind"]: finding["status"]
        for finding in result.audit["findings"]
    }
    assert statuses["file_created"] == "verified"
    assert (tmp_path / "audit" / "project-audit.json").is_file()
    assert (tmp_path / "audit" / "audit-report.html").is_file()


def test_project_audit_fails_when_command_exit_code_disagrees(tmp_path):
    source = tmp_path / "project"
    source.mkdir()
    profile = _write_profile(
        tmp_path / "profile.json",
        {
            "name": "failing-project",
            "checks": [
                {
                    "name": "failure",
                    "command": [sys.executable, "-c", "raise SystemExit(7)"],
                    "claim": "The task is fully completed.",
                }
            ],
        },
    )

    result = audit_project(profile, source=source, output_dir=tmp_path / "audit")

    assert result.passed is False
    assert result.checks[0]["exit_code"] == 7


def test_profile_rejects_empty_and_escaping_paths(tmp_path):
    empty = _write_profile(tmp_path / "empty.json", {"name": "empty"})
    with pytest.raises(ValueError, match="at least one"):
        load_project_profile(empty)

    source = tmp_path / "source"
    source.mkdir()
    escaping = _write_profile(
        tmp_path / "escaping.json",
        {
            "name": "escape",
            "artifacts": [{"path": "../secret.txt", "claim": "Created secret.txt."}],
        },
    )
    with pytest.raises(ValueError, match="escapes"):
        audit_project(escaping, source=source, output_dir=tmp_path / "audit")
