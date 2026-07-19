from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .adapters import convert_claude_code, convert_openai_responses, convert_otlp_json
from .io import dump_events


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentproof-import",
        description="Normalize agent runtime exports into AgentProof JSONL evidence",
    )
    parser.add_argument(
        "format",
        choices=("claude-code", "openai-responses", "otel"),
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        raw = args.input.read_text(encoding="utf-8")
        if args.format == "claude-code":
            events = convert_claude_code(raw)
        elif args.format == "openai-responses":
            events = convert_openai_responses(raw)
        else:
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("OTLP input must be a JSON object")
            events = convert_otlp_json(payload)
        dump_events(events, args.output)
        print(json.dumps({"format": args.format, "events": len(events), "output": str(args.output)}))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"agentproof-import: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
