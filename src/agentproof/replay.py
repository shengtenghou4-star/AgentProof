from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ReplayStep:
    name: str
    command: list[str]
    cwd: str = "."
    timeout_seconds: int = 300
    expected_exit_code: int = 0


@dataclass(frozen=True)
class ReplayStepResult:
    name: str
    command: list[str]
    exit_code: int | None
    expected_exit_code: int
    passed: bool
    timed_out: bool
    duration_seconds: float
    stdout: str
    stderr: str


@dataclass(frozen=True)
class ReplayResult:
    reproducible: bool
    workspace: str
    steps: list[ReplayStepResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "reproducible": self.reproducible,
            "workspace": self.workspace,
            "steps": [asdict(step) for step in self.steps],
        }


def load_replay_manifest(path: Path) -> list[ReplayStep]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_steps = payload.get("steps") if isinstance(payload, dict) else None
    if not isinstance(raw_steps, list) or not raw_steps:
        raise ValueError("replay manifest must contain a non-empty 'steps' list")

    steps: list[ReplayStep] = []
    for index, raw in enumerate(raw_steps):
        if not isinstance(raw, dict):
            raise ValueError(f"step {index} must be an object")
        command = raw.get("command")
        if isinstance(command, str):
            raise ValueError(f"step {index} command must be an argv list, not a shell string")
        if not isinstance(command, list) or not command or not all(isinstance(part, str) for part in command):
            raise ValueError(f"step {index} command must be a non-empty string list")
        steps.append(
            ReplayStep(
                name=str(raw.get("name") or f"step-{index + 1}"),
                command=list(command),
                cwd=str(raw.get("cwd") or "."),
                timeout_seconds=int(raw.get("timeout_seconds", 300)),
                expected_exit_code=int(raw.get("expected_exit_code", 0)),
            )
        )
    return steps


def replay(
    manifest: Path,
    *,
    source: Path = Path("."),
    keep_workspace: bool = False,
    clean_environment: bool = True,
) -> ReplayResult:
    steps = load_replay_manifest(manifest)
    workspace_path = Path(tempfile.mkdtemp(prefix="agentproof-replay-"))
    copied_root = workspace_path / "workspace"
    _copy_source(source.resolve(), copied_root)

    environment = _clean_environment() if clean_environment else dict(os.environ)
    results: list[ReplayStepResult] = []
    try:
        for step in steps:
            cwd = (copied_root / step.cwd).resolve()
            if copied_root.resolve() not in (cwd, *cwd.parents):
                raise ValueError(f"step '{step.name}' cwd escapes replay workspace")
            if not cwd.exists():
                raise FileNotFoundError(f"step '{step.name}' cwd does not exist: {step.cwd}")
            started = time.monotonic()
            try:
                completed = subprocess.run(
                    step.command,
                    cwd=cwd,
                    env=environment,
                    capture_output=True,
                    text=True,
                    timeout=step.timeout_seconds,
                    shell=False,
                    check=False,
                )
                duration = time.monotonic() - started
                results.append(
                    ReplayStepResult(
                        name=step.name,
                        command=step.command,
                        exit_code=completed.returncode,
                        expected_exit_code=step.expected_exit_code,
                        passed=completed.returncode == step.expected_exit_code,
                        timed_out=False,
                        duration_seconds=round(duration, 6),
                        stdout=completed.stdout,
                        stderr=completed.stderr,
                    )
                )
            except subprocess.TimeoutExpired as exc:
                duration = time.monotonic() - started
                results.append(
                    ReplayStepResult(
                        name=step.name,
                        command=step.command,
                        exit_code=None,
                        expected_exit_code=step.expected_exit_code,
                        passed=False,
                        timed_out=True,
                        duration_seconds=round(duration, 6),
                        stdout=_decode_timeout_stream(exc.stdout),
                        stderr=_decode_timeout_stream(exc.stderr),
                    )
                )
                break
            if not results[-1].passed:
                break
    finally:
        reproducible = bool(results) and len(results) == len(steps) and all(step.passed for step in results)
        result = ReplayResult(reproducible=reproducible, workspace=str(copied_root), steps=results)
        if not keep_workspace:
            shutil.rmtree(workspace_path, ignore_errors=True)
    return result


def _copy_source(source: Path, destination: Path) -> None:
    ignored_names = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".ruff_cache", "node_modules"}

    def ignore(_directory: str, names: list[str]) -> set[str]:
        return {name for name in names if name in ignored_names}

    shutil.copytree(source, destination, ignore=ignore)


def _clean_environment() -> dict[str, str]:
    allowed = {
        "PATH",
        "PATHEXT",
        "SYSTEMROOT",
        "WINDIR",
        "COMSPEC",
        "TMP",
        "TEMP",
        "HOME",
        "USERPROFILE",
        "LANG",
        "LC_ALL",
        "PYTHONUTF8",
        "PYTHONIOENCODING",
    }
    return {key: value for key, value in os.environ.items() if key in allowed}


def _decode_timeout_stream(value: str | bytes | None) -> str:
    if value is None:
        return ""
    return value.decode(errors="replace") if isinstance(value, bytes) else value
