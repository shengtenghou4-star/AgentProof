# Model route attestation

AgentProof can sit between an agent runtime and an OpenAI-compatible upstream API. The proxy forwards traffic while recording a tamper-evident `model_call` event that reflects what crossed the network boundary.

## What is recorded

- configured provider label and upstream hostname;
- requested model from the JSON request body;
- actual model returned in the JSON response body, when disclosed;
- provider request ID from common response headers;
- HTTP status, latency, request path, and method;
- SHA-256 digests of request and response bodies;
- header names, but never header values;
- an explicit route-mismatch flag when requested and returned models differ.

Authorization tokens, prompt text, response text, and header values are not written to the trace. Body hashes provide equality evidence without storing plaintext.

## Start the proxy

```bash
agentproof-proxy \
  --upstream https://api.example.com/v1 \
  --provider example \
  --trace route-evidence.jsonl \
  --host 127.0.0.1 \
  --port 8787
```

Point the agent's OpenAI-compatible base URL at `http://127.0.0.1:8787`. Keep the normal authorization header; the proxy forwards it but does not log its value.

After the run:

```bash
agentproof audit route-evidence.jsonl \
  --response "I used example/premium-model."
```

## Verification levels

A matching upstream response model is treated as verified. A successful request where the upstream omits its actual model is partial evidence. A failed upstream request, provider mismatch, or requested/actual model substitution is contradicted.

The proxy is an application-layer attestor, not remote hardware attestation. A malicious process that bypasses the configured proxy remains outside its observation boundary. Production use should combine network egress controls, signed evidence bundles, and restricted trace permissions.
