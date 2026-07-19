from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_manifest(paths: Iterable[str | Path], *, root: str | Path = ".") -> dict[str, object]:
    root_path = Path(root).resolve()
    files: list[dict[str, object]] = []
    for item in sorted((Path(path).resolve() for path in paths), key=str):
        if not item.is_file():
            raise FileNotFoundError(item)
        try:
            relative = item.relative_to(root_path)
        except ValueError as exc:
            raise ValueError(f"Artifact {item} is outside manifest root {root_path}") from exc
        files.append({"path": relative.as_posix(), "size": item.stat().st_size, "sha256": sha256_file(item)})
    manifest: dict[str, object] = {"schema": "agentproof.manifest.v1", "files": files}
    manifest["manifest_sha256"] = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return manifest


def verify_manifest(manifest: dict[str, object], *, root: str | Path = ".") -> list[str]:
    errors: list[str] = []
    root_path = Path(root).resolve()
    expected_digest = manifest.get("manifest_sha256")
    unsigned = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    actual_digest = hashlib.sha256(
        json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if expected_digest != actual_digest:
        errors.append("manifest digest mismatch")
    files = manifest.get("files")
    if not isinstance(files, list):
        return errors + ["manifest files must be a list"]
    for record in files:
        if not isinstance(record, dict) or "path" not in record:
            errors.append("invalid file record")
            continue
        path = (root_path / str(record["path"])).resolve()
        try:
            path.relative_to(root_path)
        except ValueError:
            errors.append(f"artifact escapes root: {record['path']}")
            continue
        if not path.is_file():
            errors.append(f"artifact missing: {record['path']}")
            continue
        if path.stat().st_size != record.get("size"):
            errors.append(f"artifact size mismatch: {record['path']}")
        if sha256_file(path) != record.get("sha256"):
            errors.append(f"artifact hash mismatch: {record['path']}")
    return errors
