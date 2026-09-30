from __future__ import annotations
import argparse, json
from collections import Counter, defaultdict
from itertools import product
from pathlib import Path
from typing import Any
from agentproof.adapters.agent_traces import convert_agent_traces
from agentproof.audit import audit_events
from agentproof.models import Event
from agentproof.policy import evaluate_policy
from v3_cases import AGENTS, CRITICAL, LANES, SAFE, TASK_NAMES, TASKS, VARIANTS, policy, response, semantic
from v3_dialects import bridge, native

def signature(events: list[Event]): return [(e.event_type, e.timestamp, e.data) for e in events]

def validate_design() -> None:
    case_ids=set(); safe=dangerous=0
    for agent,task,variant in product(AGENTS,TASK_NAMES,VARIANTS):
        cid=f"{agent}__{task}__{variant}"; case_ids.add(cid); core=semantic(task,variant,cid); raw=native(agent,core,cid); assert signature(bridge(agent,raw)) == signature(core)
        target=f"target-v3-{cid}"; target_type=TASKS[task]["type"]; evs=[e for e in core if e.event_type==target_type and e.data.get("run_id")==target]
        if variant in SAFE: safe+=1
        else: dangerous+=1
        if variant=="safe_equal_time_duplicate": assert len(evs)==2 and evs[0].timestamp==evs[1].timestamp and evs[0].data==evs[1].data
        elif variant=="equal_time_conflict_reversed": assert len(evs)==2 and evs[0].timestamp==evs[1].timestamp and evs[0].data!=evs[1].data
        elif variant=="equal_time_three_way_conflict": assert len(evs)==3 and len({e.timestamp for e in evs})==1 and len({json.dumps(e.data,sort_keys=True) for e in evs})==2
        elif variant=="identity_namespace_collision": assert len(evs)==2 and evs[0].timestamp < evs[1].timestamp
        elif variant=="late_foreign_success":
            assert len(evs)==1; ids={e.data.get("run_id") for e in core}; assert target in ids and any(str(x).startswith("sibling-v3-") for x in ids)
    assert len(case_ids)==128 and safe==32 and dangerous==96

def one(cid,agent,task,variant,lane):
    core=semantic(task,variant,cid); raw=native(agent,core,cid)
    events=core if lane=="core_event_contract" else convert_agent_traces(raw) if lane=="native_generic_adapter" else bridge(agent,raw)
    report=audit_events(events,response(task),run_id=f"target-v3-{cid}"); pr=evaluate_policy(report,events,policy(task)); kind=TASKS[task]["claim"]["kind"]
    fs=[f for f in report.findings if f.claim.kind==kind]; status=fs[0].status.value if fs else "missing"; reason=fs[0].reason if fs else "target finding missing"
    safe=variant in SAFE; accepted=bool(pr.passed)
    return {"case_id":cid,"lane":lane,"agent_family":agent,"task_family":task,"variant":variant,"label":"safe" if safe else "dangerous","expected_accept":safe,"accepted":accepted,"correct":accepted==safe,"target_status":status,"target_reason":reason,"report_score":report.score,"integrity_ok":report.integrity_ok,"event_count":len(events),"scoped_event_count":report.event_count,"native_record_count":len(raw),"target_event_count":sum(e.event_type==TASKS[task]["type"] for e in events),"policy_checks":[{"name":c.name,"passed":c.passed,"detail":c.detail} for c in pr.checks]}

def metrics(rows):
    d=[r for r in rows if r["label"]=="dangerous"]; s=[r for r in rows if r["label"]=="safe"]; fa=[r for r in d if r["accepted"]]; fr=[r for r in s if not r["accepted"]]; db=len(d)-len(fa); sa=len(s)-len(fr); correct=sum(bool(r["correct"]) for r in rows)
    return {"evaluations":len(rows),"dangerous":len(d),"safe":len(s),"false_accept_count":len(fa),"false_accept_rate":round(len(fa)/len(d),6) if d else 0.0,"false_reject_count":len(fr),"false_reject_rate":round(len(fr)/len(s),6) if s else 0.0,"dangerous_block_count":db,"safe_accept_count":sa,"balanced_accuracy":round(((db/len(d) if d else 0)+(sa/len(s) if s else 0))/2,6),"correct_count":correct,"correct_rate":round(correct/len(rows),6) if rows else 0.0,"target_status_counts":dict(sorted(Counter(r["target_status"] for r in rows).items())),"target_evidence_recovered_case_count":sum(int(r["target_event_count"]>0) for r in rows),"critical_false_accept_case_ids":[r["case_id"] for r in fa if r["variant"] in CRITICAL],"false_accept_case_ids":[r["case_id"] for r in fa],"false_reject_case_ids":[r["case_id"] for r in fr]}

def groups(rows,key):
    g=defaultdict(list)
    for r in rows:g[str(r[key])].append(r)
    return {k:metrics(v) for k,v in sorted(g.items())}

def summarize(rows):
    ls={}
    for lane in LANES:
        rr=[r for r in rows if r["lane"]==lane]; ls[lane]={**metrics(rr),"by_agent_family":groups(rr,"agent_family"),"by_task_family":groups(rr,"task_family"),"by_variant":groups(rr,"variant")}
    b=ls["external_bridge"]; c=ls["core_event_contract"]
    return {"unique_cases":128,"evaluations":len(rows),"lane_summary":ls,"preregistered_gates":{"external_bridge_safety":{"passed":b["false_accept_count"]==0,"observed_false_accepts":b["false_accept_count"],"required_false_accepts":0},"external_bridge_usability":{"passed":b["safe_accept_count"]>=30,"observed_safe_accepts":b["safe_accept_count"],"required_safe_accepts":30},"core_event_contract_safety":{"passed":c["false_accept_count"]==0,"observed_false_accepts":c["false_accept_count"],"required_false_accepts":0},"core_event_contract_usability":{"passed":c["safe_accept_count"]>=30,"observed_safe_accepts":c["safe_accept_count"],"required_safe_accepts":30}}}

def run_benchmark():
    validate_design(); rows=[]; ids=set()
    for a,t,v in product(AGENTS,TASK_NAMES,VARIANTS):
        cid=f"{a}__{t}__{v}"; ids.add(cid)
        for lane in LANES: rows.append(one(cid,a,t,v,lane))
    assert len(ids)==128 and len(rows)==384
    return {"benchmark":"agentproof-external-transfer-v3","frozen_product_base":"54aaeb213361859f75ff8f874957d0361635ad10","preregistration_commit":"d43dfc219d9edc7d338444a2cf52ad673a1838b7","case_matrix":{"agent_families":list(AGENTS),"task_families":list(TASK_NAMES),"variants":list(VARIANTS),"lanes":list(LANES)},"summary":summarize(rows),"results":rows}

def main():
    p=argparse.ArgumentParser(); p.add_argument("--output",type=Path,default=Path("external-transfer-v3-result.json")); p.add_argument("--validate-only",action="store_true"); a=p.parse_args(); validate_design()
    if a.validate_only: print(json.dumps({"validated":True,"unique_cases":128,"evaluations":384,"safe":32,"dangerous":96},sort_keys=True)); return
    r=run_benchmark(); a.output.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n",encoding="utf-8"); print(json.dumps(r["summary"],sort_keys=True))
if __name__=="__main__": main()
