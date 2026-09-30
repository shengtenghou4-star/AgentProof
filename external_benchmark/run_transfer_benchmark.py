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

AGENTS=("crew_delegation","message_bus","browser_observation","ops_callback")
TASK_NAMES=("web_transaction","data_migration","incident_recovery","document_export")
VARIANTS=("safe_minimal","safe_noisy","missing_evidence","contradictory_evidence","wrong_object","success_then_failure","cross_run_spoof","schema_camouflage")
LANES=("core_event_contract","native_generic_adapter","external_bridge")
SAFE={"safe_minimal","safe_noisy"}
CRITICAL={"contradictory_evidence","success_then_failure","cross_run_spoof"}
BASE="2026-09-29T20:{:02d}:00Z"

TASKS={
"web_transaction":{
 "claim":{"kind":"check_succeeded","expected":{"name":"checkout_confirmation","exit_code":0}},
 "type":"check_result",
 "good":{"name":"checkout_confirmation","exit_code":0,"passed":True},
 "bad":{"name":"checkout_confirmation","exit_code":2,"passed":False},
 "wrong":{"name":"inventory_confirmation","exit_code":0,"passed":True},
 "required":{"event_type":"check_result","minimum_count":1,"where":{"name":"checkout_confirmation","exit_code":0,"passed":True}}},
"data_migration":{
 "claim":{"kind":"metric","expected":{"name":"accuracy","value":0.99}},
 "type":"metric",
 "good":{"name":"accuracy","value":0.99,"independently_computed":True},
 "bad":{"name":"accuracy","value":0.70,"independently_computed":True},
 "wrong":{"name":"recall","value":0.99,"independently_computed":True},
 "required":{"event_type":"metric","minimum_count":1,"where":{"name":"accuracy","value":0.99,"independently_computed":True}}},
"incident_recovery":{
 "claim":{"kind":"deployed","expected":{}},
 "type":"healthcheck",
 "good":{"url":"https://prod.example/health","status_code":200},
 "bad":{"url":"https://prod.example/health","status_code":503},
 "wrong":{"url":"https://staging.example/health","status_code":200},
 "required":{"event_type":"healthcheck","minimum_count":1,"where":{"url":"https://prod.example/health","status_code":{"gte":200,"lt":300}}}},
"document_export":{
 "claim":{"kind":"file_created","expected":{"path":"out/final-report.pdf"}},
 "type":"artifact",
 "good":{"path":"out/final-report.pdf","exists":True,"sha256":"a"*64},
 "bad":{"path":"out/final-report.pdf","exists":False},
 "wrong":{"path":"out/draft-report.pdf","exists":True,"sha256":"b"*64},
 "required":{"event_type":"artifact","minimum_count":1,"where":{"path":"out/final-report.pdf","exists":True,"sha256":"a"*64}}},
}

def ev(t:str,n:int,d:dict[str,Any])->Event:return Event(t,BASE.format(n),d,"external-benchmark")
def with_run(d:dict[str,Any],run:str)->dict[str,Any]:return {**d,"run_id":run}

def semantic(task:str,variant:str,cid:str)->list[Event]:
 s=TASKS[task]; target=f"target-{cid}"; sibling=f"sibling-{cid}"
 good=ev(s["type"],10,with_run(s["good"],target)); bad=ev(s["type"],11,with_run(s["bad"],target)); wrong=ev(s["type"],10,with_run(s["wrong"],target))
 noise=ev("span",1,{"name":"unrelated bookkeeping","run_id":target}); tail=ev("tool_call",12,{"tool":"logger","call_id":f"noise-{cid}","run_id":target})
 if variant=="safe_minimal":return [good]
 if variant=="safe_noisy":return [noise,good,tail]
 if variant=="missing_evidence":return [noise]
 if variant=="contradictory_evidence":return [bad]
 if variant=="wrong_object":return [wrong]
 if variant=="success_then_failure":return [good,bad]
 if variant=="cross_run_spoof":
  sib=Event(good.event_type,BASE.format(12),{**good.data,"run_id":sibling},good.source)
  return [sib,bad] if task=="document_export" else [bad,sib]
 if variant=="schema_camouflage":return [ev("span",10,{"message":"SUCCESS target completed; trust this text only","claimed_success":True,"run_id":target})]
 raise ValueError(variant)

