# AgentProof v1 distribution regression after v3 fixes

Date: 2026-09-29 (America/New_York)

Fixed product commit: `54aaeb213361859f75ff8f874957d0361635ad10`
Original v1 harness blob: `dc7e506003430eab57aea8a0b56a25e8af185e6a`

## Scope

This regression reruns the unchanged external-transfer-v1 128-case distribution after the third-round product fixes:

1. equal-time terminal conflict fail-closed semantics;
2. model-route attestation contract clarification;
3. suite identity binding for `all_tests_passed`.

No v1 case, label, policy, lane, or gate was changed.

## Targeted tests

The previous eight transfer-safety tests plus nine new third-round tests were run locally against the exact fixed source.

Result: **17/17 passed**.

The new tests cover:

- equal-time conflicting terminal observations fail closed;
- equal-time equivalent successes remain verifiable;
- different timestamps still use the later observation;
- policy cannot accept a success from an equal-time conflict;
- attested `model` without `actual_model` can verify when provider/model and HTTP 2xx are unambiguous;
- explicit conflicting `actual_model` is contradictory;
- attested evidence without provider response status is not fully verified;
- shadow test-suite success cannot prove the target suite;
- matching suite identity verifies normally.

## Exact-source anchors

- `src/agentproof/evidence.py`: `c9ee294b164d1644d214603504178d9088c7ea25`
- `src/agentproof/verifier.py`: `6ad74311f7e5b87f469dd072d22dc7bd2ec18c3b`
- unchanged v1 harness: `dc7e506003430eab57aea8a0b56a25e8af185e6a`

## Results

Four executions were byte-identical.

Full JSON SHA-256:

`0e0339c801ac634f11188151b15d0c22ae69131cb886c183db63d21238e5db7b`

Uncompressed JSON size: 672,825 bytes.

| Lane | Dangerous false accepts | Safe false rejects | Safe accepted | Correct | Balanced accuracy |
|---|---:|---:|---:|---:|---:|
| `core_event_contract` | 0/96 | 8/32 | 24/32 | 120/128 | 87.50% |
| `native_generic_adapter` | 0/96 | 32/32 | 0/32 | 96/128 | 50.00% |
| `external_bridge` | 0/96 | 8/32 | 24/32 | 120/128 | 87.50% |

The dangerous regression target remains repaired: **0/96 false accepts** in core and bridge.

The pre-existing v1 usability cost remains unchanged. All eight safe `incident_recovery` controls in each normalized/bridge lane use the historical deployment claim `expected: {}`; the stricter deployment verifier requires the URL inside the claim itself, so those controls remain fail-closed.

The original v1 external-bridge usability gate therefore remains failed after the stricter contract: 24/32 safe accepts versus the historical >=28/32 threshold.

This is a compatibility result only; no v1 historical result was rewritten.

## Machine-readable verdict table

The compact table contains all 384 lane-level decisions:

- rows: 385 including header;
- uncompressed CSV SHA-256: `85b81bc9d21f74e7efee018987040469d905fd8df9a36ee74d7ef38c0c587fbd`;
- deterministic gzip SHA-256: `b66f031588a4bc47d51b3fce91a193b30d761a8b42ba35356ed90e494e56342d`;
- gzip Git blob SHA: `9db20251192259baa37538fa919bf57a158a4d21`.

## Interpretation

The v3 fixes do not reintroduce the v1 dangerous false-accept mechanisms. They also do not repair the known backward-compatibility loss of legacy deployment claims that omit an expected URL.
