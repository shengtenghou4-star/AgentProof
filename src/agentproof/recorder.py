from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from .integrity import event_hash
from .models import Event


class TraceRecorder:
    """Append-only JSONL recorder with an embedded SHA-256 hash chain."""

    def __init__(self, path: str | Path, *, source: str = "recorder") -> None:
        self.path = Path(path)
        self.source = source
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._previous_hash = ""
        if self.path.exists() and self.path.stat().st_size:
            self._previous_hash = self._read_last_hash()

    def emit(self, event_type: str, **data: Any) -> Event:
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        clean = Event(event_type=event_type, timestamp=timestamp, data=data, source=self.source)
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

    def record_metric(self, name: str, value: float, *, independently_computed: bool = False, **metadata: Any) -> Event:
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
                stdout=exc.stdout or "",
                stderr=exc.stderr or "",
            )
            timed_out = True
        duration_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        self.emit(
            "command",
            command=list(command),
            cwd=str(cwd) if cwd else None,
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            duration_ms=duration_ms,
            timed_out=timed_out,
        )
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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
