from __future__ import annotations

import ast
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

_TOKEN_PATTERN = re.compile(
    r"(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9_]{16,}|xox[baprs]-[A-Za-z0-9-]{16,})"
)
_FORBIDDEN_CALLS = {"eval", "exec"}
_PICKLE_CALLS = {"pickle.load", "pickle.loads"}


@dataclass(frozen=True)
class SecurityFinding:
    control: str
    path: str
    line: int
    severity: str
    message: str


@dataclass(frozen=True)
class SecurityControlReport:
    scanned_files: int
    findings: tuple[SecurityFinding, ...]
    required_documents: dict[str, bool]
    passed: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def run_security_controls(
    root: str | Path = ".",
    *,
    source_paths: Iterable[str] = ("src",),
) -> SecurityControlReport:
    """Run deterministic repository controls without importing project modules."""

    project_root = Path(root).resolve()
    findings: list[SecurityFinding] = []
    scanned = 0
    for source_path in source_paths:
        candidate = (project_root / source_path).resolve()
        if project_root not in (candidate, *candidate.parents):
            raise ValueError(f"security scan path escapes root: {source_path}")
        if not candidate.exists():
            continue
        for path in sorted(candidate.rglob("*.py")):
            scanned += 1
            findings.extend(_scan_python(path, project_root))

    documents = {
        "SECURITY.md": (project_root / "SECURITY.md").is_file(),
        "docs/threat-model.md": (project_root / "docs" / "threat-model.md").is_file(),
        "docs/EVIDENCE_CLAIMS.md": (project_root / "docs" / "EVIDENCE_CLAIMS.md").is_file(),
    }
    for name, present in documents.items():
        if not present:
            findings.append(
                SecurityFinding(
                    "DOC-001",
                    name,
                    0,
                    "medium",
                    "Required security or evidence-boundary document is missing",
                )
            )

    blocking = [item for item in findings if item.severity in {"high", "critical"}]
    return SecurityControlReport(
        scanned_files=scanned,
        findings=tuple(findings),
        required_documents=documents,
        passed=not blocking and all(documents.values()),
    )


def write_security_report(
    output: str | Path,
    *,
    root: str | Path = ".",
) -> SecurityControlReport:
    report = run_security_controls(root)
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def _scan_python(path: Path, root: Path) -> list[SecurityFinding]:
    text = path.read_text(encoding="utf-8", errors="replace")
    relative = path.relative_to(root).as_posix()
    findings: list[SecurityFinding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if _TOKEN_PATTERN.search(line) and "_TOKEN_PATTERN" not in line:
            findings.append(
                SecurityFinding(
                    "SECRET-001",
                    relative,
                    line_number,
                    "high",
                    "Source contains a string resembling a live provider credential",
                )
            )
    try:
        tree = ast.parse(text, filename=relative)
    except SyntaxError as exc:
        return findings + [
            SecurityFinding(
                "AST-001",
                relative,
                int(exc.lineno or 0),
                "high",
                f"Python source could not be parsed: {exc.msg}",
            )
        ]

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node.func)
        if name in _FORBIDDEN_CALLS:
            findings.append(
                SecurityFinding(
                    "CODE-001",
                    relative,
                    node.lineno,
                    "high",
                    f"Dynamic code execution via {name} is forbidden",
                )
            )
        if name in _PICKLE_CALLS:
            findings.append(
                SecurityFinding(
                    "SER-001",
                    relative,
                    node.lineno,
                    "high",
                    "Unsafe pickle deserialization is forbidden in the verifier core",
                )
            )
        if name in {"subprocess.run", "subprocess.Popen", "subprocess.call"}:
            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant):
                    if keyword.value.value is True:
                        findings.append(
                            SecurityFinding(
                                "SHELL-001",
                                relative,
                                node.lineno,
                                "critical",
                                "subprocess shell=True bypasses argv-only execution controls",
                            )
                        )
    return findings


def _call_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _call_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""
