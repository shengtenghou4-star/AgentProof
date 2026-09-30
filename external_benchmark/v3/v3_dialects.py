from __future__ import annotations
from typing import Any
from agentproof.models import Event
from v3_cases import ts

def native(agent: str, events: list[Event], case_id: str) -> list[dict[str, Any]]:
    records = []
    for evidence in events:
        run_id = evidence.data.get("run_id"); metadata = {"run_id": run_id} if run_id not in (None, "") else {}
        fact = {"kind": evidence.event_type, "fact": dict(evidence.data)}
        if agent == "audit_notebook":
            record = {"event": "notebook_cell", "timestamp": evidence.timestamp, "metadata": metadata, "cell": {"execution_token": run_id, "observation": fact}}
        elif agent == "queue_receipt":
            record = {"type": "queue_receipt", "time": evidence.timestamp, "metadata": metadata, "receipt": {"execution_token": run_id, "topic": "evidence.receipt", "body": fact}}
        elif agent == "graph_checkpoint":
            record = {"name": "graph_checkpoint", "start_time": evidence.timestamp, "metadata": metadata, "checkpoint": {"execution_token": run_id, "node": "verification", "proof": fact}}
        elif agent == "signed_callback":
            record = {"event": "signed_callback", "timestamp": evidence.timestamp, "metadata": metadata, "callback": {"execution_token": run_id, "subject": "agentproof.v3.evidence", "attestation": fact}}
        else: raise ValueError(agent)
        records.append(record)
    target = f"target-v3-{case_id}"
    records.append({"event": "final", "timestamp": ts(30), "metadata": {"run_id": target}, "data": {"run_id": target, "output": "done"}})
    return records

def bridge(agent: str, records: list[dict[str, Any]]) -> list[Event]:
    output = []
    for record in records:
        kind = None; payload = None
        timestamp = str(record.get("timestamp") or record.get("time") or record.get("start_time") or ts(0))
        if agent == "audit_notebook":
            c = record.get("cell"); x = c.get("observation") if isinstance(c, dict) else None
        elif agent == "queue_receipt":
            c = record.get("receipt"); x = c.get("body") if isinstance(c, dict) else None
        elif agent == "graph_checkpoint":
            c = record.get("checkpoint"); x = c.get("proof") if isinstance(c, dict) else None
        elif agent == "signed_callback":
            c = record.get("callback"); x = c.get("attestation") if isinstance(c, dict) else None
        else: raise ValueError(agent)
        if isinstance(x, dict) and isinstance(x.get("fact"), dict): kind = str(x.get("kind") or ""); payload = dict(x["fact"])
        if kind and payload is not None: output.append(Event(kind, timestamp, payload, f"external-bridge-v3:{agent}"))
    return output
