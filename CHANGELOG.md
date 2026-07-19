# Changelog

## 0.3.0 — 2026-07-19

- added an OpenAI-compatible model-route attestation proxy;
- added requested-versus-returned model substitution detection;
- added privacy-preserving Claude Code and OpenAI Responses transcript adapters;
- expanded AgentProofBench to 35+ core cases with false-accept metrics, confidence intervals, confusion matrices, and a naive-trust baseline;
- added automatic pytest summary extraction from recorded commands;
- added a CI self-audit that verifies AgentProof's own test-completion claim;
- added end-to-end proxy, adapter, benchmark, and recorder coverage.

## 0.2.0 — 2026-07-19

- added clean-workspace and resource-isolated Docker replay;
- added signed evidence bundles and artifact provenance verification;
- added enforceable acceptance policies and CI gates;
- added evaluation-gaming detectors and expanded AgentProofBench;
- added OTLP/JSON ingestion and cross-run reliability aggregation;
- added a local REST API and interactive dashboard;
- expanded schemas, tests, threat modeling, and integration documentation.

## 0.1.0 — 2026-07-19

- initial deterministic claim-to-evidence audit core;
- JSON and HTML reports, hash-chain integrity, CLI, and CI.
