import json
import sys
from pathlib import Path

import pytest

from agentproof.replay import load_replay_manifest, replay


def write_manifest(path: Path, command: list[str], **extra):
    payload = {"steps": [{"name": "check", "command": command, **extra}]}
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_replay_passes_in_copied_workspace(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "probe.py").write_text("from pathlib import Path\nassert Path('data.txt').read_text() == 'ok'\n", encoding="utf-8")
    (source / "data.txt").write_text("ok", encoding="utf-8")
    manifest = tmp_path / "replay.json"
    write_manifest(manifest, [sys.executable, "probe.py"])

    result = replay(manifest, source=source)

    assert result.reproducible is True
    assert result.steps[0].passed is True


def test_replay_stops_on_failure(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    manifest = tmp_path / "replay.json"
    payload = {
        "steps": [
            {"name": "fail", "command": [sys.executable, "-c", "raise SystemExit(3)"], "expected_exit_code": 0},
            {"name": "never", "command": [sys.executable, "-c", "raise SystemExit(0)"]},
        ]
    }
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    result = replay(manifest, source=source)

    assert result.reproducible is False
    assert len(result.steps) == 1
    assert result.steps[0].exit_code == 3


def test_replay_rejects_shell_string(tmp_path):
    manifest = tmp_path / "replay.json"
    manifest.write_text(json.dumps({"steps": [{"command": "echo unsafe"}]}), encoding="utf-8")

    with pytest.raises(ValueError, match="argv list"):
        load_replay_manifest(manifest)


def test_replay_rejects_cwd_escape(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    manifest = tmp_path / "replay.json"
    write_manifest(manifest, [sys.executable, "-c", "print('x')"], cwd="..")

    with pytest.raises(ValueError, match="escapes"):
        replay(manifest, source=source)
