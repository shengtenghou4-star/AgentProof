from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .proxy import ProxyConfig, serve_proxy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentproof-proxy",
        description="Attest the actual provider and model used by OpenAI-compatible traffic",
    )
    parser.add_argument("--upstream", required=True, help="Absolute upstream base URL")
    parser.add_argument("--trace", type=Path, required=True, help="Tamper-evident JSONL output")
    parser.add_argument("--provider", help="Provider label; defaults to upstream hostname")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--max-body-mb", type=int, default=20)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if not 1 <= args.port <= 65535:
            raise ValueError("port must be between 1 and 65535")
        config = ProxyConfig(
            upstream=args.upstream,
            trace=args.trace,
            provider=args.provider,
            timeout_seconds=args.timeout,
            max_body_bytes=args.max_body_mb * 1024 * 1024,
        )
        serve_proxy(args.host, args.port, config)
    except (OSError, ValueError) as exc:
        print(f"agentproof-proxy: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
