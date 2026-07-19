# AgentProof

**Evidence-based verification for autonomous AI agents.**

AgentProof checks whether an agent's final claims are supported by observable execution evidence. It maps statements such as “all tests passed”, “AUC reached 0.757”, “I used model X”, “the file was created”, or “the API is deployed” to test summaries, independently recomputed metrics, runtime model calls, artifact hashes, health checks, and clean-environment replays.

The project starts from a simple rule: **do not trust completion language; verify external facts.**

## Capabilities

- atomic claim extraction and deterministic verification;
- test, metric, model-route, artifact, deployment, and completion checks;
- explicit acceptance policies that fail CI when required evidence is missing;
- contradiction detection for inflated completion language;
- append-only hash-chained traces;
- artifact integrity manifests;
- signed portable evidence bundles;
- clean copied-workspace replay with reduced environment and no shell execution;
- adversarial false-completion benchmark;
- OTLP/JSON import for model and tool spans;
- reusable GitHub Action, JSON/HTML reports, schemas, and CI thresholds;
- zero runtime dependencies.

## Quick start

```bash
python -m pip install -e '.[dev]'
agentproof audit examples/sample_trace.jsonl \
  --response-file examples/sample_response.txt \
  --json agentproof-report.json \
  --html agentproof-report.html

agentproof gate examples/sample_trace.jsonl examples/strict-policy.json \
  --response-file examples/sample_response.txt \
  --json gate-report.json

agentproof record-command run.jsonl pytest -q
agentproof manifest artifacts.json model.pkl report.json --root .
agentproof verify-manifest artifacts.json --root .
agentproof import-otel otlp.json run.jsonl
agentproof replay examples/replay.json --source . --json replay-report.json

# use a random 32+ byte secret kept outside version control
agentproof bundle evidence.json \
  --trace run.jsonl \
  --response-file final-response.txt \
  --artifact model.pkl \
  --artifact report.json \
  --root . \
  --key-file .agentproof-key
agentproof verify-bundle evidence.json --root . --key-file .agentproof-key
agentproof benchmark
```

The included sample deliberately contains inflated claims: four tests failed and the deployment health check returned 503. AgentProof marks those claims as contradicted while independently verifying the recorded AUC and model route.

## Acceptance policies

A policy converts evidence quality into an enforceable release gate. It can require a minimum audit score, a valid hash chain, zero contradictions, specific verified claim types, and concrete runtime events with numeric or equality conditions.

```json
{
  "minimum_score": 90,
  "forbid_contradictions": true,
  "required_events": [
    {"event_type": "test_summary", "where": {"total": {"gt": 0}, "failed": 0, "exit_code": 0}},
    {"event_type": "healthcheck", "where": {"status_code": {"gte": 200, "lt": 300}}}
  ]
}
```

## Replay and bundles

Replay manifests declare deterministic checks as argv arrays. AgentProof copies the source into a fresh temporary workspace, strips common local-state directories, reduces inherited environment variables, executes without a shell, and emits a reproducibility report.

Evidence bundles pin the response, trace, and artifacts by SHA-256. Optional HMAC-SHA256 signatures detect any post-run modification to bundle metadata. This creates a portable unit that can be independently verified later.

These controls are stronger than trusting saved prose or logs, but they are not a complete hostile-code sandbox. See `docs/threat-model.md`.

## Architecture

```text
Agent final response ──> claim extraction ─> atomic claims
Runtime trace ─────────> event normalization ─> observed facts
Acceptance policy ─────> evidence gate ────────> pass / fail
Replay manifest ───────> clean workspace rerun ─> reproducibility evidence
Artifacts + trace ─────> signed evidence bundle ─> provenance evidence
                                         │
                                         ▼
                              deterministic verifiers
                                         │
                                         ▼
                 verified / partial / unsupported / contradicted
```

## Roadmap

1. Container isolation and resource policies for untrusted reruns.
2. Agent-framework adapters beyond OTLP.
3. Expanded adversarial false-completion and grader-gaming benchmark.
4. Cross-agent reliability reports.
5. ClaimForge and Major Forest case studies.

## Development

```bash
python -m pip install -e '.[dev]'
ruff check src tests
pytest
```

## Status

AgentProof is an early alpha. It is already usable for deterministic evidence audits, acceptance gates, and reproducibility checks, but it is not yet a security boundary.
