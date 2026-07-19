# Internal completion boundary

AgentProof separates work that can be completed and verified inside the repository from evidence that requires independent people, organizations, production systems, or private data.

## Coding-stage definition of done

The internal stage is complete only when the repository contains and continuously validates all of the following.

### Verification engine

- deterministic claim extraction with explicit structured claims;
- negation-safe parsing that does not turn a denial into a positive claim;
- verified, partial, unsupported, and contradicted verdicts;
- named acceptance-check verification;
- test, metric, model-route, artifact, deployment, and completion verification;
- run-level detection of hidden failures, evaluator tampering, stale artifacts, mock health checks, unauthorized acceptance changes, model substitution, cherry-picking, and data leakage.

### Evidence integrity and privacy

- append-only SHA-256 event chains;
- artifact manifests and signed portable evidence bundles;
- bounded command capture with full-output digests;
- common credential and token redaction;
- environment metadata that records names and hashes rather than secret values;
- runtime, dependency, platform, Git, and environment provenance fingerprints.

### Reproducibility

- local clean-workspace replay;
- network-denied, resource-limited Docker replay;
- profile-driven project audits;
- expected exit-code enforcement;
- exact artifact digest enforcement;
- machine-readable JSON, SARIF, JUnit, and human-readable HTML output.

### Runtime integrations

- OpenAI-compatible model-route attestation proxy;
- Claude Code transcript adapter;
- OpenAI Responses adapter;
- Codex transcript adapter;
- generic OpenAI Agents SDK / LangGraph-style trace adapter;
- OpenTelemetry / OTLP import;
- local API and dashboard;
- GitHub Action and CI gates.

### Internal empirical evidence

- controlled seed benchmark;
- wording and formatting perturbation benchmark;
- larger holdout-style layout benchmark;
- deterministic parser fuzzing;
- self-audit of AgentProof's own tests, lint, build, package artifacts, provenance, and benchmark claims;
- a cross-repository ClaimForge case study using only public repository contents and reproducible commands.

### Product and release quality

- installable wheel and source distribution;
- clean-environment wheel smoke test;
- Python 3.10, 3.11, and 3.12 CI;
- branch coverage gate;
- static interactive demonstration;
- reproducible documentation, threat model, evidence-claims matrix, security policy, contribution guide, and citation metadata;
- explicit limitations on every public benchmark and assurance claim.

## Evidence deliberately deferred

The following cannot be manufactured by additional repository work and are excluded from the coding-stage definition of done:

- independent security assessment or penetration test;
- external expert review or recommendation letters;
- users, downloads, stars, forks, citations, or community adoption;
- production deployment inside an unrelated organization;
- private enterprise traces or confidential incident data;
- verified cost savings, risk reduction, or operational impact;
- standards-body participation, conference acceptance, awards, or institutional endorsement;
- an untouched benchmark designed and labeled by an independent party.

These are future external-validation tracks. Their absence must not be disguised by adding more synthetic tests or stronger wording.

## Claim discipline

Passing internal checks supports the statement that AgentProof is a reproducible, tested, project-level agent-verification framework with controlled adversarial evidence. It does **not** support claims of universal deception detection, formal verification, hardware-backed attestation, enterprise certification, or independently validated real-world impact.
