#!/usr/bin/env python3
"""Inspect or execute the frozen Post-Stage-C v3 B1/B2 pilot."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT/'src'))
from developer_intent.post_stage_c_v3 import CONTRACT,validate_inputs
from developer_intent.post_stage_c_live import load_live_config
from developer_intent.post_stage_c_v3_live import output_paths,preflight,run_pilot

def config(live):
 return {"reconstruction_contract":CONTRACT,"target":"R_i(tFG)","operational_evidence_routes":["B1","B2"],"supporting_route":"B5_only","B3":"disabled_not_used","B4":"disabled_not_used","patchprompt_repository_state_evidence":"disabled","eventual_pr_commit_list_evidence":"disabled","model_calls":"disabled","network_during_check_or_dry_run":False,"transport_retries":live["transport_retries"],"github_token":"configured" if live["github_token"] else "not_configured"}
def main():
 p=argparse.ArgumentParser(); p.add_argument('--check-config',action='store_true'); p.add_argument('--dry-run',action='store_true'); a=p.parse_args(); rows=validate_inputs(ROOT); live=load_live_config(ROOT)
 if a.check_config: print(json.dumps(config(live),indent=2)); return
 if a.dry_run: print(json.dumps({"config":config(live),"cases":[{**r,"planned_outputs":{k:str(v) for k,v in output_paths(r['case_id']).items()}} for r in rows]},indent=2)); return
 preflight(ROOT)
 results=run_pilot(ROOT,live)
 print(json.dumps({"attempted":len(results),"contract":CONTRACT},indent=2))
if __name__=='__main__': main()
