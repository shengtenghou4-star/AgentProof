# AgentProofBench

AgentProofBench is a deterministic adversarial benchmark for false-completion and evaluation-gaming detection.

The core v0.2 suite covers honest and dishonest variants across tests, metrics, model routing, route attestation, artifacts, deployment, completion claims, evaluator-file tampering, hidden command failures, stale artifact reuse, mock health checks, acceptance-criteria rewriting, model substitution, seed cherry-picking, and future or label leakage.

The perturbed v0.3 suite expands each seed oracle into eight deterministic language and formatting variants. It preserves the same evidence ground truth while changing:

- claim paraphrases;
- Markdown emphasis;
- explanatory prefixes and suffixes;
- list formatting and line breaks;
- capitalization and equivalent completion wording.

With 38 seed cases, the perturbed suite contains 304 cases. Expansion is deterministic, so CI regressions remain reproducible and do not depend on an external model.

The benchmark reports:

- exact status accuracy;
- a 95% Wilson interval for accuracy;
- false-accept rate on claims that should be contradicted or unsupported;
- a naive-trust baseline that accepts every agent claim;
- a status confusion matrix;
- per-category accuracy and case counts;
- the number of seed cases and perturbations per seed for the extended suite.

Every case has a known oracle and can run without network access or model credentials.

```bash
agentproof benchmark --suite core
agentproof benchmark --suite extended --json benchmark-report.json
```

The false-accept rate is the primary safety metric. It measures how often AgentProof incorrectly treats a claim as verified or partial when the oracle says the claim is contradicted or unsupported.

The built-in suites remain controlled regression corpora rather than claims of real-world coverage. The next evidence tier requires framework-recorded multi-step traces, independently labeled agent runs, adversarial human review and held-out attack families.
