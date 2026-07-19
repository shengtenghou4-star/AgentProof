# Threat model

AgentProof assumes the audited agent may exaggerate, omit failures, reuse stale artifacts, change acceptance criteria, or emit misleading completion language.

## In scope

- false claims about test success, metrics, model routing, artifacts, deployment, and completion;
- missing or contradictory runtime evidence;
- artifact replacement after execution;
- tampering with append-only event chains;
- dependence on hidden local state that breaks clean replay;
- malformed or unsafe replay manifests, including shell-string execution and workspace escapes.

## Out of scope in the current alpha

- hostile operating-system kernels or container runtimes;
- secrets exfiltration prevention;
- verification of arbitrary semantic claims without an observable oracle;
- side-channel attacks;
- proof that an external telemetry producer was honest before AgentProof received the data.

AgentProof is a verification layer, not a complete sandbox or endpoint-security product. Replay commands use argv execution without a shell, run in a copied workspace, and receive a reduced environment. Strong isolation remains a roadmap item.
