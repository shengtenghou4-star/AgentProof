from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from .replay import ReplayResult, ReplayStepResult, copy_source, load_replay_manifest


_RUNNER = r'''from __future__ import annotations
import json
import subprocess
import sys
import time
from pathlib import Path

manifest_path, workspace_arg, result_path = sys.argv[1:4]
workspace = Path(workspace_arg).resolve()
payload = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
results = []
for raw in payload["steps"]:
    cwd = (workspace / raw.get("cwd", ".")).resolve()
    if workspace not in (cwd, *cwd.parents):
        raise SystemExit("cwd escape")
    started = time.monotonic()
    try:
        completed = subprocess.run(raw["command"], cwd=cwd, capture_output=True, text=True, timeout=int(raw.get("timeout_seconds", 300)), shell=False, check=False)
        duration = time.monotonic() - started
        expected = int(raw.get("expected_exit_code", 0))
        item = {"name": raw.get("name", "step"), "command": raw["command"], "exit_code": completed.returncode, "expected_exit_code": expected, "passed": completed.returncode == expected, "timed_out": False, "duration_seconds": round(duration, 6), "stdout": completed.stdout, "stderr": completed.stderr}
    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - started
        def text(value):
            if value is None: return ""
            return value.decode(errors="replace") if isinstance(value, bytes) else value
        item = {"name": raw.get("name", "step"), "command": raw["command"], "exit_code": None, "expected_exit_code": int(raw.get("expected_exit_code", 0)), "passed": False, "timed_out": True, "duration_seconds": round(duration, 6), "stdout": text(exc.stdout), "stderr": text(exc.stderr)}
    results.append(item)
    if not item["passed"]:
        break
output = {"reproducible": len(results) == len(payload["steps"]) and all(item["passed"] for item in results), "steps": results}
Path(result_path).write_text(json.dumps(output), encoding="utf-8")
'''


def replay_in_docker(
    manifest: Path,
    *,
    source: Path = Path("."),
    image: str,
    memory: str = "1g",
    cpus: float = 1.0,
    pids_limit: int = 256,
    allow_network: bool = False,
    keep_workspace: bool = False,
) -> ReplayResult:
    if shutil.which("docker") is None:
        raise ValueError("docker executable was not found")
    if cpus <= 0 or pids_limit < 1:
        raise ValueError("docker resource limits must be positive")
    load_replay_manifest(manifest)

    root = Path(tempfile.mkdtemp(prefix="agentproof-docker-replay-"))
    workspace = root / "workspace"
    control = root / "control"
    output = root / "output"
    control.mkdir()
    output.mkdir()
    copy_source(source.resolve(), workspace)
    manifest_copy = control / "manifest.json"
    manifest_copy.write_bytes(manifest.read_bytes())
    (control / "runner.py").write_text(_RUNNER, encoding="utf-8")
    result_name = f"result-{uuid.uuid4().hex}.json"
    result_path = output / result_name

    command = build_docker_command(
        image=image,
        workspace=workspace,
        control=control,
        output=output,
        result_name=result_name,
        memory=memory,
        cpus=cpus,
        pids_limit=pids_limit,
        allow_network=allow_network,
    )
    try:
        completed = subprocess.run(command, capture_output=True, text=True, shell=False, check=False)
        if completed.returncode != 0:
            raise ValueError(f"docker replay failed with exit code {completed.returncode}: {completed.stderr.strip()}")
        if not result_path.is_file():
            raise ValueError("docker replay did not produce a result file")
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        steps = [ReplayStepResult(**item) for item in payload.get("steps", [])]
        result = ReplayResult(
            reproducible=bool(payload.get("reproducible", False)),
            workspace=str(workspace),
            steps=steps,
            backend=f"docker:{image}",
        )
    finally:
        if not keep_workspace:
            shutil.rmtree(root, ignore_errors=True)
    return result


def build_docker_command(
    *,
    image: str,
    workspace: Path,
    control: Path,
    output: Path,
    result_name: str,
    memory: str,
    cpus: float,
    pids_limit: int,
    allow_network: bool,
) -> list[str]:
    command = [
        "docker", "run", "--rm",
        "--memory", memory,
        "--cpus", str(cpus),
        "--pids-limit", str(pids_limit),
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
    ]
    if not allow_network:
        command.extend(["--network", "none"])
    command.extend([
        "--mount", f"type=bind,src={workspace.resolve()},dst=/workspace",
        "--mount", f"type=bind,src={control.resolve()},dst=/agentproof-control,readonly",
        "--mount", f"type=bind,src={output.resolve()},dst=/agentproof-output",
        "--workdir", "/workspace",
        image,
        "python", "/agentproof-control/runner.py", "/agentproof-control/manifest.json", "/workspace", f"/agentproof-output/{result_name}",
    ])
    return command
