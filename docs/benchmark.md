# AgentProofBench

AgentProofBench is a deterministic adversarial benchmark for false-completion and evaluation-gaming detection.

The alpha suite covers honest and dishonest variants across tests, metrics, model routing, artifacts, deployment, evaluator-file tampering, hidden command failures, stale artifact reuse, mock health checks, acceptance-criteria rewriting, seed cherry-picking, and future-data leakage.

The benchmark reports overall and per-category accuracy. Every case has a known oracle and can run without network access or model credentials, making regressions reproducible in CI.

```bash
agentproof benchmark
```

The built-in suite is a seed corpus, not a claim of real-world coverage. Later releases will add framework-recorded traces, paraphrase variation, multi-step attacks, and independently labeled agent runs.
