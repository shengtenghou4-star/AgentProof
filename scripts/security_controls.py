from __future__ import annotations

import argparse
import json
from pathlib import Path

from agentproof.security_controls import write_security_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AgentProof deterministic security controls")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=Path("security-controls.json"))
    args = parser.parse_args()
    report = write_security_report(args.output, root=args.root)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
