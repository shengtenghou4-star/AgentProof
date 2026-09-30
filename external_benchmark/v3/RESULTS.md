# AgentProof external-transfer benchmark v3 — results

Date executed: 2026-09-29 (America/New_York)
Frozen product base: `54aaeb213361859f75ff8f874957d0361635ad10`
Preregistration commit: `d43dfc219d9edc7d338444a2cf52ad673a1838b7`
Frozen harness commit: `49250ee266dbdb3557c5bda2d6b3b361375d426b`

Frozen harness blobs:

- `external_benchmark/v3/v3_cases.py`: `8136b0830c4ce3bad67267a8d2318225f528dcbf`
- `external_benchmark/v3/v3_dialects.py`: `f2e5e9605e5040d746cf07cdac31c32f30f28df1`
- `external_benchmark/v3/run_transfer_benchmark_v3.py`: `ceaf3ca3c1721d2a526fb5180a80fee39b3e4fbd`

## Bottom line

The preregistered v3 core and external-bridge gates **passed**.

On both `core_event_contract` and `external_bridge`, AgentProof produced:

- **0/96 dangerous false accepts**;
- **0/32 safe false rejects**;
- **32/32 safe accepts**;
- **128/128 correct release decisions**;
- **100% balanced accuracy**.

All four preregistered v3 primary gates passed under the thresholds fixed before execution.

The `native_generic_adapter` lane remained fail-closed but unusable: **0/96 dangerous false accepts and 32/32 safe false rejects**. None of the four unfamiliar raw dialects yielded usable zero-shot target evidence through the frozen generic adapter.

This v3 PASS does not alter the frozen historical v2 FAIL. V2 remains a valid negative result for the earlier product.

## Preregistered gate results

| Gate | Requirement | Observed | Result |
|---|---:|---:|---|
| external-bridge safety | 0 dangerous false accepts / 96 | 0/96 | **PASS** |
| external-bridge usability | >=30 safe accepts / 32 | 32/32 | **PASS** |
| core-event safety | 0 dangerous false accepts / 96 | 0/96 | **PASS** |
| core-event usability | >=30 safe accepts / 32 | 32/32 | **PASS** |

No threshold, label, case, or gate was changed after execution.

## Aggregate results

| Lane | Dangerous false accepts | Safe false rejects | Safe accepted | Correct | Balanced accuracy |
|---|---:|---:|---:|---:|---:|
| `core_event_contract` | 0/96 | 0/32 | 32/32 | 128/128 | 100.00% |
| `native_generic_adapter` | 0/96 | 32/32 | 0/32 | 96/128 | 50.00% |
| `external_bridge` | 0/96 | 0/32 | 32/32 | 128/128 | 100.00% |

Core/bridge target-claim status distribution:

- `contradicted`: 76;
- `partial`: 8;
- `unsupported`: 4;
- `verified`: 40.

The 40 verified target claims consist of all 32 safe controls plus 8 dangerous `attestation_conflicting_fields` cases that were blocked by anomaly findings and strict policy. Those eight cases are discussed explicitly below.

## By task family, core/bridge lanes

Each task family contains 24 dangerous cases and 8 safe controls per lane.

| Task family | Dangerous false accepts | Safe false rejects | Safe accepted |
|---|---:|---:|---:|
| `compliance_matrix` | 0/24 | 0/8 | 8/8 |
| `search_quality_gate` | 0/24 | 0/8 | 8/8 |
| `gateway_model_route` | 0/24 | 0/8 | 8/8 |
| `payments_canary` | 0/24 | 0/8 | 8/8 |

The outcome pattern was identical across all four v3 raw dialects after normalized bridging: every dialect produced 32/32 correct decisions in both the core and bridge lanes.

## By v3 variant, core/bridge lanes

Each variant contains 16 cases per lane.

| Variant | False accepts | False rejects | Result |
|---|---:|---:|---|
| `safe_single_attested` | 0 | 0/16 | all safe controls accepted |
| `safe_equal_time_duplicate` | 0 | 0/16 | equivalent equal-time duplicate success remained verifiable |
| `equal_time_conflict_reversed` | 0/16 | 0 | all equal-time success/failure conflicts blocked |
| `equal_time_three_way_conflict` | 0/16 | 0 | all 2-success/1-failure equal-time conflicts blocked |
| `identity_namespace_collision` | 0/16 | 0 | neighboring identity success could not prove failed target |
| `attestation_missing_field` | 0/16 | 0 | all incomplete evidence blocked |
| `attestation_conflicting_fields` | 0/16 | 0 | all internally conflicting evidence blocked at final release gate |
| `late_foreign_success` | 0/16 | 0 | later sibling-run success could not override target failure |

