from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .audit import audit_run
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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "audit":
        return 2
    response = args.response if args.response is not None else args.response_file.read_text(encoding="utf-8")
    try:
        report = audit_run(args.trace, response, run_id=args.run_id)
    except (OSError, ValueError) as exc:
        print(f"agentproof: {exc}", file=sys.stderr)
        return 2

    if args.json_output:
        write_json(report, args.json_output)
    if args.html_output:
        write_html(report, args.html_output)
    print(json.dumps(report.to_dict(), indent=2))
    return 1 if report.score < args.fail_under or not report.integrity_ok else 0


if __name__ == "__main__":
    raise SystemExit(main())
