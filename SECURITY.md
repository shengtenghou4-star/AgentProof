# Security policy

## Supported versions

Security fixes are applied to the current `main` branch. Until a stable 1.0 release, older tags are not maintained as separate security branches.

## Reporting a vulnerability

Do not publish credentials, private traces, exploit details, or sensitive agent transcripts in a public issue. Use GitHub's private vulnerability-reporting feature when available. Include:

- affected commit or version;
- threat model and required attacker privileges;
- minimal reproduction;
- expected and observed behavior;
- whether secrets, evidence integrity, route identity, replay isolation, or policy enforcement are affected.

## Security boundaries

AgentProof is application-layer verification infrastructure. It is not:

- hardware-backed remote attestation;
- a trusted execution environment;
- a formal proof system;
- a sandbox for hostile native code;
- a replacement for network egress controls, IAM, secret management, or host isolation;
- an independent security certification.

The route proxy can only attest traffic that actually passes through it. Hash chains detect modification relative to their trust root; a fully privileged attacker who can replace the verifier, keys, and all stored evidence is outside the default model. Docker replay reduces ambient privileges but does not make an unsafe host trustworthy.

## Secret handling

Command output is redacted for common credential forms, bounded in size, and accompanied by a digest of the original bytes. Transcript adapters hash content by default. These controls reduce accidental disclosure but do not guarantee discovery of every possible secret representation. Users should avoid recording unnecessary sensitive data and should use dedicated test credentials.

## Safe deployment defaults

- bind the local API to loopback unless an authenticated reverse proxy is configured;
- deny replay network access unless a task explicitly requires it;
- use read-only mounts and disposable workspaces;
- keep signing keys outside evidence bundles;
- restrict agent network egress so required route-attestation proxies cannot be bypassed;
- treat imported traces as untrusted input;
- keep project audit profiles under code review because they define acceptance criteria.
