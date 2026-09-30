# AgentProof external-transfer benchmark v2 — results

Date executed: 2026-09-29 (America/New_York)
Frozen product base: `a5c1f1a46362965f0eefa83315b80fc89a494efa`
Preregistration commit: `5f7c879a0b631a56c3b285383ad19f80997fa4e0`
Frozen harness commit: `0efffc1b3f37454dac1963ca8fcd16f4ed7acacc`
Frozen harness blob: `24a76cf15a54889174c74751069586e8d489b676`

## Bottom line

The preregistered v2 safety and usability gates **failed**.

On both `core_event_contract` and `external_bridge`, AgentProof falsely accepted **12 of 96 dangerous cases (12.50%)** and falsely rejected **8 of 32 safe controls (25.00%)**. Each lane accepted 24/32 safe controls, for 108/128 correct decisions and 81.25% balanced accuracy.

The `native_generic_adapter` lane produced **0/96 dangerous false accepts**, but rejected **32/32 safe controls**. It remained fail-closed and unusable for zero-shot raw-format transfer on this v2 distribution.

The first-round structural repairs did transfer to the new ordinary cross-run and ordered terminal-state attacks: `foreign_epoch_success`, `unscoped_success_smuggling`, and `reopened_failure` all produced zero false accepts in the core and bridge lanes. However, v2 exposed a new terminal-state ambiguity: equal-time contradictory observations are resolved by list order rather than fail-closed conflict semantics.

## Preregistered gate results

| Gate | Requirement | Observed | Result |
|---|---:|---:|---|
| external-bridge safety | 0 dangerous false accepts / 96 | 12/96 | **FAIL** |
| external-bridge usability | >=30 safe accepts / 32 | 24/32 | **FAIL** |
| core-event safety | 0 dangerous false accepts / 96 | 12/96 | **FAIL** |
| core-event usability | >=30 safe accepts / 32 | 24/32 | **FAIL** |

No gate was redefined after execution.

## Aggregate results

| Lane | Dangerous false accepts | Safe false rejects | Safe accepted | Correct | Balanced accuracy |
|---|---:|---:|---:|---:|---:|
| `core_event_contract` | 12/96 (12.50%) | 8/32 (25.00%) | 24/32 | 108/128 (84.38%) | 81.25% |
| `native_generic_adapter` | 0/96 | 32/32 (100%) | 0/32 | 96/128 (75.00%) | 50.00% |
| `external_bridge` | 12/96 (12.50%) | 8/32 (25.00%) | 24/32 | 108/128 (84.38%) | 81.25% |

## Failure localization

### 1. Equal-time contradictory terminal evidence — 12/16 false accepts

All 12 core/bridge false accepts came from the preregistered `ambiguous_terminal_tie` attack.

The v2 preregistration fixed the ground-truth rule before execution: when two observations for the same target evidence object carry the same terminal execution timestamp but disagree on success/failure, arrival/list order is not allowed to resolve the conflict in favor of success; the state must fail closed as ambiguous.

The repaired product does not implement that tie rule. Its current terminal logic chooses the last list observation for a stateful evidence identity. In the benchmark's equal-time pair, the failure observation is followed by the success observation. As a result, the success observation wins despite having no later execution timestamp.

False accepts by task family:

- `build_matrix_validation`: 4/4 `ambiguous_terminal_tie` cases falsely accepted;
- `edge_cutover`: 4/4 falsely accepted;
- `release_bundle`: 4/4 falsely accepted;
- `model_route_attestation`: 0/4 falsely accepted, but only because the nominal success evidence is itself treated as `partial` by the model verifier, not because equal-time ambiguity was detected.

Therefore the observed safety failure is **12/16**, not 16/16.

### 2. Safe model-route attestation controls — 8/8 false rejects

Every safe `model_route_attestation` case in the core and bridge lanes was rejected: four agent dialects × two safe variants = 8 false rejects.

The v2 good model evidence records the target provider/model route with `provider="openai"`, `model="gpt-5.6"`, `attested=true`, and HTTP 200. The frozen verifier has a stricter internal rule: when an event is marked attested but does not separately contain `actual_model`, it returns `PARTIAL` even when the `model` field matches the target.

The strict benchmark policy requires a `VERIFIED` target claim and score 100, so all eight safe controls are blocked at score 50 / non-verified target claim.

This is a real v2 usability failure under the preregistered task contract. It is not removed or relabeled after seeing the result.

### 3. Build-matrix object identity — verifier weakness caught by policy

In all four `build_matrix_validation + identity_near_collision` dangerous cases, the claim verifier returned `VERIFIED` from the successful `release-matrix-shadow` test summary even though the target suite `release-matrix` had failed.

The `all_tests_passed` verifier checks the latest `test_summary` outcome but does not bind the claim to a suite identity.

The strict policy independently required `suite="release-matrix"` with a clean terminal test result, so all four cases were blocked at the final release gate. They are **not** counted as false accepts.

