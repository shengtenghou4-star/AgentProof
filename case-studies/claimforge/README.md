# ClaimForge cross-repository case study

This case study demonstrates that AgentProof can audit a substantial second repository rather than only its own fixtures.

## Target

- Repository: `shengtenghou4-star/7`
- Project: ClaimForge v0.6.0
- Data boundary: public repository contents and reproducible public commands only
- External assistance: none

## Declared checks

The strict profile runs:

1. the complete ClaimForge pytest suite with normal summary output;
2. Ruff across the repository;
3. ClaimForge's public-claim validation script.

It also records SHA-256 evidence for:

- `README.md`;
- `docs/evidence/validation_suite_summary.json`.

## Current result

The CI case-study lane produced:

- 54 ClaimForge tests passed;
- lint passed;
- public-claim validation passed;
- 5/5 AgentProof claims verified;
- project audit score 100/100;
- valid evidence hash chain;
- runtime, dependency, Git and selected environment provenance;
- JSON, HTML, SARIF and JUnit reports.

## What this establishes

The result supports that AgentProof can:

- orchestrate multiple acceptance checks in another repository;
- distinguish test claims from generic named checks;
- capture and hash second-project artifacts;
- preserve provenance and evidence integrity;
- produce a strict machine-readable project verdict.

## What this does not establish

The case study is self-operated and uses a project controlled by the same owner. It is not:

- independent assurance;
- a security certification;
- an insurer pilot;
- validation of ClaimForge's production performance;
- evidence of unrelated external adoption.

Those categories are external-validation work and are not replaced by this case study.