## Third-round repair validation

### 1. Equal-time terminal conflict semantics

Both new equal-time attack forms were blocked in every task and agent cell:

- `equal_time_conflict_reversed`: 0/16 false accepts;
- `equal_time_three_way_conflict`: 0/16 false accepts.

The reversed-delivery attack deliberately placed success before failure at the same maximal timestamp. The three-way attack placed two success observations and one failure at the same maximal timestamp.

Neither list arrival order nor majority count granted verification.

The safe duplicate control also passed:

- `safe_equal_time_duplicate`: 16/16 accepted.

Thus the frozen semantics distinguish materially equivalent duplicate observations from materially conflicting equal-time observations.

### 2. Model-route attestation contract

All eight safe `gateway_model_route` controls were accepted in both core and bridge lanes.

The frozen contract behaved as preregistered:

- `actual_model` is authoritative when present;
- otherwise `model` is the observed route;
- attested evidence requires an explicit successful provider status;
- conflicting explicit `actual_model` is contradictory;
- missing provider status is not fully verified.

The v2 8/8 model-route safe false-reject mechanism did not recur.

### 3. Suite identity

All `compliance_matrix + identity_namespace_collision` cases were blocked by the claim verifier itself.

A later successful `compliance-prod-shadow` summary did not replace the failed target `compliance-prod` summary. The structured `expected.suite` identity is now enforced inside `all_tests_passed` verification rather than relying only on the policy layer.

## Defense-in-depth findings retained

The final 0/96 false-accept result does **not** mean every dangerous case was independently classified as contradicted by its target claim verifier.

Eight dangerous `attestation_conflicting_fields` cases had target claim status `VERIFIED` but were still correctly blocked:

1. Four `search_quality_gate` cases:
   - the target metric equaled 0.91 and independently recomputed, so the metric claim itself was verified;
   - the same event recorded `selected_best_seed=true` and `all_seeds_reported=false`;
   - the anomaly detector added a contradicted seed-cherry-picking finding;
   - audit score fell to 50 and the no-contradictions policy check failed.

2. Four `payments_canary` cases:
   - the target URL returned HTTP 204, so the deployment claim itself was verified;
   - the healthcheck was marked `synthetic=true`;
   - the anomaly detector added a contradicted mock-deployment finding;
   - audit score fell to 50 and the no-contradictions policy check failed.

Therefore the correct statement is:

**the integrated frozen release gate produced 0/96 dangerous false accepts on v3.**

It would be inaccurate to claim that every underlying claim verifier independently rejected every dangerous evidence object.

## Missing-field behavior

The 16 `attestation_missing_field` dangerous cases were all blocked, with task-specific target statuses:

- compliance suite identity omitted: `UNSUPPORTED`;
- metric independent-recompute marker omitted: `PARTIAL`;
- attested model provider status omitted: `PARTIAL`;
- deployment HTTP status omitted: `CONTRADICTED` because the exact target healthcheck does not establish a 2xx result.

No missing-field case was released.

## Identity collision behavior

All 16 `identity_namespace_collision` cases were blocked.

The neighboring successful identities were deliberately plausible but distinct:

- `compliance-prod-shadow` versus `compliance-prod`;
- `mrr` versus `ndcg`;
- `openai-compatible` versus `openai`;
- `https://payments.example/v3/live-shadow` versus the exact production canary URL.

A later success for the neighboring identity did not replace the target object's failed state.

## Run-scope behavior

All 16 `late_foreign_success` cases were blocked.

The sibling execution's valid-looking success occurred later in wall-clock/execution time than the target failure. Run-scoped evidence binding still excluded it from the target audit and policy match, demonstrating that recency does not override execution identity.

## Zero-shot generic adapter

The generic-adapter lane produced:

- 0/96 dangerous false accepts;
- 32/32 safe false rejects;
- 0/32 safe accepts;
- 96/128 correct decisions;
- 50% balanced accuracy;
- 0/128 cases with recovered target evidence events;
- all 128 target claims `UNSUPPORTED`.

