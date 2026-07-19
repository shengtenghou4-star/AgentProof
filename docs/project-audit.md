# Profile-driven project audits

`agentproof project-audit` turns a repository's own acceptance checks into a tamper-evident audit bundle.

A profile declares commands, the claims those commands are meant to support, and required output artifacts. AgentProof runs each command without a shell, records command output and exit status into a SHA-256 hash chain, extracts supported test summaries, hashes declared artifacts, audits the resulting completion claims, and writes machine-readable and HTML reports.

```json
{
  "name": "example-project",
  "checks": [
    {
      "name": "tests",
      "command": ["python", "-m", "pytest", "-ra"],
      "claim": "All tests passed.",
      "timeout_seconds": 300,
      "expected_exit_code": 0
    }
  ],
  "artifacts": [
    {
      "path": "dist/report.json",
      "claim": "Created dist/report.json."
    }
  ]
}
```

Run it with:

```bash
agentproof project-audit profile.json \
  --source . \
  --output-dir audit-output \
  --fail-under 100
```

The output directory contains:

- `evidence.jsonl`: hash-chained execution and artifact evidence;
- `final-response.txt`: the exact claims under audit;
- `audit-report.json`: claim-level verdicts and evidence score;
- `audit-report.html`: a human-readable audit;
- `project-audit.json`: command, artifact and overall project result.

Project profiles reject shell strings, source-directory escapes and artifact path traversal. A passing project audit requires expected command exit codes, all declared artifacts, a valid hash chain, at least one auditable claim, and no unsupported or contradicted finding.
