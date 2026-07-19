from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .audit import audit_run
from .recorder import TraceRecorder
from .reporting import render_html


@dataclass(frozen=True)
class ProjectCheck:
    name: str
    command: list[str]
    claim: str
    cwd: str = "."
    timeout_seconds: int = 300
    expected_exit_code: int = 0


@dataclass(frozen=True)
class ProjectArtifact:
    path: str
    claim: str


@dataclass(frozen=True)
class ProjectProfile:
    name: str
    checks: list[ProjectCheck]
    artifacts: list[ProjectArtifact]


@dataclass(frozen=True)
class ProjectAuditResult:
    profile: str
    source: str
    trace: str
    final_response: str
    checks: list[dict[str, Any]]
    artifacts: list[dict[str, Any]]
    audit: dict[str, Any]
    passed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_project_profile(path: str | Path) -> ProjectProfile:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("project profile must be a JSON object")

    name = str(payload.get("name") or "project-audit")
    raw_checks = payload.get("checks", [])
    raw_artifacts = payload.get("artifacts", [])
    if not isinstance(raw_checks, list) or not isinstance(raw_artifacts, list):
        raise ValueError("checks and artifacts must be lists")
    if not raw_checks and not raw_artifacts:
        raise ValueError("project profile must define at least one check or artifact")

    checks: list[ProjectCheck] = []
    for index, raw in enumerate(raw_checks):
        if not isinstance(raw, dict):
            raise ValueError(f"check {index} must be an object")
        command = raw.get("command")
        if not isinstance(command, list) or not command or not all(isinstance(part, str) for part in command):
            raise ValueError(f"check {index} command must be a non-empty string list")
        claim = str(raw.get("claim") or "").strip()
        if not claim:
            raise ValueError(f"check {index} must define a claim")
        timeout_seconds = int(raw.get("timeout_seconds", 300))
        if timeout_seconds < 1:
            raise ValueError(f"check {index} timeout_seconds must be positive")
        checks.append(
            ProjectCheck(
                name=str(raw.get("name") or f"check-{index + 1}"),
                command=list(command),
                claim=claim,
                cwd=str(raw.get("cwd") or "."),
                timeout_seconds=timeout_seconds,
                expected_exit_code=int(raw.get("expected_exit_code", 0)),
            )
        )

    artifacts: list[ProjectArtifact] = []
    for index, raw in enumerate(raw_artifacts):
        if not isinstance(raw, dict):
            raise ValueError(f"artifact {index} must be an object")
        artifact_path = str(raw.get("path") or "").strip()
        claim = str(raw.get("claim") or "").strip()
        if not artifact_path or not claim:
            raise ValueError(f"artifact {index} must define path and claim")
        artifacts.append(ProjectArtifact(path=artifact_path, claim=claim))

    return ProjectProfile(name=name, checks=checks, artifacts=artifacts)


def audit_project(
    profile_path: str | Path,
    *,
    source: str | Path = ".",
    output_dir: str | Path = "agentproof-project-audit",
) -> ProjectAuditResult:
    profile = load_project_profile(profile_path)
    source_root = Path(source).resolve()
    if not source_root.is_dir():
        raise ValueError(f"project source is not a directory: {source_root}")

    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    trace_path = output_root / "evidence.jsonl"
    if trace_path.exists():
        trace_path.unlink()
    recorder = TraceRecorder(trace_path, source="project-audit")

    check_results: list[dict[str, Any]] = []
    claims: list[str] = []
    for check in profile.checks:
        cwd = _resolve_inside(source_root, check.cwd, label=f"check '{check.name}' cwd")
        result = recorder.run_command(
            check.command,
            cwd=cwd,
            timeout=check.timeout_seconds,
        )
        passed = result.returncode == check.expected_exit_code
        check_results.append(
            {
                "name": check.name,
                "command": check.command,
                "cwd": str(cwd.relative_to(source_root)),
                "expected_exit_code": check.expected_exit_code,
                "exit_code": result.returncode,
                "passed": passed,
            }
        )
        claims.append(check.claim)

    artifact_results: list[dict[str, Any]] = []
    for artifact in profile.artifacts:
        path = _resolve_inside(source_root, artifact.path, label="artifact")
        exists = path.is_file()
        digest = _sha256_file(path) if exists else None
        recorder.emit(
            "artifact",
            path=artifact.path.replace("\\", "/"),
            exists=exists,
            sha256=digest,
            size=path.stat().st_size if exists else None,
        )
        artifact_results.append(
            {
                "path": artifact.path,
                "exists": exists,
                "sha256": digest,
                "passed": exists,
            }
        )
        claims.append(artifact.claim)

    final_response = "\n".join(claims) + "\n"
    response_path = output_root / "final-response.txt"
    response_path.write_text(final_response, encoding="utf-8")

    report = audit_run(trace_path, final_response, run_id=profile.name)
    audit_payload = report.to_dict()
    (output_root / "audit-report.json").write_text(
        json.dumps(audit_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_root / "audit-report.html").write_text(render_html(report), encoding="utf-8")

    passed = (
        all(item["passed"] for item in check_results)
        and all(item["passed"] for item in artifact_results)
        and report.integrity_ok
        and not any(finding.status.value == "contradicted" for finding in report.findings)
    )
    result = ProjectAuditResult(
        profile=profile.name,
        source=str(source_root),
        trace=str(trace_path),
        final_response=str(response_path),
        checks=check_results,
        artifacts=artifact_results,
        audit=audit_payload,
        passed=passed,
    )
    (output_root / "project-audit.json").write_text(
        json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def _resolve_inside(root: Path, relative: str, *, label: str) -> Path:
    candidate = (root / relative).resolve()
    if root not in (candidate, *candidate.parents):
        raise ValueError(f"{label} escapes project source: {relative}")
    return candidate


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