This is conservative fail-closed behavior but **not usable zero-shot raw-format transfer** for these four v3 dialects.

The successful external-bridge lane cannot be used to relabel or excuse this usability failure.

## Reproducibility

The v3 preregistration was committed before harness implementation:

- preregistration commit: `d43dfc219d9edc7d338444a2cf52ad673a1838b7`;
- preregistration blob: `5d0430bf6c16de6ef33907c98c402a706ad1d1a4`.

The harness then passed pre-verdict structural validation:

- 128 unique cases;
- 384 planned lane-level judgments;
- 32 safe controls;
- 96 dangerous cases;
- bridge/core semantic event reconstruction matched exactly for all 128 cases;
- no AgentProof verdict was generated during validation.

The exact harness was frozen before the first verdict:

- harness commit: `49250ee266dbdb3557c5bda2d6b3b361375d426b`;
- `v3_cases.py` blob: `8136b0830c4ce3bad67267a8d2318225f528dcbf`;
- `v3_dialects.py` blob: `f2e5e9605e5040d746cf07cdac31c32f30f28df1`;
- runner blob: `ceaf3ca3c1721d2a526fb5180a80fee39b3e4fbd`.

The full 384-decision benchmark was executed four times. All four uncompressed JSON files were byte-identical:

`SHA-256 7b73e28e640c0a52e89b6cbdf5a820527c9a0c190d5c2ca65a86b7a7b7963da8`

Uncompressed full JSON size: 710,429 bytes.

The compact case-level verdict table contains all 384 decisions:

- rows: 385 including header;
- uncompressed CSV SHA-256: `205c9ac708079dd94eb3fda6ac1c4ef12bf768e02ec6af0c6223cf260b8404a0`;
- deterministic gzip SHA-256: `f64a471f6561865e5c4c9efe750624babbe64879d5dc954ba7bee22806a24f59`;
- expected gzip Git blob: `20e515fda7942a7d9caa3d340257a88b53a479ad`.

After v3 execution, the exact frozen product source was rerun against the targeted third-round regression tests: **17/17 passed**.

## Relationship to frozen v1/v2 evidence

Before v3 preregistration, the unchanged v1 and v2 distributions were rerun against the third-round product.

### V1 regression

- core: 0/96 dangerous false accepts, 24/32 safe accepted;
- bridge: 0/96 dangerous false accepts, 24/32 safe accepted;
- generic: 0/96 dangerous false accepts, 0/32 safe accepted.

The known v1 deployment-claim backward-compatibility loss remains. V1's historical safe deployment claims omit the target URL, so the stricter deployment verifier continues to fail closed on those controls.

V1 regression full JSON SHA-256:

`0e0339c801ac634f11188151b15d0c22ae69131cb886c183db63d21238e5db7b`

### V2 regression

Under the original, unchanged v2 preregistered thresholds:

- core: 0/96 dangerous false accepts, 32/32 safe accepted;
- bridge: 0/96 dangerous false accepts, 32/32 safe accepted;
- generic: 0/96 dangerous false accepts, 0/32 safe accepted.

All four original v2 primary gates pass on the repaired product.

V2 regression full JSON SHA-256:

`0c983e99f0de8c36a59777ccd7f43bb98964f95f5119c59cedc648e03b23e7f5`

This new regression result does not rewrite the historical v2 result. The original v2 run remains:

- 12/96 dangerous false accepts in core/bridge;
- 8/32 safe false rejects in core/bridge;
- frozen full JSON SHA-256 `88d1ed124ed130b1e5675433bb6c7ad1cdbc53e7f0eac58924ea8ac00ba8bb6b`.

## Interpretation boundary

The defensible conclusion is:

**The third-round AgentProof product passed all preregistered core and external-bridge gates on this synthetic post-freeze v3 transfer distribution, while preserving 0/96 dangerous false accepts on the unchanged v1 and v2 regression distributions.**

This supports transfer only on these specified frozen benchmark distributions.

It does not establish:

- universal real-world agent safety;
- a real-world false-accept rate;
- independent third-party assurance;
- usable zero-shot raw-format transfer, since the generic adapter still rejected all v3 safe controls.

The original v1 and v2 negative evidence remains part of the scientific record and is not superseded by the v3 PASS.
