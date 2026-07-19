# Evidence claims matrix

This matrix defines what each repository artifact can and cannot support.

| Claim | Supporting evidence | Supported scope | Not supported |
|---|---|---|---|
| AgentProof verifies atomic completion claims | Unit tests, controlled benchmarks, JSON/HTML/SARIF/JUnit reports | Covered claim types and event schemas | Arbitrary natural-language truth verification |
| AgentProof detects covered false-completion patterns | Core, extended, and holdout-style deterministic suites | Enumerated attacks and perturbations | Every unknown real-world deception strategy |
| AgentProof can detect model-route substitution | End-to-end proxy tests and attested request/response model fields | Traffic that passes through the configured proxy and identifies the returned model | Calls that bypass the proxy; hardware identity; provider honesty beyond observed responses |
| AgentProof preserves trace integrity | SHA-256 event chains, manifests, bundle verification tests | Accidental or detectable post-record modification under the stated trust model | A fully privileged attacker who can replace code, keys, and all evidence roots |
| AgentProof protects common secrets in command evidence | Redaction and bounded-capture tests | Covered token forms and configured capture paths | A formal data-loss-prevention guarantee or every possible secret format |
| AgentProof reproduces declared checks | Clean-workspace and Docker replay tests | Deterministic commands with declared dependencies and artifacts | Nondeterministic external services, hidden state, or unavailable credentials |
| AgentProof audits complete repositories | Project-audit tests, self-audit, ClaimForge case-study workflow | Declared commands, expected exits, artifacts, and claims | Undeclared acceptance criteria or business correctness outside the profile |
| AgentProof is cross-runtime | Claude Code, OpenAI Responses, Codex, generic agent-trace, and OTLP adapter tests | Supported record shapes and aliases | Guaranteed compatibility with every future framework version |
| AgentProof is installable and usable from a clean wheel | Package build and clean-venv smoke job | Supported Python versions and packaged commands | Operating systems and environments not exercised by CI |
| AgentProof has zero mandatory runtime dependencies | Package metadata and clean-wheel installation | Core Python package | Optional development, audit, documentation, or deployment tooling |
| ClaimForge passes an AgentProof project audit | Cross-repository CI case study and uploaded audit bundle | The checked-out public commit, declared commands, and declared artifacts | Independent assurance, production insurer validation, or external adoption |

## Benchmark interpretation

A benchmark result is reported with:

- exact case count;
- exact oracle agreement;
- false-accept count and rate;
- status confusion matrix;
- per-category results;
- a 95% Wilson interval for observed accuracy;
- a naive-trust baseline;
- an explicit statement that deterministic controlled suites are not an estimate of universal real-world coverage.

## Public wording rule

Public documentation may say that the current controlled suites passed if the corresponding CI artifact exists for the referenced commit. It must not translate controlled-suite accuracy into a real-world probability without an independently sampled and labeled evaluation set.
