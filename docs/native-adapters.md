# Native transcript adapters

AgentProof normalizes supported agent-runtime exports into its JSONL evidence schema. Adapters intentionally hash prompt, response, tool argument, and tool result content instead of copying plaintext into the evidence trace.

## Claude Code

Claude Code print mode supports structured JSON and streaming JSON output. Import either form with:

```bash
claude -p "run the tests" --output-format stream-json --verbose > claude-run.jsonl
agentproof-import claude-code claude-run.jsonl evidence.jsonl
```

The adapter emits:

- `model_call` events when a model identifier is present;
- `tool_call` and `tool_result` events with content hashes;
- an `agent_result` event with success state, duration, turns, cost, and result hash;
- generic spans for unrecognized record types.

## OpenAI Responses

Responses API objects and JSON event streams can be imported with:

```bash
agentproof-import openai-responses responses.jsonl evidence.jsonl
```

The adapter emits model calls, function/computer/search tool calls, and final result metadata. Output content is represented by SHA-256 only.

## OpenTelemetry

Existing OTLP/JSON conversion remains available:

```bash
agentproof-import otel traces.json evidence.jsonl
```

Adapters provide normalized observation evidence. The model-route proxy is stronger for provider/model identity because it observes the network boundary and records requested versus returned models.
