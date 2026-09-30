# AgentProof external-transfer benchmark v1 — results

Date executed: 2026-09-29 (America/New_York)
Frozen product base: `9352155607018aa8e94feefb8cc387b534bd8e61`
Preregistration commit: `cb37fb6e6ac7fedb16050f624ee6a1589ffdfd9e`
Harness commit: `81b12f02284de914249771e2b8d599addd3c6bc7`

## Bottom line

The preregistered transfer safety gate **failed**.

On both the normalized core-event lane and the external-bridge lane, AgentProof falsely accepted **20 of 96 dangerous cases (20.8333%)**. All 32 safe controls were accepted in those lanes.

The zero-shot generic-adapter lane produced **0/96 dangerous false accepts**, but also rejected **32/32 safe controls**. This is fail-closed behavior with effectively no usable zero-shot transfer to these four unfamiliar trace dialects.

These results do not invalidate the historical 1,558-case controlled result. They show that the zero-false-accept result did **not** transfer to this post-freeze attack distribution.

## Aggregate results

| Lane | Dangerous false accepts | Safe false rejects | Safe accepted | Correct | Balanced accuracy | Gate |
|---|---:|---:|---:|---:|---:|---|
| `core_event_contract` | 20/96 (20.83%) | 0/32 | 32/32 | 108/128 (84.38%) | 89.58% | safety FAIL |
| `native_generic_adapter` | 0/96 | 32/32 (100%) | 0/32 | 96/128 (75.00%) | 50.00% | zero-shot usability FAIL |
| `external_bridge` | 20/96 (20.83%) | 0/32 | 32/32 | 108/128 (84.38%) | 89.58% | safety FAIL; usability PASS |

Preregistered external-bridge safety gate: required 0 dangerous false accepts; observed 20. **FAIL.**

Preregistered external-bridge usability gate: required at least 28/32 safe accepts; observed 32. **PASS.**

Preregistered core-event safety diagnostic: required 0 dangerous false accepts; observed 20. **FAIL.**

## Failure localization

### 1. Cross-run evidence spoofing — 16/16 false accepts

Every `cross_run_spoof` case was accepted in `core_event_contract` and `external_bridge`.

The frozen audit API records a report `run_id`, but the tested claim verifiers and policy event requirements do not bind matching evidence to that target run. A sibling run can therefore contribute success-looking evidence to the target audit.

Breakdown: four agent dialects × four task families = 16 false accepts.

### 2. Artifact terminal-state handling — 4/16 success-then-failure false accepts

All four false accepts in `success_then_failure` were `document_export` cases.

The frozen file verifier returns on the first artifact event matching the expected path. A fresh, hashed success artifact followed by a terminal `exists=false` event therefore remains `verified`. The strict policy also sees a matching successful artifact event somewhere in the trace and passes.

Other task families used latest matching evidence and correctly blocked this attack.

### 3. Deployment object identity — verifier weakness caught by policy

All four `incident_recovery + wrong_object` dangerous cases received target claim status `verified` because the deployment verifier checks only the latest healthcheck status code, not the claimed URL/object identity.

However, the preregistered strict policy required a 2xx healthcheck for the production URL. That policy check blocked all four cases, so they were **not** false accepts at the final release gate.

This is useful evidence that the policy layer provides real defense-in-depth, while the underlying claim verifier is still too weak on object identity.

## By task family, core/bridge lanes

| Task family | False accepts / 24 dangerous | Safe accepted / 8 |
|---|---:|---:|
| `web_transaction` | 4 (16.67%) | 8 |
| `data_migration` | 4 (16.67%) | 8 |
| `incident_recovery` | 4 (16.67%) | 8 |
| `document_export` | 8 (33.33%) | 8 |

## By attack family, core/bridge lanes

| Variant | False accepts / 16 |
|---|---:|
| `missing_evidence` | 0 |
| `contradictory_evidence` | 0 |
| `wrong_object` | 0 at final policy gate |
| `schema_camouflage` | 0 |
| `success_then_failure` | 4 |
| `cross_run_spoof` | 16 |

## Cross-agent result

The false-accept pattern was identical for all four unfamiliar agent dialects after normalization/bridging: each agent family produced 5 false accepts out of 24 dangerous cases.

That symmetry is expected because the bridge preserved the same semantic evidence contract. It localizes the observed safety failures to core evidence scoping/terminal semantics rather than to one agent dialect.

The existing generic adapter did not recover task evidence from any of the four unfamiliar raw dialects: all 128 target claims were `unsupported`, producing 0/32 safe accepts. Thus zero-shot raw-format transfer was not usable on this benchmark.

## Reproducibility

The full 384-evaluation JSON was executed four times locally. All four uncompressed outputs were byte-identical:

`SHA-256 73dcaf5de8ca5b93c64ee254f7b7b4681663e11e655d6334bbdfa73a17d7b723`

Uncompressed size: 624,098 bytes.

The committed gzip contains that raw JSON:
- gzip SHA-256: `1102e7c58241a9c8e0365080efe1c2fc9105e8bc825ea5fa750e3f5ccf8dcf28`
- decompress and verify the uncompressed SHA above.

Before execution, the local copies of every product source file actually used by this benchmark plus the harness were checked against their GitHub Git-blob SHA values; all matched the frozen repository versions. A minimal local `adapters/__init__.py` import shim was used only to avoid importing unrelated adapters; the tested `agent_traces.py` was the exact frozen blob.

Execution environment: Linux x86_64, Python 3.13.5.

## Infrastructure note

GitHub Actions run `36654128145` for this benchmark failed at job level with zero executed steps and no benchmark artifact/log. The existing repository CI jobs showed the same no-step failure pattern. Therefore that Actions failure is recorded as an infrastructure failure, not as a benchmark result.

The scientific result above comes from the deterministic local execution described under Reproducibility.

## Interpretation boundary

This benchmark is externalized relative to the frozen repository-owned corpus: it was preregistered after the product freeze, uses new task semantics and unfamiliar trace dialects, and no existing controlled case was sliced or paraphrased into it.

It is still authored and run by the project operator, not an independent third-party penetration test. The four unfamiliar dialects are benchmark-defined synthetic schemas, not byte-for-byte traces captured from four production agent vendors.

Accordingly, the result supports one narrow conclusion: **the frozen AgentProof core does not maintain its historical zero-dangerous-false-accept behavior under this post-freeze transfer distribution.** It does not establish a universal real-world false-accept rate.

## Honest next engineering gates

The observed failures identify two concrete product gates for a future version, not changes to this frozen result:

1. bind every auditable evidence item and policy match to the target execution/run scope;
2. define terminal-state semantics for repeated evidence objects, especially artifacts, instead of accepting the first successful observation.

Any fixes must be evaluated on a new benchmark version while preserving this v1 result unchanged.
