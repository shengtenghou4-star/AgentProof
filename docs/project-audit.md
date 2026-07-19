# Profile-driven project audits

`agentproof project-audit` turns a repository's acceptance criteria into a tamper-evident audit bundle.

A profile declares commands, expected exit codes, optional exact claims, required artifacts, optional expected artifact digests, dependency names and selected environment names. AgentProof runs each command without a shell, captures bounded and redacted output, emits named check results, parses supported test summaries, hashes artifacts, records runtime provenance, audits the resulting claims and writes human- and machine-readable reports.

## Generate a starting profile

```bash
agentproof init-profile agentproof-profile.json --source .
```

Discovery supports common local signals:

- Python `pytest` and Ruff;
- Node `lint`, `test`, `build` and `typecheck` scripts;
- Rust `cargo test`;
- Go `go test ./...`;
- a Makefile `test` target.

Discovery never executes project code. Review the generated profile because the profile defines the acceptance boundary.

## Profile format

```json
{
  "$schema": "../schemas/project-profile.schema.json",
  "name": "example-project",
  "allow_partial": false,
  "distributions": ["example-project", "pytest", "ruff"],
  "environment_names": ["CI", "GITHUB_SHA"],
  "checks": [
    {
      "name": "tests",
      "command": ["python", "-m", "pytest", "-ra"],
      "timeout_seconds": 300,
      "expected_exit_code": 0
    },
    {
      "name": "lint",
      "command": ["python", "-m", "ruff", "check", "."],
      "claim": "AGENTPROOF_CLAIM {\"kind\":\"check_succeeded\",\"expected\":{\"name\":\"lint\",\"exit_code\":0}}"
    }
  ],
  "artifacts": [
    {
      "path": "dist/report.json",
      "expected_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    }
  ]
}
```

If a check claim is omitted, AgentProof generates an exact `check_succeeded` structured claim using its name and expected exit code. If an artifact claim is omitted, it generates a `Created path.` claim.

`allow_partial: false` makes the profile fail unless every claim is fully verified. An expected artifact digest prevents a stale or substituted file from satisfying existence alone.

The schema is available at [`schemas/project-profile.schema.json`](../schemas/project-profile.schema.json).

## Run an audit

```bash
agentproof project-audit profile.json \
  --source . \
  --output-dir audit-output \
  --fail-under 100 \
  --json project-audit-summary.json
```

## Output bundle

The output directory contains:

- `evidence.jsonl` — hash-chained commands, test summaries, named checks, artifacts and provenance;
- `provenance.json` — Python/platform, dependency, Git and selected environment fingerprint;
- `final-response.txt` — exact claims under audit;
- `audit-report.json` — claim-level verdicts and evidence score;
- `audit-report.html` — human-readable audit;
- `audit-report.sarif` — SARIF 2.1.0 for code-scanning ingestion;
- `audit-report.xml` — JUnit XML for CI test views;
- `project-audit.json` — checks, artifacts, provenance, claim report and overall pass/fail.

## Safety behavior

Project profiles and execution reject or fail on:

- shell command strings instead of argv arrays;
- empty commands and invalid timeouts;
- working directories or artifacts that escape the source root;
- unexpected command exit codes;
- missing artifacts;
- artifact digest mismatches;
- invalid evidence chains;
- zero auditable claims;
- unsupported or contradicted claims;
- partial claims when strict mode is enabled.

Command stdout and stderr are redacted for common credential forms, bounded in size and accompanied by digests of the original bytes. Selected environment values are hashed and never exposed as plaintext by the project-audit provenance collector.

## Case studies

The repository's CI performs two complete audits:

1. **AgentProof self-audit** — tests, Ruff, wheel/sdist build, artifact hashes and strict 100/100 claim verification.
2. **ClaimForge cross-repository audit** — checks out the public ClaimForge repository, runs its tests, lint and public-claim validation, hashes declared evidence files and requires a strict 100/100 result.

Both are internally operated reproducibility evidence. Neither is presented as third-party assurance.
