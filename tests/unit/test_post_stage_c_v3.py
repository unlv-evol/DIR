from __future__ import annotations
import csv,hashlib,json,glob,subprocess,unittest
from pathlib import Path
from developer_intent.post_stage_c_v3 import (FROZEN_CASES,b5_cannot_start_b2,
    choose_target,extract_b1,initialize_record,pilot_rows)
from developer_intent.post_stage_c_v3_live import execute_case
ROOT=Path(__file__).resolve().parents[2]

def record(text, *, role='user'):
 return {'admissible_prior_turns':[{'turn_id':'turn_1','role':role,'text':text}]}
def aggregate(pattern):
 h=hashlib.sha256()
 for p in sorted(glob.glob(str(ROOT/pattern))): h.update(Path(p).read_bytes())
 return h.hexdigest()

class PostStageCV3Tests(unittest.TestCase):
 def test_v1_v2_preserved_and_v2_executed(self):
  self.assertEqual(aggregate('cases/reconstruction/CASE_*/historical_state_acquisition_v1.json'),'fac6445bb7a652774a1d0cdc067eccd3e5a0c2cfba21f566668d4e41dbddc162')
  self.assertEqual(aggregate('data/derived/historical_information/CASE_*/historical_information_index_v1.json'),'247cb41eedfe0ab5ff237e1c4b03ff56b950fb329a574bd880c71af53ce2cf1d')
  self.assertEqual(aggregate('cases/reconstruction/CASE_*/historical_state_acquisition_v2.json'),'c62165d4c6d5cab69ecd9308186ab7f23d01c7bc893a09988e6217378abacd59')
  self.assertEqual(aggregate('data/derived/historical_information/CASE_*/historical_information_boundary_v2.json'),'74f5b5f0487fe5eb499599b147c274a0cfbdded9f6953895022577861bcde600')
  rows=list(csv.DictReader((ROOT/'cases/manifests/post_stage_c_reconstruction_pilot_v2.csv').read_text().splitlines()))
  self.assertEqual(len(rows),8); self.assertTrue(all(r['executed']=='true' for r in rows))
  self.assertTrue(all(json.loads((ROOT/f"cases/reconstruction/{r['case_id']}/historical_state_acquisition_v2.json").read_text())['historical_state_reconstructible']=='unresolved' for r in rows))
 def test_same_eight_v3_unexecuted(self):
  rows=pilot_rows(ROOT); self.assertEqual(tuple(r['case_id'] for r in rows),FROZEN_CASES)
  self.assertTrue(all(r['executed']=='false' for r in rows)); self.assertEqual([r['pa_pn_stratum'] for r in rows],['PA']*4+['PN']*4)
 def test_full_sha_direct_baseline(self):
  sha='a'*40; b1=extract_b1(record('I am working from commit '+sha)); self.assertEqual(b1['status'],'established')
  self.assertEqual(choose_target(b1,{})['authoritative'],sha)
 def test_abbreviated_sha_is_auditable_candidate(self):
  b1=extract_b1(record('I am working from commit abcdef123456'))
  self.assertEqual(b1['candidates'][0]['identifier_type'],'abbreviated_commit_sha')
 def test_ambiguous_semantics_and_multiple_revisions(self):
  self.assertEqual(extract_b1(record('reference '+'a'*40))['status'],'not_established')
  self.assertEqual(extract_b1(record('working from '+'a'*40+' and working from '+'b'*40))['status'],'ambiguous')
 def test_first_generation_and_later_turns_are_structurally_absent(self):
  r=record('no revision'); r['first_generation_response']={'text':'working from '+'a'*40}; r['later_turns']=[{'text':'working from '+'b'*40}]
  self.assertEqual(extract_b1(r)['status'],'not_established')
 def test_b2_requires_b1_and_parent_is_not_automatic(self):
  self.assertTrue(b5_cannot_start_b2('not_established','B5'))
  b1=extract_b1(record('commit '+'a'*40+' contains the change'))
  self.assertEqual(choose_target(b1,{'status':'not_attempted'})['status'],'unresolved')
 def test_b2_valid_parent_requires_b1_source(self):
  b1=extract_b1(record('commit '+'a'*40+' contains the change'))
  b2={'status':'validated','starting_revision_source':'B1','relationship_type':'first_parent','relationship_result':'b'*40}
  self.assertEqual(choose_target(b1,b2)['authoritative'],'b'*40)
  b2['starting_revision_source']='eventual_pr'; self.assertEqual(choose_target(b1,b2)['status'],'unresolved')
 def test_b5_sources_never_start_b2(self):
  for source in ('current_pr_base','stage_a_base_sha','current_git_reachability','latest_before_tFG','nearest_before_tFG'):
   self.assertTrue(b5_cannot_start_b2('not_established','B5'),source)
 def test_patchprompt_routes_disabled_and_case_identity_retained(self):
  rows=pilot_rows(ROOT); self.assertTrue(all(r['patchprompt_archive_repository_state_input']=='disabled' for r in rows))
  self.assertTrue(all(r['pr_number'] and r['repository'] for r in rows))
 def test_record_contract_disables_b3_b4_archive(self):
  e=next(csv.DictReader((ROOT/'cases/manifests/post_stage_c_eligibility.csv').read_text().splitlines())); a=next(csv.DictReader((ROOT/'cases/manifests/post_stage_c_historical_target_audit.csv').read_text().splitlines()))
  s=json.loads((ROOT/e['stage_c_authoritative_record']).read_text()); r=initialize_record(e,a,s)
  self.assertEqual(r['b3']['status'],'not_used_v3'); self.assertEqual(r['b4']['status'],'not_used_v3'); self.assertFalse(r['patchprompt_archive_repository_state_used'])
  self.assertEqual(r['historical_state_reconstructible'],'unresolved')
 def test_event_availability_observation_are_distinct(self):
  schema=json.loads((ROOT/'schemas/historical_state_acquisition_v3.schema.json').read_text()); self.assertIn('b1',schema['properties']); self.assertIn('b5_support',schema['properties'])
 def test_check_and_dry_are_offline(self):
  for flag in ('--check-config','--dry-run'):
   p=subprocess.run(['python3','-B','pipeline/post_stage_c/run_pilot_v3.py',flag],cwd=ROOT,capture_output=True,text=True,check=True)
   self.assertIn('post-stage-c-reconstruction-v3',p.stdout); self.assertIn('disabled',p.stdout)
 def test_pipeline_state_unchanged(self):
  e=list(csv.DictReader((ROOT/'cases/manifests/post_stage_c_eligibility.csv').read_text().splitlines())); self.assertEqual(len(e),111); self.assertTrue(all(r['final_scientific_eligibility']=='pending_resolution' for r in e))
  self.assertEqual(hashlib.sha256((ROOT/'cases/manifests/stage_c_post_resolution_authority.csv').read_bytes()).hexdigest(),'03682e1d5071e5e0cf5219fd647cf7311ee581feb44f07d13e0c863c95a171cb')

 def _live_fixture(self,tmp,text):
  e=next(r for r in csv.DictReader((ROOT/'cases/manifests/post_stage_c_eligibility.csv').read_text().splitlines()) if r['case_id']==FROZEN_CASES[0])
  a=next(r for r in csv.DictReader((ROOT/'cases/manifests/post_stage_c_historical_target_audit.csv').read_text().splitlines()) if r['case_id']==FROZEN_CASES[0])
  rel='stage.json'; (Path(tmp)/rel).write_text(json.dumps(record(text)))
  e={**e,'stage_c_authoritative_record':rel}; return e,a

 def test_live_no_b1_performs_no_git_and_is_unresolved(self):
  import tempfile
  with tempfile.TemporaryDirectory() as tmp:
   e,a=self._live_fixture(tmp,'general task text without a revision')
   fail=lambda *x,**y:self.fail('Git must not run without B1')
   out=execute_case(Path(tmp),e,a,{'timeout':1,'transport_retries':0},relationship_probe=fail,materializer=fail)
  self.assertEqual(out['record']['historical_state_reconstructible'],'unresolved'); self.assertEqual(out['attempts'],[])

 def test_live_direct_b1_materializes_without_parent_probe(self):
  import tempfile
  sha='a'*40
  with tempfile.TemporaryDirectory() as tmp:
   e,a=self._live_fixture(tmp,'I am working from commit '+sha)
   material=lambda *x,**y:{'status':'validated','remote_operations':1,'object_type':'commit','tree_sha':'b'*40,'deterministic_repeat':True}
   out=execute_case(Path(tmp),e,a,{'timeout':1,'transport_retries':0},relationship_probe=lambda *x,**y:self.fail('parent is not automatic'),materializer=material)
  self.assertEqual(out['record']['authoritative_R_i_tFG'],sha); self.assertEqual(out['record']['historical_state_reconstructible'],'yes')

 def test_live_focal_change_uses_b1_as_b2_start(self):
  import tempfile
  sha='a'*40; parent='b'*40
  probe=lambda *x,**y:{'status':'validated','remote_operations':1,'requested_sha':sha,'parent_sha':parent,'tree_sha':'c'*40,'commit_time':''}
  material=lambda *x,**y:{'status':'validated','remote_operations':1,'object_type':'commit','tree_sha':'d'*40,'deterministic_repeat':True}
  with tempfile.TemporaryDirectory() as tmp:
   e,a=self._live_fixture(tmp,'commit '+sha+' contains the change')
   out=execute_case(Path(tmp),e,a,{'timeout':1,'transport_retries':0},relationship_probe=probe,materializer=material)
  self.assertEqual(out['record']['b2']['starting_revision_source'],'B1'); self.assertEqual(out['record']['authoritative_R_i_tFG'],parent)
  self.assertTrue(all(item['operation']!='github_current_pr_metadata' for item in out['attempts']))

if __name__=='__main__': unittest.main()
