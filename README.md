# AgentProof

**Evidence-based verification for autonomous AI agents.**

AgentProof checks whether an agent's final claims are supported by observable execution evidence. It maps completion language to tests, independently recomputed metrics, model calls, artifact hashes, health checks, acceptance policies, and clean-environment replays.

The project starts from a simple rule: **do not trust completion language; verify external facts.**

## Capabilities

- atomic claim extraction and deterministic verification;
- test, metric, model-route, artifact, deployment, and completion checks;
- run-level detectors for grader tampering, hidden failures, stale artifacts, mock deployment evidence, unauthorized acceptance changes, seed cherry-picking, and data leakage;
- explicit acceptance policies that fail CI when required evidence is missing;
- append-only hash-chained traces and artifact integrity manifests;
- signed portable evidence bundles;
- clean copied-workspace replay with reduced environment and no shell execution;
- AgentProofBench with overall and per-category adversarial accuracy;
- OTLP/JSON import for model and tool spans;
- reusable GitHub Action, JSON/HTML reports, schemas, and CI thresholds;
- zero runtime dependencies.

## Quick start

```bash
python -m pip install -e '.[dev]'
agentproof audit examples/sample_trace.jsonl --response-file examples/sample_response.txt --json agentproof-report.json --html agentproof-report.html
agentproof gate examples/sample_trace.jsonl examples/strict-policy.json --response-file examples/sample_response.txt --json gate-report.json
agentproof record-command run.jsonl pytest -q
agentproof manifest artifacts.json model.pkl report.json --root .
agentproof verify-manifest artifacts.json --root .
agentproof import-otel otlp.json run.jsonl
agentproof replay examples/replay.json --source . --json replay-report.json
agentproof bundle evidence.json --trace run.jsonl --response-file final-response.txt --artifact model.pkl --root . --key-file .agentproof-key
agentproof verify-bundle evidence.json --root . --key-file .agentproof-key
agentproof benchmark
```

## Acceptance policies

Policies turn evidence quality into an enforceable release gate. They can require a minimum score, a valid hash chain, zero contradictions, specific verified claim types, and concrete runtime events with equality or numeric conditions.

## Adversarial detection

AgentProof does not wait for the final answer to confess a problem. It also scans the execution record for observable evaluation-gaming signals, including protected test or grader modifications, suppressed nonzero command exits, stale artifacts, mock health checks, unauthorized policy changes, best-seed-only reporting, and future-data leakage.

See `docs/benchmark.md` for the current benchmark scope.

## Replay and bundles

Replay manifests declare deterministic checks as argv arrays. AgentProof copies source into a fresh temporary workspace, strips common local-state directories, reduces inherited environment variables, executes without a shell, and emits a reproducibility report.

Evidence bundles pin the response, trace, and artifacts by SHA-256. Optional HMAC-SHA256 signatures detect post-run modification to bundle metadata.

These controls are stronger than trusting saved prose or logs, but they are not a complete hostile-code sandbox. See `docs/threat-model.md`.

## Architecture

```text
Agent final response ──> claim extraction ───────> atomic claims
Runtime trace ─────────> event normalization ────> observed facts
Runtime trace ─────────> anomaly detectors ──────> gaming findings
Acceptance policy ─────> evidence gate ──────────> pass / fail
Replay manifest ───────> clean workspace rerun ─> reproducibility evidence
Artifacts + trace ─────> signed bundle ──────────> provenance evidence
```

## Roadmap

1. Container isolation and resource policies for untrusted reruns.
2. Native adapters beyond OTLP.
3. Multi-step and paraphrase-rich benchmark expansion.
4. Cross-agent reliability reports.
5. ClaimForge and Major Forest case studies.

## Development

```bash
python -m pip install -e '.[dev]'
ruff check src tests
pytest
```

## Status

AgentProof is an early alpha. It is usable for deterministic evidence audits, acceptance gates, and reproducibility checks, but it is not yet a security boundary.
