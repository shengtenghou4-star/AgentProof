# Repository operations

This repository is a public verification product and reproducibility package.

## Source-of-truth map

- verifier behavior: source code and tests;
- benchmark evidence: locked benchmark outputs and the commit that produced them;
- supported claims: `README.md` and `docs/EVIDENCE_CLAIMS.md`;
- completion boundary: `docs/INTERNAL_COMPLETION.md`;
- release authority: immutable GitHub release artifacts bound to one commit.

A generated report verifies only the declared evidence and acceptance policy. It does not silently change the repository's own public claims.

## Change lanes

| Lane | Scope | Gate |
|---|---|---|
| verifier | parsers, claim checks, adapters | unit, fuzz and regression tests |
| security | redaction, isolation, integrity controls | deterministic security lane |
| evidence | benchmarks and locked reports | rerun, digest and wording review |
| operations | packaging, CI, documentation | zero protected-evidence changes |
| bounded contribution | named paths and acceptance tests | isolated branch and maintainer review |

## Bounded work packet

Every delegated task records an exact base commit, allowed paths, acceptance commands, prohibited paths, and expected evidence. Returned work enters an isolated branch. Signing keys, private traces, unreleased benchmark cases, locked outputs, and acceptance thresholds remain outside the task unless explicitly required and separately reviewed.

## Release gate

A release requires passing tests, deterministic benchmarks, security controls, package build and clean-install smoke, self-audit, public-claim validation, and immutable artifacts. Superseded releases remain historical records and are not overwritten.