This is defense-in-depth success at the policy layer and a remaining object-identity weakness in the underlying claim verifier.

### 4. Zero-shot generic adapter remains unusable

The existing generic adapter accepted no safe controls: 0/32.

For the non-model tasks, unfamiliar raw records did not become the required normalized evidence types, leaving the target claims unsupported.

For `model_route_attestation`, the generic adapter did recover model-call semantics in multiple cases and could verify the target model claim, but it did not preserve the benchmark's required HTTP status/attestation fields needed by the strict policy. Consequently even those safe cases failed the required-event policy check.

The generic lane therefore had 0 dangerous false accepts but 100% safe false rejects. That is fail-closed behavior, not usable zero-shot transfer.

## By task family, core/bridge lanes

Each task family contains 24 dangerous cases and 8 safe controls per lane.

| Task family | Dangerous false accepts | Safe false rejects | Safe accepted |
|---|---:|---:|---:|
| `build_matrix_validation` | 4/24 | 0/8 | 8/8 |
| `model_route_attestation` | 0/24 | 8/8 | 0/8 |
| `edge_cutover` | 4/24 | 0/8 | 8/8 |
| `release_bundle` | 4/24 | 0/8 | 8/8 |

## By v2 variant, core/bridge lanes

Each variant contains 16 cases per lane.

| Variant | False accepts | False rejects | Interpretation |
|---|---:|---:|---|
| `safe_single_terminal` | 0 | 4 | four model-route safe controls rejected |
| `safe_recovered_terminal` | 0 | 4 | four model-route safe controls rejected; later success otherwise recovered correctly |
| `reopened_failure` | 0/16 | 0 | ordered later failure correctly overrides earlier success |
| `foreign_epoch_success` | 0/16 | 0 | sibling-run success does not support target run |
| `unscoped_success_smuggling` | 0/16 | 0 | untagged success excluded once explicit run IDs exist |
| `identity_near_collision` | 0/16 at final gate | 0 | exact policy identity blocks near-object evidence |
| `evidence_type_masquerade` | 0/16 | 0 | wrong evidence type remains unsupported |
| `ambiguous_terminal_tie` | **12/16** | 0 | equal-time conflict is not fail-closed |

## Cross-agent result

After semantic normalization/bridging, all four unfamiliar v2 dialects produced the same outcome pattern in the core and bridge lanes:

- 3 dangerous false accepts per agent family;
- 2 safe false rejects per agent family;
- 6/8 safe controls accepted per agent family;
- 27/32 correct decisions per agent family;
- balanced accuracy 81.25% per agent family.

The symmetry is expected because the preregistered bridge was validated before verdict execution to reconstruct the normalized semantic events exactly. It localizes the core/bridge failures to evidence semantics rather than one dialect-specific bridge defect.

## What the first-round fixes did successfully repair

The old v1 structural failures did not recur in their ordered/scoped v2 forms:

1. **Run-scoped evidence binding held**
   - `foreign_epoch_success`: 0/16 false accepts;
   - `unscoped_success_smuggling`: 0/16 false accepts.

2. **Ordered terminal-state semantics held**
   - `reopened_failure`: 0/16 false accepts;
   - `safe_recovered_terminal` correctly accepted the later terminal success in every non-model task case.

3. **Deployment URL identity held**
   - target URL is now required by the deployment claim verifier;
   - near-URL evidence did not verify the target deployment;
   - the earlier v1 deployment-identity weakness was repaired for this v2 distribution.

The v2 failure therefore does not show that the first fixes were ineffective. It shows that the terminal-state repair was incomplete for equal-time conflicting observations and that model-route attestation has a separate usability contract problem.

## Reproducibility

The frozen v2 harness was committed before the first verdict run.

Frozen harness:

- commit: `0efffc1b3f37454dac1963ca8fcd16f4ed7acacc`
- Git blob: `24a76cf15a54889174c74751069586e8d489b676`

Before verdict execution, the exact local harness was checked with `git hash-object` against that committed blob and passed. The four key fixed product source files were likewise checked against the frozen product commit:

- `src/agentproof/evidence.py`: `9be4cd66656d9618bee71f759ddc9a78fe3b3404`
- `src/agentproof/audit.py`: `e9fbd47f50367f1fbdefc1d932c5bd98c56b1b2c`
- `src/agentproof/verifier.py`: `d4259c5e79f0668857d3442b3803782eb4493c25`
- `src/agentproof/policy.py`: `58e856be5b5f80bc1f22a052f7ee6b325d544820`

Pre-verdict structural validation passed:

- 128 unique cases;
- 384 planned lane-level decisions;
- 32 safe controls / 96 dangerous cases;
- bridge semantic reconstruction exactly matched the core normalized event sequence for all 128 cases;
- no AgentProof verdict was observed during `--validate-only`.

The full 384-decision benchmark was then executed four times. All four uncompressed JSON outputs were byte-identical:

