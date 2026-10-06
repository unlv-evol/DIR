#!/usr/bin/env python3
"""Canonical Post-Stage-C v4 production interface."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from developer_intent.post_stage_c_transport import load_live_config
from developer_intent.post_stage_c import CONTRACT,PROCEDURE,validate_record
from developer_intent.post_stage_c_corpus import (population, run, validate_complete,
                                                  validate_eligibility,
                                                  write_eligibility)
from developer_intent.post_stage_c_engine import execute_case,output_paths

def main():
 p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group();g.add_argument('--case-id');g.add_argument('--all',action='store_true');p.add_argument('--check-config',action='store_true');p.add_argument('--dry-run',action='store_true');p.add_argument('--validate',action='store_true');p.add_argument('--resolve-eligibility',action='store_true');p.add_argument('--validate-eligibility',action='store_true');a=p.parse_args()
 cfg=load_live_config(ROOT);pop=population(ROOT)
 base={"contract":CONTRACT,"procedure":PROCEDURE,"authoritative_population":len(pop),"outcome_inputs_enabled":False,"github_token":"configured" if cfg['github_token'] else "not_configured"}
 if a.check_config: print(json.dumps(base,indent=2));return
 if a.validate: print(json.dumps({"validated":len(validate_complete(ROOT))},indent=2));return
 if a.resolve_eligibility: print(json.dumps({"eligible":len(write_eligibility(ROOT))},indent=2));return
 if a.validate_eligibility: print(json.dumps({"validated_eligibility":len(validate_eligibility(ROOT))},indent=2));return
 selected=pop if a.all else ([next(r for r in pop if r['case_id']==a.case_id)] if a.case_id else [])
 if a.dry_run: print(json.dumps({**base,"selected_cases":[r['case_id'] for r in selected]},indent=2));return
 if not selected: p.error('choose --case-id CASE_ID or --all')
 if a.all: rows=run(ROOT,cfg);print(json.dumps({"processed":len(rows)},indent=2));return
 path=ROOT/output_paths(selected[0]['case_id'])['acquisition']
 if path.exists():
  record=json.loads(path.read_text());validate_record(record);disposition='existing_authoritative_record_validated'
 else:
  record=execute_case(ROOT,selected[0],cfg,persist=True);disposition='executed_and_persisted'
 print(json.dumps({"case_id":record['case_id'],"status":record['reconstruction_status'],"disposition":disposition},indent=2))
if __name__=='__main__':main()
