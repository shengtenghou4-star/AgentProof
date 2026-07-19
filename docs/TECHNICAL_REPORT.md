# AgentProof technical report

## Abstract

AgentProof is an evidence-verification framework for autonomous AI agents and agent-produced software. It addresses a narrow but consequential failure mode: an agent may state that tests passed, a metric was achieved, a particular model was used, an artifact was created, or a service was deployed without sufficient external evidence—or despite contradictory execution records.

The system converts final-answer language into atomic claims, normalizes runtime evidence from commands, model gateways and agent frameworks, verifies each claim with deterministic rules, detects observable evaluation-gaming patterns, and emits machine-readable audit results. It also executes project-level acceptance profiles, fingerprints runtime provenance, verifies artifacts, and replays declared checks in clean local or containerized environments.

## 1. Problem definition

Agent observability answers: **what events were recorded?** AgentProof asks a stricter question:

> Does the observable evidence support the agent's exact completion claims?

The distinction matters because a trace may be complete but still contradict the final answer, a runtime may record only self-reported metrics, an agent may modify the evaluator, or a model gateway may return a different model than the one requested.

AgentProof therefore separates:

1. **Claim** — a statement made by the agent or project profile.
2. **Evidence event** — an observable fact from execution or an external verifier.
3. **Verification rule** — a deterministic mapping from claim and evidence to a verdict.
4. **Integrity control** — a mechanism that makes later evidence modification detectable.
5. **Acceptance policy** — a release condition imposed on the resulting report.

## 2. Verdict model

Each atomic claim receives one of four states:

- `verified` — sufficient matching evidence exists and no material contradiction is present;
- `partial` — matching evidence exists but an independence, provenance or completeness requirement is absent;
- `unsupported` — the required evidence class is missing or insufficient;
- `contradicted` — observed evidence directly conflicts with the claim or exposes a disqualifying failure.

The four-state model avoids two common errors: treating missing evidence as proof of falsehood, and treating weak self-reported evidence as full verification.

## 3. Claim extraction

AgentProof supports two paths.

### 3.1 Conservative natural-language extraction

Regular-expression rules identify a deliberately limited set of testable claims:

- all tests passed;
- a metric reached a stated value;
- a provider/model was used;
- a named file was created;
- an API or service was deployed;
- work was fully completed.

Negation checks prevent phrases such as “not all tests passed” from becoming positive claims.

### 3.2 Structured claims

Automation can emit an exact record:

```text
AGENTPROOF_CLAIM {"kind":"check_succeeded","expected":{"name":"lint","exit_code":0}}
```

Structured claims remove linguistic ambiguity while retaining the same verification and reporting pipeline.

## 4. Evidence model

Evidence is normalized into append-only JSONL events. Major event classes include:

- command execution and bounded stdout/stderr captures;
- parsed test summaries;
- named acceptance-check results;
- independently computed or self-reported metrics;
- requested and returned model routes;
- tool calls and tool results;
- artifact existence, size and SHA-256;
- deployment health checks;
- runtime errors;
- data access, evaluator modification and acceptance-criteria changes;
- runtime and dependency provenance.

Each recorder-generated event includes the previous event hash and its own SHA-256, producing a tamper-evident chain.

## 5. Privacy and bounded evidence

Raw execution output creates two risks: accidental secret disclosure and unbounded evidence growth. AgentProof applies:

- common bearer-token, API-key, GitHub-token and Slack-token redaction;
- assignment-value redaction for common secret names;
- configurable byte limits with head/tail preservation;
- a SHA-256 digest of the complete original output;
- original and captured byte counts;
- truncation and redaction metadata.

Transcript adapters prefer content digests for prompts, responses, tool arguments and tool outputs. Provider, model, run identifiers, status and errors remain available where required for verification.

## 6. Model-route attestation

The OpenAI-compatible proxy observes the network boundary between an agent and an upstream model API. It records:

- requested model;
- returned model, when supplied by the upstream response;
- provider identity configured at the proxy;
- HTTP status and provider request ID;
- latency;
- request and response body SHA-256;
- whether requested and returned model identities differ.

A successful response with a different returned model contradicts a claim that the requested model executed the task. A successful request where the upstream omits model identity can provide only partial support.

This is application-layer evidence. Calls that bypass the proxy are not observed, and the proxy does not provide hardware-backed proof of provider execution.

## 7. Project-level audits

A project profile defines:

- acceptance commands;
- working directories;
- timeouts;
- expected exit codes;
- explicit or automatically generated claims;
- required artifacts;
- optional expected artifact digests;
- dependency names and selected environment names for provenance;
- whether partial findings are accepted.