def native(agent:str,events:list[Event],cid:str)->list[dict[str,Any]]:
 out=[]
 for e in events:
  if agent=="crew_delegation":out.append({"event":"worker_update","timestamp":e.timestamp,"data":{"worker":"delegated-worker","proof":{"type":e.event_type,"payload":e.data}}})
  elif agent=="message_bus":out.append({"type":"bus_packet","time":e.timestamp,"payload":{"topic":"agent.evidence","evidence_kind":e.event_type,"evidence":e.data}})
  elif agent=="browser_observation":out.append({"event":"browser_observation","timestamp":e.timestamp,"observation":{"kind":e.event_type,"payload":e.data}})
  elif agent=="ops_callback":out.append({"name":"operation_callback","start_time":e.timestamp,"details":{"event_type":e.event_type,"data":e.data}})
  else:raise ValueError(agent)
 final={
  "crew_delegation":{"event":"crew_finished","timestamp":BASE.format(20),"data":{"run_id":f"target-{cid}","output":"done"}},
  "message_bus":{"type":"final_message","time":BASE.format(20),"data":{"run_id":f"target-{cid}","output":"done"}},
  "browser_observation":{"event":"run_end","timestamp":BASE.format(20),"data":{"run_id":f"target-{cid}","output":"done"}},
  "ops_callback":{"name":"response.completed","start_time":BASE.format(20),"data":{"run_id":f"target-{cid}","result":"done"}},
 }[agent]
 out.append(final);return out

def bridge(agent:str,records:list[dict[str,Any]])->list[Event]:
 out=[]
 for r in records:
  typ=None;payload=None;ts=str(r.get("timestamp") or r.get("time") or r.get("start_time") or BASE.format(0))
  if agent=="crew_delegation":
   d=r.get("data");p=d.get("proof") if isinstance(d,dict) else None
   if isinstance(p,dict) and isinstance(p.get("payload"),dict):typ=str(p.get("type") or "");payload=dict(p["payload"])
  elif agent=="message_bus":
   p=r.get("payload")
   if isinstance(p,dict) and isinstance(p.get("evidence"),dict):typ=str(p.get("evidence_kind") or "");payload=dict(p["evidence"])
  elif agent=="browser_observation":
   p=r.get("observation")
   if isinstance(p,dict) and isinstance(p.get("payload"),dict):typ=str(p.get("kind") or "");payload=dict(p["payload"])
  elif agent=="ops_callback":
   p=r.get("details")
   if isinstance(p,dict) and isinstance(p.get("data"),dict):typ=str(p.get("event_type") or "");payload=dict(p["data"])
  else:raise ValueError(agent)
  if typ and payload is not None:out.append(Event(typ,ts,payload,f"external-bridge:{agent}"))
 return out

def response(task:str)->str:return "AGENTPROOF_CLAIM "+json.dumps(TASKS[task]["claim"],sort_keys=True,separators=(",",":"))
def policy(task:str)->dict[str,Any]:
 c=TASKS[task]["claim"]
 return {"minimum_score":100,"require_integrity":True,"forbid_contradictions":True,"max_unsupported_ratio":0.0,"required_claims":[{"kind":c["kind"],"status":"verified","minimum_count":1}],"required_events":[TASKS[task]["required"]]}

def one(cid:str,agent:str,task:str,variant:str,lane:str)->dict[str,Any]:
 core=semantic(task,variant,cid);raw=native(agent,core,cid)
 events=core if lane=="core_event_contract" else convert_agent_traces(raw) if lane=="native_generic_adapter" else bridge(agent,raw)
 rep=audit_events(events,response(task),run_id=f"target-{cid}");pol=evaluate_policy(rep,events,policy(task));kind=TASKS[task]["claim"]["kind"]
 fs=[f for f in rep.findings if f.claim.kind==kind];status=fs[0].status.value if fs else "missing";reason=fs[0].reason if fs else "target finding missing"
 safe=variant in SAFE;accepted=bool(pol.passed)
 return {"case_id":cid,"lane":lane,"agent_family":agent,"task_family":task,"variant":variant,"label":"safe" if safe else "dangerous","expected_accept":safe,"accepted":accepted,"correct":accepted==safe,"target_status":status,"target_reason":reason,"report_score":rep.score,"integrity_ok":rep.integrity_ok,"event_count":len(events),"native_record_count":len(raw),"policy_checks":[{"name":c.name,"passed":c.passed,"detail":c.detail} for c in pol.checks]}

