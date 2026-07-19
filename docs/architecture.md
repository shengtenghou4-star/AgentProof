# AgentProof architecture

AgentProof separates **claims**, **observations**, and **verification rules**.

1. An agent produces a final natural-language response.
2. Conservative extractors convert externally testable statements into atomic claims.
3. Runtime adapters and independent checkers emit normalized JSONL events.
4. Deterministic verifiers match each claim to the minimum sufficient evidence.
5. Reports distinguish verified, partial, unsupported, and contradicted claims.
6. Optional chained hashes make deletion, reordering, and mutation of recorded events detectable.

The core deliberately avoids asking a second language model whether the first model was truthful. LLM judges may later assist claim extraction, but final verification should prefer deterministic checks and independently reproduced facts.

## Trust boundaries

AgentProof can prove only what its evidence sources can observe. A compromised runtime can forge local events, so stronger deployments should combine:

- isolated verifier processes;
- signed attestations;
- remote model-provider receipts;
- sandboxed replay;
- artifact storage with immutable retention;
- independent metric recomputation.

The current alpha establishes the protocol and verification semantics. It is not yet a hardened security boundary.
