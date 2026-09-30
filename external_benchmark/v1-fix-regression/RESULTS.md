# AgentProof v1 distribution regression after transfer-safety fixes

Date: 2026-09-29 (America/New_York)

Original frozen v1 result branch: `agentproof/external-transfer-20260929`
Original v1 result: 20/96 dangerous false accepts in both `core_event_contract` and `external_bridge`.
Original v1 evidence is unchanged.

Fixed product commit: `a5c1f1a46362965f0eefa83315b80fc89a494efa`
Original v1 harness blob: `dc7e506003430eab57aea8a0b56a25e8af185e6a`

## Fixes under regression

1. Run-scoped evidence binding:
   - if a trace carries any explicit run IDs, claim verification and anomaly scanning use only evidence whose `data.run_id` equals the target audit `run_id`;
   - policy event matching applies the same scope;
   - untagged evidence cannot support a target once explicit run IDs are present;
   - legacy traces containing no explicit run IDs retain single-run compatibility.

2. Terminal-state semantics:
   - repeated stateful evidence is collapsed to its terminal observation for policy matching;
   - artifact verification now evaluates the last observation for the claimed path;
   - model verification now evaluates the terminal matching provider route.

3. Deployment identity:
   - a deployment claim must declare an explicit expected URL;
   - healthcheck evidence must match that exact URL;
   - repeated healthchecks for the target URL use the terminal observation;
   - deployment claims without an expected URL fail closed as unsupported.

## Targeted safety tests

Eight new targeted tests were run locally against the exact committed product source:

- sibling-run evidence cannot verify a target run;
- policy cannot borrow a required event from a sibling run;
- terminal artifact failure overrides an earlier success;
- policy required-event matching uses terminal artifact state;
- deployment verification requires the target URL;
- deployment without a URL fails closed;
- terminal deployment failure overrides an earlier success;
- terminal model-route failure overrides an earlier success.

Result: **8/8 passed**.

## Exact-source verification

The local product files used for the official regression were checked by Git blob hash against the fixed commit:

- `src/agentproof/evidence.py`: `9be4cd66656d9618bee71f759ddc9a78fe3b3404`
- `src/agentproof/audit.py`: `e9fbd47f50367f1fbdefc1d932c5bd98c56b1b2c`
- `src/agentproof/verifier.py`: `d4259c5e79f0668857d3442b3803782eb4493c25`
- `src/agentproof/policy.py`: `58e856be5b5f80bc1f22a052f7ee6b325d544820`

## v1 distribution regression result

The unchanged v1 128-case harness was executed through all three lanes, yielding 384 decisions per run.

Four repeated runs were byte-identical.

Full JSON SHA-256:

`0e0339c801ac634f11188151b15d0c22ae69131cb886c183db63d21238e5db7b`

Uncompressed JSON size: 672,825 bytes.

| Lane | Dangerous false accepts | Safe false rejects | Safe accepted | Correct | Balanced accuracy |
|---|---:|---:|---:|---:|---:|
| `core_event_contract` | 0/96 | 8/32 | 24/32 | 120/128 | 87.50% |
| `native_generic_adapter` | 0/96 | 32/32 | 0/32 | 96/128 | 50.00% |
| `external_bridge` | 0/96 | 8/32 | 24/32 | 120/128 | 87.50% |

All v1 critical attack families were blocked after the fixes:
- `cross_run_spoof`: 0 false accepts;
- `success_then_failure`: 0 false accepts;
- `contradictory_evidence`: 0 false accepts.

## Compatibility cost

The fixed core does **not** preserve v1 safe-control usability exactly.

All eight safe `incident_recovery` cases in each normalized/bridge lane are now rejected because the frozen v1 structured deployment claim used `expected: {}` and therefore did not identify the production URL inside the claim itself.

Under the new verifier contract, that claim is insufficient to prove deployment and fails closed as `unsupported`, even though the v1 policy separately required the production URL.

Therefore:
- the v1 dangerous false-accept regression target is repaired: **0/96**;
- the old v1 external-bridge usability gate of >=28/32 does not pass after the stricter deployment contract: observed **24/32**;
- this is recorded as a real backward-compatibility/usability regression, not hidden or reclassified.

Future benchmarks must place deployment identity in the claim itself so the claim verifier and policy independently check the same target.

## Interpretation

This regression establishes only that the three specified structural repairs block the dangerous cases in the old v1 distribution.

It is not evidence that the fixes generalize to a new attack distribution. That question is reserved for the separately preregistered external-transfer-v2 benchmark.
