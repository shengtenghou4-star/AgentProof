from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from importlib import metadata
from pathlib import Path
from typing import Iterable

from .security import safe_environment_metadata


def collect_runtime_provenance(
    *,
    root: str | Path = ".",
    distributions: Iterable[str] = (),
    environment_names: Iterable[str] = (),
) -> dict[str, object]:
    """Collect reproducible runtime facts without storing environment secrets."""

    project_root = Path(root).resolve()
    selected_environment = {
        name: os.environ[name]
        for name in sorted(set(environment_names))
        if name in os.environ
    }
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": str(Path(sys.executable).resolve()),
            "cache_tag": getattr(sys.implementation, "cache_tag", None),
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python_build": list(platform.python_build()),
        },
        "project_root": str(project_root),
        "git": _git_metadata(project_root),
        "distributions": _distribution_metadata(distributions),
        "environment": safe_environment_metadata(selected_environment),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    payload["fingerprint_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return payload


def _distribution_metadata(names: Iterable[str]) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for name in sorted(set(names)):
        try:
            version = metadata.version(name)
        except metadata.PackageNotFoundError:
            version = "not-installed"
        output.append({"name": name, "version": version})
    return output


def _git_metadata(root: Path) -> dict[str, object]:
    commit = _git(root, "rev-parse", "HEAD")
    branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    status = _git(root, "status", "--porcelain")
    remote = _git(root, "config", "--get", "remote.origin.url")
    return {
        "available": commit is not None,
        "commit": commit,
        "branch": branch,
        "dirty": bool(status) if status is not None else None,
        "status_sha256": hashlib.sha256((status or "").encode("utf-8")).hexdigest(),
        "remote_sha256": hashlib.sha256((remote or "").encode("utf-8")).hexdigest()
        if remote
        else None,
    }


def _git(root: Path, *arguments: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *arguments],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()
