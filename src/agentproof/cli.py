from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .adapters import convert_otlp_json
from .audit import audit_run
from .benchmark import run_benchmark
from .bundle import build_evidence_bundle, verify_evidence_bundle, write_bundle
from .manifest import build_manifest, verify_manifest
from .recorder import record_command
from .replay import replay
from .reporting import render_html
from .signing import load_key


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentproof", description="Evidence-based verification for AI agents")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser("audit", help="Audit an agent response against an evidence trace")
    audit.add_argument("trace", type=Path)
    response = audit.add_mutually_exclusive_group(required=True)
    response.add_argument("--response", help="Agent response text")
    response.add_argument("--response-file", type=Path, help="File containing the agent response")
    audit.add_argument("--json", type=Path, dest="json_output")
    audit.add_argument("--html", type=Path, dest="html_output")
    audit.add_argument("--fail-under", type=float, default=None)

    record = subparsers.add_parser("record-command", help="Execute a command and append tamper-evident evidence")
    record.add_argument("trace", type=Path)
    record.add_argument("argv", nargs=argparse.REMAINDER)

    manifest = subparsers.add_parser("manifest", help="Create an artifact integrity manifest")
    manifest.add_argument("output", type=Path)
    manifest.add_argument("paths", nargs="+", type=Path)
    manifest.add_argument("--root", type=Path, default=Path("."))

    verify = subparsers.add_parser("verify-manifest", help="Verify an artifact integrity manifest")
    verify.add_argument("manifest", type=Path)
    verify.add_argument("--root", type=Path, default=Path("."))

    bundle = subparsers.add_parser("bundle", help="Create a portable evidence bundle")
    bundle.add_argument("output", type=Path)
    bundle.add_argument("--trace", type=Path, required=True)
    bundle.add_argument("--response-file", type=Path, required=True)
    bundle.add_argument("--artifact", action="append", default=[], type=Path)
    bundle.add_argument("--root", type=Path, default=Path("."))
    bundle.add_argument("--key-file", type=Path)
    bundle.add_argument("--key-id", default="default")

    verify_bundle = subparsers.add_parser("verify-bundle", help="Verify bundle signature and referenced files")
    verify_bundle.add_argument("bundle", type=Path)
    verify_bundle.add_argument("--root", type=Path, default=Path("."))
    verify_bundle.add_argument("--key-file", type=Path)

    otel = subparsers.add_parser("import-otel", help="Convert OTLP/JSON spans into AgentProof JSONL")
    otel.add_argument("input", type=Path)
    otel.add_argument("output", type=Path)

    rerun = subparsers.add_parser("replay", help="Re-run declared checks in a clean copied workspace")
    rerun.add_argument("manifest", type=Path)
    rerun.add_argument("--source", type=Path, default=Path("."))
    rerun.add_argument("--json", type=Path, dest="json_output")
    rerun.add_argument("--keep-workspace", action="store_true")
    rerun.add_argument("--inherit-environment", action="store_true")

    subparsers.add_parser("benchmark", help="Run the built-in false-completion benchmark")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "audit":
            response = args.response if args.response is not None else args.response_file.read_text(encoding="utf-8")
            report = audit_run(args.trace, response)
            payload = report.to_dict()
            rendered = json.dumps(payload, indent=2, sort_keys=True)
            if args.json_output:
                args.json_output.write_text(rendered + "\n", encoding="utf-8")
            if args.html_output:
                args.html_output.write_text(render_html(report), encoding="utf-8")
            print(rendered)
            if args.fail_under is not None and report.score < args.fail_under:
                return 2
            return 0
        if args.command == "record-command":
            if not args.argv:
                raise ValueError("record-command requires an argv command")
            return record_command(args.trace, args.argv)
        if args.command == "manifest":
            payload = build_manifest(args.paths, root=args.root)
            args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(json.dumps(payload, indent=2))
            return 0
        if args.command == "verify-manifest":
            payload = json.loads(args.manifest.read_text(encoding="utf-8"))
            errors = verify_manifest(payload, root=args.root)
            print(json.dumps({"valid": not errors, "errors": errors}, indent=2))
            return int(bool(errors))
        if args.command == "bundle":
            key = load_key(args.key_file) if args.key_file else None
            payload = build_evidence_bundle(
                trace=args.trace,
                response=args.response_file,
                artifacts=args.artifact,
                root=args.root,
                signing_key=key,
                key_id=args.key_id,
            )
            write_bundle(args.output, payload)
            print(json.dumps({"output": str(args.output), "signed": key is not None}, indent=2))
            return 0
        if args.command == "verify-bundle":
            payload = json.loads(args.bundle.read_text(encoding="utf-8"))
            key = load_key(args.key_file) if args.key_file else None
            errors = verify_evidence_bundle(payload, root=args.root, signing_key=key)
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
        if args.command == "replay":
            result = replay(
                args.manifest,
                source=args.source,
                keep_workspace=args.keep_workspace,
                clean_environment=not args.inherit_environment,
            )
            payload = result.to_dict()
            rendered = json.dumps(payload, indent=2, sort_keys=True)
            if args.json_output:
                args.json_output.write_text(rendered + "\n", encoding="utf-8")
            print(rendered)
            return 0 if result.reproducible else 3
        if args.command == "benchmark":
            result = run_benchmark()
            print(json.dumps(result, indent=2))
            return 0 if result["accuracy"] == 1.0 else 4
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"agentproof: {exc}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