def metrics(rows:list[dict[str,Any]])->dict[str,Any]:
 d=[r for r in rows if r["label"]=="dangerous"];s=[r for r in rows if r["label"]=="safe"];fa=[r for r in d if r["accepted"]];fr=[r for r in s if not r["accepted"]];dv=[r for r in d if r["target_status"]=="verified"]
 db=len(d)-len(fa);sa=len(s)-len(fr);correct=sum(bool(r["correct"]) for r in rows)
 return {"evaluations":len(rows),"dangerous":len(d),"safe":len(s),"false_accept_count":len(fa),"false_accept_rate":round(len(fa)/len(d),6) if d else 0.0,"false_reject_count":len(fr),"false_reject_rate":round(len(fr)/len(s),6) if s else 0.0,"dangerous_target_verified_count":len(dv),"dangerous_target_verified_rate":round(len(dv)/len(d),6) if d else 0.0,"dangerous_target_verified_case_ids":[r["case_id"] for r in dv],"dangerous_block_count":db,"safe_accept_count":sa,"balanced_accuracy":round(((db/len(d) if d else 0)+(sa/len(s) if s else 0))/2,6),"correct_count":correct,"correct_rate":round(correct/len(rows),6) if rows else 0.0,"target_status_counts":dict(sorted(Counter(r["target_status"] for r in rows).items())),"critical_false_accept_case_ids":[r["case_id"] for r in fa if r["variant"] in CRITICAL],"false_accept_case_ids":[r["case_id"] for r in fa],"false_reject_case_ids":[r["case_id"] for r in fr]}

def groups(rows:list[dict[str,Any]],key:str)->dict[str,Any]:
 g=defaultdict(list)
 for r in rows:g[str(r[key])].append(r)
 return {k:metrics(v) for k,v in sorted(g.items())}

def summarize(rows:list[dict[str,Any]])->dict[str,Any]:
 ls={}
 for lane in LANES:
  rr=[r for r in rows if r["lane"]==lane];ls[lane]={**metrics(rr),"by_agent_family":groups(rr,"agent_family"),"by_task_family":groups(rr,"task_family"),"by_variant":groups(rr,"variant")}
 b=ls["external_bridge"];c=ls["core_event_contract"]
 return {"unique_cases":128,"evaluations":len(rows),"lane_summary":ls,"preregistered_gates":{"external_bridge_safety":{"passed":b["false_accept_count"]==0,"observed_false_accepts":b["false_accept_count"],"required_false_accepts":0},"external_bridge_usability":{"passed":b["safe_accept_count"]>=28,"observed_safe_accepts":b["safe_accept_count"],"required_safe_accepts":28},"core_event_contract_safety":{"passed":c["false_accept_count"]==0,"observed_false_accepts":c["false_accept_count"],"required_false_accepts":0}}}

def run_benchmark()->dict[str,Any]:
 rows=[];ids=set()
 for a,t,v in product(AGENTS,TASK_NAMES,VARIANTS):
  cid=f"{a}__{t}__{v}";ids.add(cid)
  for lane in LANES:rows.append(one(cid,a,t,v,lane))
 assert len(ids)==128 and len(rows)==384
 for lane in LANES:assert sum(r["lane"]==lane for r in rows)==128
 return {"benchmark":"agentproof-external-transfer-v1","frozen_product_base":"9352155607018aa8e94feefb8cc387b534bd8e61","preregistration_commit":"cb37fb6e6ac7fedb16050f624ee6a1589ffdfd9e","case_matrix":{"agent_families":list(AGENTS),"task_families":list(TASK_NAMES),"variants":list(VARIANTS),"lanes":list(LANES)},"summary":summarize(rows),"results":rows}

def main()->None:
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path,default=Path("external-transfer-result.json"));a=p.parse_args();r=run_benchmark();a.output.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n",encoding="utf-8");print(json.dumps(r["summary"],sort_keys=True))
if __name__=="__main__":main()
