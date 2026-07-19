import json

import pytest

from agentproof.autoprofile import discover_project_profile, write_project_profile


def test_discovers_python_and_node_checks(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\n[tool.pytest.ini_options]\n[tool.ruff]\n',
        encoding="utf-8",
    )
    (tmp_path / "package.json").write_text(
        json.dumps({"name": "web-demo", "scripts": {"test": "vitest", "build": "vite build"}}),
        encoding="utf-8",
    )
    payload = discover_project_profile(tmp_path)
    names = {check["name"] for check in payload["checks"]}
    assert {"python-tests", "python-lint", "node-test", "node-build"} <= names
    assert payload["allow_partial"] is False


def test_writes_profile_and_refuses_overwrite(tmp_path):
    (tmp_path / "go.mod").write_text("module example.com/demo\n", encoding="utf-8")
    output = tmp_path / "agentproof.json"
    write_project_profile(output, root=tmp_path)
    assert output.is_file()
    with pytest.raises(ValueError, match="already exists"):
        write_project_profile(output, root=tmp_path)


def test_rejects_unknown_project(tmp_path):
    with pytest.raises(ValueError, match="no supported"):
        discover_project_profile(tmp_path)
