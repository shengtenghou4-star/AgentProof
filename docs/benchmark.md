# AgentProofBench

AgentProofBench is a deterministic adversarial benchmark for false-completion and evaluation-gaming detection.

## Suites

### Core

The 38 seed oracles cover honest and dishonest variants across:

- test completion and zero-test gaming;
- independently recomputed, self-reported, missing and inflated metrics;
- runtime and attested model routes;
- requested/returned model substitution;
- artifact existence and integrity;
- deployment health checks and mock evidence;
- completion claims;
- evaluator-file tampering and hidden command failures;
- stale artifact reuse and unauthorized acceptance changes;
- best-seed-only reporting;
- future-information and label leakage.

### Language and formatting perturbations

The 304-case suite expands every seed into eight deterministic wording or formatting variants. It changes paraphrases, Markdown, prefixes, suffixes, list formatting, capitalization and line breaks while preserving the same evidence ground truth.

### Layout/context holdout-style perturbations

The 1,216-case suite combines eight surrounding-context prefixes, four suffixes and rotating containers for each seed. It tests whether the extractor and verifier remain stable when the same controlled claim appears in reports, block quotes, bullets, inline code, status labels and other layouts.

The word **holdout-style** refers to a separate deterministic perturbation construction. It does not mean that the underlying attack families were designed by an independent party or hidden during development.

## Current controlled results

| Suite | Cases | Unsafe cases | False accepts | Correct |
|---|---:|---:|---:|---:|
| Core | 38 | 25 | 0 | 38 |
| Language/format | 304 | 200 | 0 | 304 |
| Layout/context holdout-style | 1,216 | 800 | 0 | 1,216 |
| **Combined** | **1,558** | **1,025** | **0** | **1,558** |

For the 1,216-case suite, the observed-accuracy 95% Wilson interval is approximately 99.69%–100%. The interval describes repeated sampling around this controlled corpus; it does not transform the suite into a real-world performance estimate.

## Reported metrics

Every suite reports:

- exact status agreement;
- 95% Wilson interval for observed accuracy;
- false-accept count and rate;
- a naive-trust baseline that accepts every agent claim;
- expected-versus-observed status confusion matrix;
- per-category accuracy and case count;
- seed and perturbation counts where applicable.

The false-accept rate is the primary safety metric. A false accept occurs when the oracle is `unsupported` or `contradicted` but AgentProof returns `verified` or `partial`.

## Commands

```bash
agentproof benchmark --suite core
agentproof benchmark --suite extended
agentproof benchmark --suite holdout
agentproof benchmark --suite all --json benchmark-report.json
python scripts/fuzz_claims.py
```

The fixed-seed fuzz harness generates 5,000 positive, negated and noise-heavy claim strings. It checks expected extraction, rejection of negated statements and a runtime budget.

## Interpretation boundary

The built-in suites are controlled regression corpora. They show that covered rules remain stable across the stated oracles and perturbations. They do **not** establish:

- universal real-world deception-detection accuracy;
- robustness to unknown attack families;
- independent evaluation;
- adversarial human red-team performance;
- production reliability across every agent framework.

Those claims require independently sampled and labeled runs, outside attack design and external validation. They are deliberately excluded from the coding-stage benchmark.
