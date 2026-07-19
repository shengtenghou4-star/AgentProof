# AgentProof

**Evidence-based verification for autonomous AI agents.**

AgentProof checks whether an agent's final claims are supported by observable execution evidence. It maps completion language to tests, independently recomputed metrics, attested model routes, artifact hashes, health checks, acceptance policies, and reproducible reruns.

The project starts from a simple rule: **do not trust completion language; verify external facts.**

## Capabilities

- atomic claim extraction and deterministic verification;
- test, metric, model-route, artifact, deployment, and completion checks;
- an OpenAI-compatible route-attestation proxy that records requested and returned models without storing prompts, responses, or authorization values;
- native privacy-preserving importers for Claude Code JSON/stream-json and OpenAI Responses objects/event streams;
- run-level detectors for grader tampering, hidden failures, stale artifacts, mock deployment evidence, unauthorized acceptance changes, model substitution, seed cherry-picking, and data leakage;
- explicit acceptance policies that fail CI when required evidence is missing;
- append-only hash-chained traces and artifact integrity manifests;
- signed portable evidence bundles;
- local clean-workspace replay and resource-limited Docker replay;
- AgentProofBench with exact accuracy, false-accept rate, Wilson intervals, confusion matrices, and per-category results;
- cross-run reliability aggregation;
- OTLP/JSON import for model and tool spans;
- dependency-free local REST API and interactive dashboard;
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
agentproof-import claude-code claude-run.jsonl claude-evidence.jsonl
agentproof-import openai-responses responses.jsonl openai-evidence.jsonl
agentproof-import otel otlp.json otel-evidence.jsonl
agentproof replay examples/replay.json --source . --json replay-report.json
agentproof replay examples/replay.json --source . --docker-image python:3.12-slim --json container-report.json
agentproof bundle evidence.json --trace run.jsonl --response-file final-response.txt --artifact model.pkl --root . --key-file .agentproof-key
agentproof verify-bundle evidence.json --root . --key-file .agentproof-key
agentproof summarize run-1.json run-2.json --json reliability.json
agentproof benchmark
agentproof serve --host 127.0.0.1 --port 8080
```

To attest the actual upstream model route:

```bash
agentproof-proxy \
  --upstream https://api.example.com/v1 \
  --provider example \
  --trace route-evidence.jsonl \
  --port 8787
```

Point the agent's OpenAI-compatible base URL at `http://127.0.0.1:8787`. The proxy forwards authorization but records only header names and body hashes, not secret values or prompt/response text.

## Evidence gates and adversarial detection

Policies convert evidence quality into enforceable release criteria: minimum score, valid hash chain, zero contradictions, verified claim types, and concrete runtime events with equality or numeric conditions.

AgentProof also scans execution records for observable gaming signals rather than waiting for the final answer to disclose them. The detectors cover protected evaluator-file modifications, suppressed command failures, stale artifact reuse, mock health checks, unauthorized acceptance changes, requested/actual model substitution, best-seed-only reporting, and future-data leakage.

## Replay, provenance, and integration

Local replay copies source into a fresh temporary workspace, strips common local-state directories, reduces inherited environment variables, executes argv commands without a shell, and emits a reproducibility report.

Docker replay adds network denial, capability dropping, `no-new-privileges`, memory/CPU/process limits, and disposable mounts. Evidence bundles pin responses, traces, and artifacts by SHA-256 and can be signed with HMAC-SHA256.

The route proxy provides application-layer model provenance by observing the request model, provider request ID, returned model, status, latency, and cryptographic body digests. It marks substitutions and failed calls as contradictions.

Native transcript adapters normalize Claude Code and OpenAI Responses records into model, tool, and result evidence. Prompt, response, tool argument, and tool result content is stored as SHA-256 rather than plaintext.

The local server exposes `/api/audit`, `/api/gate`, `/health`, and an interactive dashboard at `/`. It accepts inline evidence only and does not execute uploaded commands.

## Architecture

```text
Agent final response ──> claim extraction ───────> atomic claims
Runtime exports ────────> native adapters ───────> normalized evidence
Runtime trace ─────────> event normalization ────> observed facts
API traffic ───────────> route attestation ──────> provider/model evidence
Runtime trace ─────────> anomaly detectors ──────> gaming findings
Acceptance policy ─────> evidence gate ──────────> pass / fail
Replay manifest ───────> local/container rerun ──> reproducibility evidence
Artifacts + trace ─────> signed bundle ──────────> provenance evidence
Audit reports ─────────> reliability aggregation > cross-run comparison
API/dashboard ─────────> integration surface ────> human and machine use
```

## Documentation

- `docs/model-route-attestation.md`
- `docs/native-adapters.md`
- `docs/threat-model.md`
- `docs/container-replay.md`
- `docs/benchmark.md`
- `docs/reliability-reports.md`
- `docs/api.md`

## Roadmap

1. Codex and additional coding-agent transcript adapters.
2. Multi-step and paraphrase-rich benchmark expansion.
3. ClaimForge and Major Forest case studies.
4. Public alpha packaging and hosted demo.

## Development

```bash
python -m pip install -e '.[dev]'
ruff check src tests
pytest
```

## Status

AgentProof is an early alpha. It is usable for deterministic evidence audits, model-route attestation, transcript normalization, acceptance gates, provenance verification, reproducibility checks, and local API integrations. It is not a formal security boundary.
