from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from .integrity import event_hash
from .models import Event
from .security import capture_text

_PYTEST_COUNT = re.compile(
    r"(?P<count>\d+)\s+(?P<kind>passed|failed|error|errors|skipped|xfailed|xpassed)\b",
    re.IGNORECASE,
)


class TraceRecorder:
    """Append-only JSONL recorder with an embedded SHA-256 hash chain."""

    def __init__(
        self,
        path: str | Path,
        *,
        source: str = "recorder",
        max_output_bytes: int = 65536,
    ) -> None:
        self.path = Path(path)
        self.source = source
        self.max_output_bytes = max_output_bytes
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._previous_hash = ""
        if self.path.exists() and self.path.stat().st_size:
            self._previous_hash = self._read_last_hash()

    def emit(self, event_type: str, **data: Any) -> Event:
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        clean = Event(
            event_type=event_type,
            timestamp=timestamp,
            data=data,
            source=self.source,
        )
        digest = event_hash(clean, self._previous_hash)
        chained = Event(
            event_type=event_type,
            timestamp=timestamp,
            data={**data, "prev_hash": self._previous_hash, "event_hash": digest},
            source=self.source,
        )
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(chained), sort_keys=True) + "\n")
        self._previous_hash = digest
        return chained

    def record_model_call(self, provider: str, model: str, **metadata: Any) -> Event:
        return self.emit("model_call", provider=provider, model=model, **metadata)

    def record_metric(
        self,
        name: str,
        value: float,
        *,
        independently_computed: bool = False,
        **metadata: Any,
    ) -> Event:
        return self.emit(
            "metric",
            name=name,
            value=float(value),
            independently_computed=independently_computed,
            **metadata,
        )

    def record_artifact(self, path: str | Path) -> Event:
        artifact = Path(path)
        exists = artifact.is_file()
        digest = _sha256_file(artifact) if exists else None
        return self.emit("artifact", path=str(artifact), exists=exists, sha256=digest)

    def run_command(
        self,
        command: Sequence[str],
        *,
        cwd: str | Path | None = None,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        started = datetime.now(timezone.utc)
        try:
            result = subprocess.run(
                list(command),
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            timed_out = False
        except subprocess.TimeoutExpired as exc:
            result = subprocess.CompletedProcess(
                args=list(command),
                returncode=124,
                stdout=_timeout_text(exc.stdout),
                stderr=_timeout_text(exc.stderr),
            )
            timed_out = True
        duration_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        stdout_capture = capture_text(result.stdout, max_bytes=self.max_output_bytes)
        stderr_capture = capture_text(result.stderr, max_bytes=self.max_output_bytes)
        self.emit(
            "command",
            command=list(command),
            cwd=str(cwd) if cwd else None,
            exit_code=result.returncode,
            stdout=stdout_capture.text,
            stderr=stderr_capture.text,
            stdout_sha256=stdout_capture.sha256,
            stderr_sha256=stderr_capture.sha256,
            stdout_original_bytes=stdout_capture.original_bytes,
            stderr_original_bytes=stderr_capture.original_bytes,
            stdout_truncated=stdout_capture.truncated,
            stderr_truncated=stderr_capture.truncated,
            redactions=stdout_capture.redactions + stderr_capture.redactions,
            duration_ms=duration_ms,
            timed_out=timed_out,
        )
        summary = parse_pytest_summary(
            "\n".join(part for part in (result.stdout, result.stderr) if part),
            exit_code=result.returncode,
        )
        if summary is not None:
            self.emit("test_summary", **summary)
        return result

    def _read_last_hash(self) -> str:
        last = ""
        with self.path.open("r", encoding="utf-8") as handle:
            for raw in handle:
                if raw.strip():
                    last = raw
        try:
            return str(json.loads(last)["data"]["event_hash"])
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Existing trace does not end in a valid chained event") from exc


def record_command(trace: str | Path, argv: Sequence[str]) -> int:
    """Execute argv, record tamper-evident evidence, mirror output, and return its exit code."""

    if not argv:
        raise ValueError("record_command requires a non-empty argv sequence")
    result = TraceRecorder(trace).run_command(argv)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        import sys

        print(result.stderr, end="", file=sys.stderr)
    return int(result.returncode)


def parse_pytest_summary(text: str, *, exit_code: int) -> dict[str, int] | None:
    counts: dict[str, int] = {
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "xfailed": 0,
        "xpassed": 0,
    }
    found = False
    for match in _PYTEST_COUNT.finditer(text):
        found = True
        kind = match.group("kind").lower()
        if kind == "error":
            kind = "errors"
        counts[kind] += int(match.group("count"))
    if not found:
        return None
    total = sum(counts.values())
    return {
        "total": total,
        **counts,
        "exit_code": int(exit_code),
    }


def _timeout_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    return value.decode(errors="replace") if isinstance(value, bytes) else value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