The orchestrator runs commands without a shell, records their evidence, emits named `check_result` events, hashes artifacts, builds a provenance fingerprint, audits all claims and writes:

- hash-chained JSONL evidence;
- exact final claims;
- JSON and HTML reports;
- SARIF 2.1.0;
- JUnit XML;
- runtime provenance;
- a single project-level pass/fail result.

Strict profiles fail for unexpected exit codes, missing artifacts, digest mismatches, invalid evidence chains, unsupported claims, partial claims or contradictions.

## 8. Evaluation-gaming detection

Run-level detectors examine evidence beyond the final answer. Covered signals include:

- protected test or evaluator files modified by the agent;
- failed commands hidden from the final summary;
- zero-test success claims;
- stale artifact reuse;
- mock health checks represented as deployment evidence;
- unauthorized acceptance-criteria changes;
- requested/returned model substitution;
- best-seed-only metric reporting;
- future-information and label leakage.

These detectors identify observable patterns. They do not infer hidden intent or guarantee detection of unknown attack families.

## 9. Reproducibility and provenance

Local replay copies source into a new workspace, excludes common local-state directories, reduces inherited environment variables and executes declared argv arrays without a shell.

Docker replay additionally supports:

- network denial by default;
- dropped Linux capabilities;
- `no-new-privileges`;
- memory, CPU and process limits;
- read-only source and disposable output mounts.

Runtime provenance includes Python implementation/version, platform, selected installed-package versions, Git commit/branch/dirty state and hashed selected environment values. A canonical JSON representation receives a top-level SHA-256 fingerprint.

## 10. Runtime integrations

Current adapters normalize:

- Claude Code JSON and stream-JSON;
- Codex JSON/JSONL variants;
- OpenAI Responses objects and event streams;
- generic OpenAI Agents SDK / LangGraph callback-style records;
- OpenTelemetry / OTLP JSON.

Unknown records are retained as hashed spans rather than silently discarded.

## 11. Controlled evaluation

Three deterministic suites share 38 seed oracles:

| Suite | Cases | Unsafe cases | False accepts | Oracle agreement |
|---|---:|---:|---:|---:|
| Core | 38 | 25 | 0 | 38/38 |
| Language/format perturbation | 304 | 200 | 0 | 304/304 |
| Layout/context holdout-style | 1,216 | 800 | 0 | 1,216/1,216 |
| **Combined** | **1,558** | **1,025** | **0** | **1,558/1,558** |

The primary safety metric is the false-accept rate: cases whose oracle is `unsupported` or `contradicted` but whose observed result is `verified` or `partial`.

The holdout-style suite changes formatting and surrounding context, not underlying attack families. Accordingly, these results demonstrate deterministic regression robustness over controlled oracles. They do not estimate performance on independently sampled real-world deception.

A separate fixed-seed fuzz harness generates 5,000 positive, negated and noise-heavy claim strings and enforces a runtime budget.

## 12. Self-audit and cross-project evidence

The AgentProof CI lane audits AgentProof itself. The profile runs the test suite, Ruff and package build; verifies wheel and source-distribution artifacts; records provenance; requires a 100/100 report; runs all controlled benchmark suites; and installs the wheel in a clean virtual environment.

A second lane checks out ClaimForge as a separate repository and uses AgentProof to execute its tests, lint and public-claim validation while hashing its README and locked validation summary. This demonstrates cross-repository project auditing without private data or external assistance. It remains self-operated evidence, not independent assurance.

## 13. Threat model and limitations

AgentProof assumes the verifier, its signing keys and at least one evidence trust root have not all been replaced by a fully privileged attacker. Hash chains make modification detectable relative to that root; they do not make a compromised host honest.

Other explicit boundaries:

- no hardware remote attestation;
- no formal proof of arbitrary program correctness;
- no guarantee against unknown secret formats;
- no guarantee that vendor trace schemas remain stable;
- no verification of acceptance criteria omitted from a project profile;
- no production-impact claim without independent deployment evidence;
- no independent assurance opinion.

## 14. Coding-stage conclusion

Within the repository-controlled scope, AgentProof now has a complete implementation path from claim extraction through evidence collection, integrity, verification, replay, project orchestration, machine-readable reporting, packaging, public demonstration, self-audit and a second-project case study.

The remaining high-value evidence is external by nature: independent attack design, outside users, expert review, production traces, institutional adoption and verified operational impact. Additional synthetic code cannot substitute for those categories, so they are tracked separately rather than inflated into the internal benchmark.
