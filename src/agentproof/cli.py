from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path

from .adapters import convert_otlp_json
from .audit import audit_run
from .benchmark import run_benchmark
from .manifest import build_manifest, verify_manifest
from .recorder import TraceRecorder
from .report import write_html, write_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentproof", description="Audit AI-agent claims against execution evidence")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit", help="Audit a JSONL trace and final agent response")
    audit.add_argument("trace", type=Path, help="Path to newline-delimited JSON event trace")
    source = audit.add_mutually_exclusive_group(required=True)
    source.add_argument("--response", help="Final agent response as text")
    source.add_argument("--response-file", type=Path, help="File containing the final agent response")
    audit.add_argument("--run-id", default="local")
    audit.add_argument("--json", dest="json_output", type=Path)
    audit.add_argument("--html", dest="html_output", type=Path)
    audit.add_argument("--fail-under", type=float, default=0.0)

    record = subparsers.add_parser("record-command", help="Run a command and append tamper-evident evidence")
    record.add_argument("trace", type=Path)
    record.add_argument("command", help="Shell-like command string; executed without a shell")
    record.add_argument("--cwd", type=Path)
    record.add_argument("--timeout", type=float)

    manifest = subparsers.add_parser("manifest", help="Create an artifact integrity manifest")
    manifest.add_argument("output", type=Path)
    manifest.add_argument("artifacts", nargs="+", type=Path)
    manifest.add_argument("--root", type=Path, default=Path("."))

    verify = subparsers.add_parser("verify-manifest", help="Verify an artifact integrity manifest")
    verify.add_argument("manifest", type=Path)
    verify.add_argument("--root", type=Path, default=Path("."))

    otel = subparsers.add_parser("import-otel", help="Convert OTLP/JSON spans into AgentProof JSONL")
    otel.add_argument("input", type=Path)
    otel.add_argument("output", type=Path)

    subparsers.add_parser("benchmark", help="Run the built-in false-completion benchmark")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "audit":
            return _audit(args)
        if args.command == "record-command":
            result = TraceRecorder(args.trace).run_command(
                shlex.split(args.command), cwd=args.cwd, timeout=args.timeout
            )
            return result.returncode
        if args.command == "manifest":
            payload = build_manifest(args.artifacts, root=args.root)
            args.output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
            print(json.dumps(payload, indent=2))
            return 0
        if args.command == "verify-manifest":
            payload = json.loads(args.manifest.read_text(encoding="utf-8"))
            errors = verify_manifest(payload, root=args.root)
            print(json.dumps({"valid": not errors, "errors": errors}, indent=2))
            return int(bool(errors))
        if args.command == "import-otel":
            payload = json.loads(args.input.read_text(encoding="utf-8"))
            events = convert_otlp_json(payload)
            with args.output.open("w", encoding="utf-8") as handle:
                for event in events:
                    handle.write(json.dumps({
                        "event_type": event.event_type,
                        "timestamp": event.timestamp,
                        "data": event.data,
                        "source": event.source,
                    }, sort_keys=True) + "\n")
            print(json.dumps({"events": len(events), "output": str(args.output)}, indent=2))
            return 0
        if args.command == "benchmark":
            result = run_benchmark()
            print(json.dumps(result, indent=2))
            return int(result["accuracy"] < 1.0)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"agentproof: {exc}", file=sys.stderr)
        return 2
    return 2


def _audit(args: argparse.Namespace) -> int:
    response = args.response if args.response is not None else args.response_file.read_text(encoding="utf-8")
    report = audit_run(args.trace, response, run_id=args.run_id)
    if args.json_output:
        write_json(report, args.json_output)
    if args.html_output:
        write_html(report, args.html_output)
    print(json.dumps(report.to_dict(), indent=2))
    return 1 if report.score < args.fail_under or not report.integrity_ok else 0


if __name__ == "__main__":
    raise SystemExit(main())
