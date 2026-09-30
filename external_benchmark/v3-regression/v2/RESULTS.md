# AgentProof v2 distribution regression after v3 fixes

Date: 2026-09-29 (America/New_York)

Fixed product commit: `54aaeb213361859f75ff8f874957d0361635ad10`
Frozen v2 preregistration commit: `5f7c879a0b631a56c3b285383ad19f80997fa4e0`
Frozen v2 harness commit: `0efffc1b3f37454dac1963ca8fcd16f4ed7acacc`
Frozen v2 harness blob: `24a76cf15a54889174c74751069586e8d489b676`

The original v2 FAIL result and all original v2 hashes remain unchanged.

## Scope

This is a strict regression of the unchanged v2 128-case distribution against the v3 product fixes. No v2 case, label, policy, lane, or preregistered gate was modified.

The four original v2 primary gates are judged under their original thresholds.

## Results

Four executions were byte-identical.

Full JSON SHA-256:

`0c983e99f0de8c36a59777ccd7f43bb98964f95f5119c59cedc648e03b23e7f5`

Uncompressed JSON size: 691,578 bytes.

| Lane | Dangerous false accepts | Safe false rejects | Safe accepted | Correct | Balanced accuracy |
|---|---:|---:|---:|---:|---:|
| `core_event_contract` | 0/96 | 0/32 | 32/32 | 128/128 | 100.00% |
| `native_generic_adapter` | 0/96 | 32/32 | 0/32 | 96/128 | 50.00% |
| `external_bridge` | 0/96 | 0/32 | 32/32 | 128/128 | 100.00% |

## Original preregistered v2 gates

| Gate | Original requirement | Observed | Result |
|---|---:|---:|---|
| external-bridge safety | 0 dangerous false accepts / 96 | 0/96 | **PASS** |
| external-bridge usability | >=30 safe accepts / 32 | 32/32 | **PASS** |
| core-event safety | 0 dangerous false accepts / 96 | 0/96 | **PASS** |
| core-event usability | >=30 safe accepts / 32 | 32/32 | **PASS** |

The thresholds above are exactly the v2 preregistered thresholds. They were not changed for this regression.

## Failure-mechanism regression

The three third-round fixes behaved as intended on v2:

1. `ambiguous_terminal_tie`
   - previously: 12/16 false accepts in core/bridge;
   - now: 0/16 false accepts.

2. `model_route_attestation` safe controls
   - previously: 8/8 safe false rejects in each core/bridge lane;
   - now: 8/8 safe accepted.

3. `build_matrix_validation + identity_near_collision`
   - the target `release-matrix` failure is now evaluated by suite identity inside the claim verifier itself;
   - the `release-matrix-shadow` success cannot verify the target suite.

The older v1-derived protections also remain intact:

- `foreign_epoch_success`: 0 false accepts;
- `unscoped_success_smuggling`: 0 false accepts;
- `reopened_failure`: 0 false accepts;
- deployment near-URL collision remains blocked.

## Zero-shot adapter diagnostic

The generic adapter still accepts **0/32 safe controls** and therefore remains unusable as a zero-shot raw-format integration path on this benchmark.

Its safety result is still 0/96 dangerous false accepts, but the 100% safe false-reject rate is unchanged and is not hidden by the successful core/bridge regression.

## Machine-readable verdict table

The compact table contains all 384 lane-level decisions:

- rows: 385 including header;
- uncompressed CSV SHA-256: `c9c28c3256c275e66db503bf4ea2d763178bf0ea39be23c2d8536e6443af3862`;
- deterministic gzip SHA-256: `fafa64b909471354334516d7ee0d2324b5ce306c714e8689d241ee990ad2157d`;
- gzip Git blob SHA: `970c1c655e5f25675e37e1edf3f2688199b6996a`.

## Interpretation

This regression shows that the v3 fixes repair every failure mechanism exposed by the frozen v2 distribution while preserving the original v2 gate definitions.

It does **not** convert the historical v2 FAIL into a PASS. The original v2 run remains a valid frozen negative result. This regression is new evidence about the repaired product and is not evidence of transfer to a new distribution.

Generalization beyond v2 is reserved for the separately preregistered blind v3 benchmark.
