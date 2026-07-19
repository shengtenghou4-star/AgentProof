# AgentProof

**Evidence-based verification for autonomous AI agents.**

AgentProof checks whether an agent's final claims are supported by observable execution evidence. It maps completion language to tests, independently recomputed metrics, model calls, artifact hashes, health checks, acceptance policies, and reproducible reruns.

The project starts from a simple rule: **do not trust completion language; verify external facts.**

## Capabilities

- atomic claim extraction and deterministic verification;
- test, metric, model-route, artifact, deployment, and completion checks;
- run-level detectors for grader tampering, hidden failures, stale artifacts, mock deployment evidence, unauthorized acceptance changes, seed cherry-picking, and data leakage;
- explicit acceptance policies that fail CI when required evidence is missing;
- append-only hash-chained traces and artifact integrity manifests;
- signed portable evidence bundles;
- local clean-workspace replay and resource-limited Docker replay;
- AgentProofBench with overall and per-category adversarial accuracy;
- cross-run reliability aggregation;
- OTLP/JSON import for model and tool spans;
- reusable GitHub Action, JSON/HTML reports, schemas, and CI thresholds;
- zero mandatory runtime dependencies.

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
agentproof replay examples/replay.json --source . --docker-image python:3.12-slim --json container-report.json
agentproof bundle evidence.json --trace run.jsonl --response-file final-response.txt --artifact model.pkl --root . --key-file .agentproof-key
agentproof verify-bundle evidence.json --root . --key-file .agentproof-key
agentproof summarize run-1.json run-2.json --json reliability.json
agentproof benchmark
```

## Evidence gates and adversarial detection

Policies convert evidence quality into enforceable release criteria: minimum score, valid hash chain, zero contradictions, verified claim types, and concrete runtime events with equality or numeric conditions.

AgentProof also scans execution records for observable gaming signals rather than waiting for the final answer to disclose them. The alpha detectors cover protected evaluator-file modifications, suppressed command failures, stale artifact reuse, mock health checks, unauthorized acceptance changes, best-seed-only reporting, and future-data leakage.

## Replay and provenance

Local replay copies source into a fresh temporary workspace, strips common local-state directories, reduces inherited environment variables, executes argv commands without a shell, and emits a reproducibility report.

Docker replay adds network denial, capability dropping, `no-new-privileges`, memory/CPU/process limits, and disposable mounts. See `docs/container-replay.md` for assumptions and limitations.

Evidence bundles pin responses, traces, and artifacts by SHA-256. Optional HMAC-SHA256 signatures detect post-run modification to bundle metadata.

## Architecture

```text
Agent final response ──> claim extraction ───────> atomic claims
Runtime trace ─────────> event normalization ────> observed facts
Runtime trace ─────────> anomaly detectors ──────> gaming findings
Acceptance policy ─────> evidence gate ──────────> pass / fail
Replay manifest ───────> local/container rerun ──> reproducibility evidence
Artifacts + trace ─────> signed bundle ──────────> provenance evidence
Audit reports ─────────> reliability aggregation > cross-run comparison
```

## Documentation

- `docs/threat-model.md`
- `docs/container-replay.md`
- `docs/benchmark.md`
- `docs/reliability-reports.md`

## Roadmap

1. Native adapters beyond OTLP.
2. Multi-step and paraphrase-rich benchmark expansion.
3. ClaimForge and Major Forest case studies.
4. Public alpha packaging and demo dashboard.

## Development

```bash
python -m pip install -e '.[dev]'
ruff check src tests
pytest
```

## Status

AgentProof is an early alpha. It is usable for deterministic evidence audits, acceptance gates, provenance verification, and reproducibility checks. It is not a formal security boundary.