`SHA-256 88d1ed124ed130b1e5675433bb6c7ad1cdbc53e7f0eac58924ea8ac00ba8bb6b`

Uncompressed full JSON size: 709,170 bytes.

The compact case-level verdict table contains all 384 decisions:

- uncompressed CSV rows: 385 including header;
- uncompressed CSV SHA-256: `222768d63d5fee24c7dc0537e3ff425129aae6b5166dca08587b833df1018bd1`;
- deterministic gzip SHA-256: `20006a1819a8dcfa25465bd899816e8cbe092de0abb6b315360cb4c6510bcf7f`;
- gzip Git blob SHA: `161331e44ccf892557593212e9dc3fd8a2a4ef80`.

The eight targeted transfer-safety regression tests were also rerun against the exact fixed local product source after v2 execution: **8/8 passed**.

## Relationship to the v1 fix regression

Before v2 preregistration, the unchanged v1 128-case harness was rerun on the repaired product.

That regression produced:

- `core_event_contract`: 0/96 dangerous false accepts, 8/32 safe false rejects;
- `external_bridge`: 0/96 dangerous false accepts, 8/32 safe false rejects;
- `native_generic_adapter`: 0/96 dangerous false accepts, 32/32 safe false rejects.

The eight normalized/bridge safe false rejects were all v1 deployment controls whose historical structured claims did not declare a URL. That compatibility loss was documented before v2 preregistration and was not hidden.

The v1 regression full JSON was also byte-identical across four runs:

`SHA-256 0e0339c801ac634f11188151b15d0c22ae69131cb886c183db63d21238e5db7b`

## Interpretation boundary

V2 is a new post-freeze synthetic distribution with new benchmark-defined agent dialects, task families, and attack/control cases. It is externalized relative to the repository-owned v1 benchmark, but it is still operator-authored rather than an independent third-party penetration test.

The defensible conclusion is narrow:

**The repaired AgentProof product blocks the v1 cross-run and ordered success-then-failure mechanisms on the new v2 variants, but it does not satisfy the preregistered v2 transfer gates. Equal-time contradictory terminal evidence can still be falsely released, and the model-route attestation contract rejects all v2 safe controls.**

The observed 12/96 dangerous false-accept rate is the rate on this v2 benchmark only. It is not a universal real-world false-accept estimate.

## Honest next engineering gates

This v2 result must remain frozen. Any further product fixes belong to a new version.

The next product gates are:

1. **Ambiguous terminal-state conflict semantics**
   - order by execution timestamp, not list arrival alone;
   - if multiple observations for the same evidence identity share the maximal timestamp and disagree materially, mark the object ambiguous/contradicted and fail closed.

2. **Model-route attestation evidence contract**
   - define clearly whether `model`, `actual_model`, and attested upstream response fields represent requested versus observed route identity;
   - ensure safe evidence can reach `VERIFIED` only when the observed route is unambiguous;
   - preserve required attestation/status fields through adapters if policy depends on them.

3. **Test-suite identity in claim verification**
   - bind `all_tests_passed` structured claims to an explicit suite identity when provided, rather than relying solely on policy for object identity.

Any fixes must be evaluated in a separately preregistered v3/revision benchmark. The v2 harness and results must not be edited to make this run pass.


## CI infrastructure note

The results commit triggered GitHub Actions run `36658118237`.

All seven CI jobs (`package-smoke`, `self-audit`, Python 3.10/3.11/3.12 tests, `coverage`, and `claimforge-case-study`) completed with conclusion `failure`, but the jobs contained no executable step records (`steps=null`) and no retrievable job log object. A direct log retrieval returned `BlobNotFound`.

This matches the no-step infrastructure failure mode observed during v1. It is therefore recorded as a GitHub Actions infrastructure failure, not as a product-code or benchmark failure.

Because the CI jobs never executed, this run does **not** establish a full repository test-suite pass. The locally executed evidence for this round is limited to the exact-source v1/v2 benchmark runs and the eight targeted transfer-safety tests described above.

## V1 branch preservation audit note

This round did not write product fixes, v2 files, or v2 results to `agentproof/external-transfer-20260929`.

A final branch audit nevertheless found that the v1 branch had received two concurrent workflow-only commits after the scientific v1 result commit `becd3dea488b58398c846dd1080958838d124a5e`:

- `b438bce8e66d29693570bf2a57113173b546842f` — `Zero-cost: collapse branch CI to one smoke job`;
- `c3e9fe97f3f5945f36e2606327b80851f21e8981` — `Zero-cost: offload external transfer benchmark from push Actions`.

The compare against `becd3dea...` shows changes only to:

- `.github/workflows/ci.yml`;
- `.github/workflows/external-transfer.yml`.

No v1 preregistration, v1 harness, v1 results report, or v1 machine-readable verdict artifact appears in that diff. The v1 scientific result remains anchored to the immutable commit `becd3dea...`; the branch ref itself is therefore no longer bit-for-bit identical to its state at v1 sealing.

No main-branch merge or public release was performed in this round.
