# AgentProofBench

AgentProofBench is a deterministic adversarial benchmark for false-completion and evaluation-gaming detection.

The core v0.2 suite covers honest and dishonest variants across tests, metrics, model routing, route attestation, artifacts, deployment, completion claims, evaluator-file tampering, hidden command failures, stale artifact reuse, mock health checks, acceptance-criteria rewriting, model substitution, seed cherry-picking, and future or label leakage.

The benchmark reports:

- exact status accuracy;
- a 95% Wilson interval for accuracy;
- false-accept rate on claims that should be contradicted or unsupported;
- a naive-trust baseline that accepts every agent claim;
- a status confusion matrix;
- per-category accuracy and case counts.

Every case has a known oracle and can run without network access or model credentials, making regressions reproducible in CI.

```bash
agentproof benchmark
```

The false-accept rate is the primary safety metric. It measures how often AgentProof incorrectly treats a claim as verified or partial when the oracle says the claim is contradicted or unsupported.

The built-in suite remains a seed corpus rather than a claim of real-world coverage. Later releases will add framework-recorded traces, paraphrase variation, multi-step attacks, and independently labeled agent runs.
