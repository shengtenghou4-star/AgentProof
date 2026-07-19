import pytest

from agentproof.docker_replay import build_docker_command, replay_in_docker


def test_docker_command_has_default_isolation(tmp_path):
    command = build_docker_command(
        image="python:3.12-slim",
        workspace=tmp_path / "workspace",
        control=tmp_path / "control",
        output=tmp_path / "output",
        result_name="result.json",
        memory="512m",
        cpus=0.5,
        pids_limit=64,
        allow_network=False,
    )
    assert command[:3] == ["docker", "run", "--rm"]
    assert ["--network", "none"] == command[command.index("--network"):command.index("--network") + 2]
    assert "--cap-drop" in command
    assert "no-new-privileges" in command
    assert "python:3.12-slim" in command


def test_docker_replay_requires_docker(monkeypatch, tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"steps":[{"name":"x","command":["python","-V"]}]}', encoding="utf-8")
    monkeypatch.setattr("agentproof.docker_replay.shutil.which", lambda _name: None)
    with pytest.raises(ValueError, match="not found"):
        replay_in_docker(manifest, source=tmp_path, image="python:3.12-slim")
