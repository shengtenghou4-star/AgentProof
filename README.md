# AgentProof

[![CI](https://github.com/shengtenghou4-star/AgentProof/actions/workflows/ci.yml/badge.svg)](https://github.com/shengtenghou4-star/AgentProof/actions/workflows/ci.yml)
[![Live Demo](https://img.shields.io/badge/live-demo-5ee7ff)](https://shengtenghou4-star.github.io/AgentProof/)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)
![Version](https://img.shields.io/badge/version-0.5.0-orange)
![License](https://img.shields.io/badge/license-Apache--2.0-green)

**Evidence-based verification for autonomous AI agents.**

AgentProof checks whether an agent's final claims are supported by observable execution evidence. It maps completion language to tests, independently recomputed metrics, attested model routes, artifact hashes, health checks, acceptance policies, reproducible reruns, and exact project-level acceptance checks.

> **Do not trust completion language. Verify external facts.**

**[Open the interactive demo →](https://shengtenghou4-star.github.io/AgentProof/)** · **[Inspect the evidence claims matrix →](docs/EVIDENCE_CLAIMS.md)** · **[Read the coding-stage completion boundary →](docs/INTERNAL_COMPLETION.md)**

## Validated evidence at a glance

The v0.5.0 internal validation lane currently demonstrates:

| Evidence | Result |
|---|---:|
| AgentProof test suite | 79 passed on Python 3.10, 3.11 and 3.12 |
| Strict self-audit | 100/100; 5/5 claims verified; hash chain valid |
| Core controlled benchmark | 38/38 correct; 0/25 unsafe false accepts |
| Language/format perturbation suite | 304/304 correct; 0/200 unsafe false accepts |
| Layout/context holdout-style suite | 1,216/1,216 correct; 0/800 unsafe false accepts |
| Combined deterministic corpus | 1,558 cases; 1,025 unsafe; zero false accepts |
| Deterministic parser fuzzing | 5,000 generated cases; fixed seed; 0.27 seconds in CI |
| Deterministic security controls | 39 Python files scanned; zero blocking findings |
| Source coverage | 78.4% line coverage; 65.2% branch coverage |
| Package validation | wheel + sdist build; clean-venv wheel install and CLI smoke pass |
| ClaimForge cross-project audit | 54 tests, lint and public-claim validation pass; audit 100/100 |

These are **controlled, repository-owned validation results**. They are strong regression and engineering evidence, not a claim of universal real-world deception-detection accuracy, independent assurance, or production impact.

## Complete verification stack

- **Atomic claims** — conservative natural-language extraction plus explicit `AGENTPROOF_CLAIM` JSON records.
- **Negation safety** — statements such as “not all tests passed” are not converted into positive claims.
- **Four verdicts** — `verified`, `partial`, `unsupported`, and `contradicted` preserve evidence quality instead of flattening it.
- **Claim verifiers** — tests, named checks, metrics, models, artifacts, deployments and overall completion.
- **Model-route attestation** — an OpenAI-compatible proxy observes requested and returned model identities, status, request IDs, latency and body digests without retaining prompt or response text.
- **Evaluation-gaming detectors** — protected evaluator changes, hidden failures, stale artifacts, mock health checks, acceptance rewriting, route substitution, seed cherry-picking and future/label leakage.
- **Project audits** — execute declared tests, lint, builds and validation commands; enforce expected exit codes and artifact digests; produce a single strict pass/fail result.
- **Evidence integrity** — append-only SHA-256 event chains, artifact manifests and signed portable bundles.
- **Privacy controls** — common secret redaction, bounded output capture, full-output digests and hashed transcript content.
- **Runtime provenance** — Python, platform, dependency, Git and selected environment fingerprints.
- **Security controls** — deterministic AST checks reject `shell=True`, dynamic `eval`/`exec`, unsafe pickle deserialization, credential-like source strings and missing boundary documents.
- **Reproducible replay** — clean local workspaces and network-denied, resource-limited Docker reruns.
- **Runtime adapters** — Claude Code, Codex, OpenAI Responses, generic OpenAI Agents/LangGraph-style traces and OTLP/JSON.
- **Delivery** — CLI, Python API, local REST API/dashboard, GitHub Action, interactive static demo, JSON, HTML, SARIF and JUnit.
- **Zero mandatory runtime dependencies** — the core package uses the Python standard library.

## Five-minute proof

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e '.[dev]'

# Audit an existing trace and final response.
agentproof audit examples/sample_trace.jsonl \
  --response-file examples/sample_response.txt \
  --json audit.json \
  --html audit.html \
  --sarif audit.sarif \
  --junit audit.xml

# Discover this repository's checks, then audit the whole project.
agentproof init-profile agentproof-profile.json --source .
agentproof project-audit agentproof-profile.json \
  --source . \
  --output-dir project-audit \
  --fail-under 100

# Run every deterministic benchmark suite.
agentproof benchmark --suite all --json benchmark-report.json
```

## Model-route attestation

```bash
agentproof-proxy \
  --upstream https://api.example.com/v1 \
  --provider example \
  --trace route-evidence.jsonl \
  --port 8787
```

Point the agent's OpenAI-compatible base URL at `http://127.0.0.1:8787`. The proxy forwards authorization but records only header names, route facts and cryptographic body digests. It identifies requested/returned substitutions and failed calls. It cannot observe traffic that bypasses the proxy, so production use should pair it with network egress controls.

## Runtime imports

```bash
agentproof-import claude-code claude-run.jsonl claude-evidence.jsonl
agentproof-import codex codex-run.jsonl codex-evidence.jsonl
agentproof-import openai-responses responses.jsonl openai-evidence.jsonl
agentproof-import agent-traces agent-events.jsonl agent-evidence.jsonl
agentproof-import otel otlp.json otel-evidence.jsonl
```

Prompt, response, tool-argument and tool-result content is represented by SHA-256 where the source format permits. Stable semantic fields—provider, model, run ID, call ID, status and explicit errors—remain available for verification.

## Project audit bundle

A profile defines commands, expected exit codes, optional explicit claims, required artifacts, optional expected artifact digests, dependency names and selected environment variable names.

```json
{
  "$schema": "schemas/project-profile.schema.json",
  "name": "example-project",
  "allow_partial": false,
  "checks": [
    {
      "name": "tests",
      "command": ["python", "-m", "pytest", "-ra"],
      "expected_exit_code": 0
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

The output directory contains:

- `evidence.jsonl` — hash-chained command, check, artifact and provenance evidence;
- `provenance.json` — runtime/dependency/Git/environment fingerprint;
- `final-response.txt` — exact claims under audit;
- `audit-report.json` and `audit-report.html`;
- `audit-report.sarif` and `audit-report.xml`;
- `project-audit.json` — complete project result.

## Architecture

```text
Agent final response ──> claim extraction ───────> atomic or structured claims
Runtime exports ───────> privacy-safe adapters ─> normalized evidence
Commands ──────────────> bounded recorder ───────> output digests + test summaries
API traffic ───────────> route attestation ──────> provider/model evidence
Project profile ───────> check orchestration ────> strict audit bundle
Runtime trace ─────────> anomaly detectors ──────> gaming findings
Acceptance policy ─────> evidence gate ──────────> pass / fail
Replay manifest ───────> local/container rerun ─> reproducibility evidence
Artifacts + trace ─────> signed bundle ──────────> provenance evidence
Audit reports ─────────> JSON/HTML/SARIF/JUnit ─> human and machine review
```

## Internal validation versus external validation

The coding-stage definition of done includes implementation, tests, fuzzing, controlled benchmarks, security controls, package validation, self-audit, ClaimForge cross-project audit, documentation and the public demo. See [`docs/INTERNAL_COMPLETION.md`](docs/INTERNAL_COMPLETION.md).

The following are deliberately deferred because more code cannot manufacture them:

- independent penetration testing or security assessment;
- independently designed and labeled holdout attacks;
- unrelated external users, adoption, citations or institutional endorsement;
- production deployment and verified operational impact;
- private enterprise traces or confidential incident data.

## Documentation

- [Internal completion boundary](docs/INTERNAL_COMPLETION.md)
- [Evidence claims matrix](docs/EVIDENCE_CLAIMS.md)
- [Technical report](docs/TECHNICAL_REPORT.md)
- [Project audits](docs/project-audit.md)
- [Benchmarks](docs/benchmark.md)
- [Model-route attestation](docs/model-route-attestation.md)
- [Native adapters](docs/native-adapters.md)
- [Threat model](docs/threat-model.md)
- [Container replay](docs/container-replay.md)
- [Reliability reports](docs/reliability-reports.md)
- [Local API](docs/api.md)
- [Security policy](SECURITY.md)
- [Contribution standard](CONTRIBUTING.md)

## Development

```bash
python -m pip install -e '.[dev]'
ruff check src tests scripts
pytest
coverage run -m pytest
coverage report
python scripts/fuzz_claims.py
python scripts/security_controls.py
python -m build
```

## Honest limitations

- Controlled benchmarks are not independently sampled real-world accuracy estimates.
- Application-layer model-route evidence is not hardware-backed attestation.
- Hash chains and signatures depend on the integrity of their verifier, keys and trust roots.
- Docker replay reduces ambient privilege but is not a safe host for arbitrary hostile native code.
- Redaction covers common credential forms, not every possible secret representation.
- Deterministic security controls cover explicit prohibited patterns, not every possible vulnerability.
- Project audits verify declared acceptance criteria; undeclared business correctness remains outside the profile.
- Runtime adapters are tested against supported record shapes and may require updates as vendor formats evolve.
- The ClaimForge case study is an internally operated, cross-repository reproducibility test—not third-party assurance.

## License and citation

Apache-2.0. Citation metadata is available in [`CITATION.cff`](CITATION.cff).
