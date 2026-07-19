# Reliability aggregation

AgentProof can aggregate any number of audit JSON reports into a cross-run reliability summary.

```bash
agentproof audit trace-a.jsonl --response-file answer-a.txt --run-id agent-a --json agent-a.json
agentproof audit trace-b.jsonl --response-file answer-b.txt --run-id agent-b --json agent-b.json
agentproof summarize agent-a.json agent-b.json --json reliability.json
```

The summary reports score distribution, trace-integrity pass rate, verified and contradicted finding rates, per-claim-kind performance, and a concrete contradiction list linked to run IDs. This is intended for repeated trials, model-route comparisons, framework comparisons, and regression tracking.
