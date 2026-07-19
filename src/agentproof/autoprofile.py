from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def discover_project_profile(root: str | Path = ".") -> dict[str, Any]:
    """Discover deterministic local checks without executing project code."""

    project_root = Path(root).resolve()
    if not project_root.is_dir():
        raise ValueError(f"project root is not a directory: {project_root}")

    checks: list[dict[str, object]] = []
    distributions: list[str] = []
    pyproject = project_root / "pyproject.toml"
    pytest_configured = any(
        (project_root / name).is_file()
        for name in ("pytest.ini", "tox.ini", "setup.cfg")
    )
    if pyproject.is_file():
        text = pyproject.read_text(encoding="utf-8", errors="replace")
        pytest_configured = pytest_configured or "[tool.pytest" in text or "pytest" in text
        if pytest_configured or (project_root / "tests").is_dir():
            checks.append(_check("python-tests", ["python", "-m", "pytest", "-ra"]))
        if "[tool.ruff" in text or "ruff" in text:
            checks.append(_check("python-lint", ["python", "-m", "ruff", "check", "."]))
        distributions.extend(_project_names_from_pyproject(text))
    elif (project_root / "tests").is_dir():
        checks.append(_check("python-tests", ["python", "-m", "pytest", "-ra"]))

    package_json = project_root / "package.json"
    if package_json.is_file():
        payload = json.loads(package_json.read_text(encoding="utf-8"))
        scripts = payload.get("scripts", {}) if isinstance(payload, dict) else {}
        if isinstance(scripts, dict):
            for script in ("lint", "test", "build", "typecheck"):
                if isinstance(scripts.get(script), str):
                    checks.append(_check(f"node-{script}", ["npm", "run", script]))
        if isinstance(payload, dict) and isinstance(payload.get("name"), str):
            distributions.append(str(payload["name"]))

    if (project_root / "Cargo.toml").is_file():
        checks.append(_check("rust-tests", ["cargo", "test", "--all-targets"]))
    if (project_root / "go.mod").is_file():
        checks.append(_check("go-tests", ["go", "test", "./..."]))
    makefile = project_root / "Makefile"
    if makefile.is_file():
        make_text = makefile.read_text(encoding="utf-8", errors="replace")
        if re.search(r"(?m)^test\s*:", make_text):
            checks.append(_check("make-tests", ["make", "test"]))

    checks = _deduplicate_checks(checks)
    if not checks:
        raise ValueError("no supported test, lint, build, or typecheck commands were discovered")

    return {
        "name": project_root.name or "project-audit",
        "allow_partial": False,
        "distributions": sorted(set(distributions)),
        "environment_names": ["CI", "GITHUB_ACTIONS", "GITHUB_REF_NAME", "GITHUB_SHA"],
        "checks": checks,
        "artifacts": [],
    }


def write_project_profile(
    output: str | Path,
    *,
    root: str | Path = ".",
    overwrite: bool = False,
) -> dict[str, Any]:
    destination = Path(output)
    if destination.exists() and not overwrite:
        raise ValueError(f"profile already exists: {destination}")
    payload = discover_project_profile(root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def _check(name: str, command: list[str]) -> dict[str, object]:
    return {
        "name": name,
        "command": command,
        "timeout_seconds": 900,
        "expected_exit_code": 0,
    }


def _project_names_from_pyproject(text: str) -> list[str]:
    match = re.search(r"(?m)^name\s*=\s*[\"'](?P<name>[^\"']+)[\"']\s*$", text)
    return [match.group("name")] if match else []


def _deduplicate_checks(checks: list[dict[str, object]]) -> list[dict[str, object]]:
    seen: set[tuple[str, ...]] = set()
    output: list[dict[str, object]] = []
    for check in checks:
        command = tuple(str(item) for item in check["command"])
        if command in seen:
            continue
        seen.add(command)
        output.append(check)
    return output
