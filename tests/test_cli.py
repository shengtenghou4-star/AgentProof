from agentproof.cli import build_parser


def test_cli_exposes_primary_workflows():
    parser = build_parser()
    for argv in (
        ["audit", "trace.jsonl", "--response", "done"],
        ["gate", "trace.jsonl", "policy.json", "--response-file", "answer.txt"],
        ["replay", "replay.json", "--docker-image", "python:3.12-slim"],
        ["summarize", "report.json"],
        ["serve"],
        ["benchmark"],
    ):
        assert parser.parse_args(argv).command == argv[0]
