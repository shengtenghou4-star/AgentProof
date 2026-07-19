# AgentProof

**Evidence-based verification for autonomous AI agents.**

AgentProof checks whether an agent's final claims are supported by observable execution evidence. It maps statements such as “all tests passed”, “AUC reached 0.757”, “I used model X”, “the file was created”, or “the API is deployed” to test summaries, independently recomputed metrics, runtime model calls, artifact hashes, and health checks.

The project starts from a simple rule: **do not trust completion language; verify external facts.**

## Why this exists

Agent traces show what was logged. They do not automatically prove that an agent's summary is accurate, complete, reproducible, or free from grader gaming. AgentProof adds a deterministic verification layer between agent execution and human acceptance.

Current alpha capabilities:

- conservative extraction of atomic, testable claims;
- verification of test, metric, model-routing, artifact, deployment, and completion claims;
- contradiction detection for false “all passed” and deployment claims;
- independent-metric evidence distinction;
- optional hash-chain trace integrity checks;
- JSON and standalone HTML audit reports;
- CI threshold support through `--fail-under`;
- zero runtime dependencies.

## Quick start

```bash
python -m pip install -e '.[dev]'
agentproof audit examples/sample_trace.jsonl \
  --response-file examples/sample_response.txt \
  --json agentproof-report.json \
  --html agentproof-report.html
```

The included sample deliberately contains inflated claims: four tests failed and the deployment health check returned 503. AgentProof marks those claims as contradicted while independently verifying the recorded AUC and model route.

## Event format

AgentProof consumes newline-delimited JSON. Every row contains an observed event:

```json
{"event_type":"test_summary","timestamp":"2026-07-19T09:01:08Z","data":{"total":100,"passed":96,"failed":4,"errors":0,"exit_code":1}}
```

Supported alpha event types:

| Event | Key fields | Claim verified |
|---|---|---|
| `test_summary` | `total`, `passed`, `failed`, `errors`, `exit_code` | all tests passed |
| `metric` | `name`, `value`, `independently_computed` | metric value |
| `model_call` | `provider`, `model`, `request_id` | actual model route |
| `artifact` | `path`, `exists`, `sha256` | file creation and integrity |
| `healthcheck` | `url`, `status_code` | deployment status |
| `command`, `tool_call` | execution metadata | completion support |

## Architecture

```text
Agent final response ──> claim extraction ──> atomic claims
Runtime trace ─────────> event normalization ─> observed facts
                                         │
                                         ▼
                              deterministic verifiers
                                         │
                                         ▼
                 verified / partial / unsupported / contradicted
```

## Roadmap

1. Signed evidence bundles and reproducible replay manifests.
2. OpenTelemetry and agent-framework adapters.
3. Sandboxed reruns for tests, metrics, and artifacts.
4. Adversarial false-completion and grader-gaming benchmark.
5. Cross-agent reliability reports and GitHub Action integration.
6. ClaimForge and Major Forest case studies.

## Development

```bash
python -m pip install -e '.[dev]'
ruff check src tests
pytest
```

## Status

AgentProof is an early alpha. The initial release establishes the evidence model, deterministic verifiers, trace integrity checks, CLI, reports, examples, tests, and CI. It is not yet a security boundary and should not be treated as one.
