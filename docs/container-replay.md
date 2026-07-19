# Container replay

AgentProof can rerun a replay manifest inside a single ephemeral Docker container:

```bash
agentproof replay replay.json --source . --docker-image python:3.12-slim
```

Default controls:

- network disabled;
- all Linux capabilities dropped;
- `no-new-privileges` enabled;
- memory, CPU, and process-count limits;
- a small `noexec` temporary filesystem;
- control files mounted read-only;
- source copied into a disposable workspace.

The selected image must contain Python because the container-side replay supervisor is Python-based. Project dependencies must already exist in the image or be installable by manifest steps; network remains disabled unless explicitly enabled.

Container replay substantially improves isolation from host state. It does not defend against a malicious container runtime, kernel escape, hostile image, or all possible output-tampering strategies. Treat it as defense in depth, not a formal security boundary.
