import json
import tempfile
import unittest
from pathlib import Path

from developer_intent.post_stage_c import (annotate_commit, choose_reconstruction,
                                            focal_root_external_parent,
                                            select_from_lineage,
                                            validate_eligibility_record,
                                            validate_eligibility_schema,
                                            validate_record)

TFG="2024-01-02T00:00:00+00:00"
def c(n, author, committer, parents=()):
    return {"sha":f"{n:040x}","parent_shas":[f"{p:040x}" for p in parents],"tree_sha":f"{n+100:040x}",
            "author_time":author,"committer_time":committer,"repository":"o/r","pr_number":1,"provenance":{}}
PRE="2024-01-01T00:00:00+00:00"; AT=TFG; POST="2024-01-03T00:00:00+00:00"

class V4Tests(unittest.TestCase):
    def test_eligibility_v2_schema_uses_final_contract(self):
        schema=json.loads(Path("schemas/post_stage_c_eligibility_v2.schema.json").read_text())
        validate_eligibility_schema(schema)
        self.assertEqual(schema["properties"]["reconstruction_status"]["enum"],
                         ["reconstructed_focal_state", "reconstructed_base_state", "unresolved"])

    def test_eligibility_v2_rejects_inconsistent_eligible_row(self):
        schema=json.loads(Path("schemas/post_stage_c_eligibility_v2.schema.json").read_text())
        row={field:"" for field in schema["required"]}
        for field,spec in schema["properties"].items():
            if "const" in spec: row[field]=spec["const"]
        row.update(case_id="CASE_000000000000",stage_c_processability_status="processable",
                   stage_c_authoritative_record="x",stage_c_authoritative_record_sha256="0"*64,
                   stage_c_authority_validation_status="validated",tC="x",tC_precision="timestamp",
                   tC_status="derivable",tC_source="x",tFG="x",tFG_precision="timestamp",
                   tFG_status="derivable",tFG_source="x",primary_repository_cutoff="tFG",
                   first_generation_boundary_identifiable="yes",first_generation_boundary_basis="x",
                   repository="o/r",canonical_repository_url="https://github.com/o/r",pr_number="1",
                   source_linkage_reference="x",reconstruction_target_type="git_commit",
                   target_identity_status="unresolved",historical_availability_status="unresolved",
                   historical_state_reconstructible="unresolved",repository_component_status="not_assessed",
                   pr_component_status="not_assessed",issue_component_status="not_assessed",
                   ci_component_status="not_assessed",discussion_component_status="not_assessed",
                   reconstruction_status="unresolved",reconstruction_authority_ref="x",
                   retry_disposition="not_applicable",remaining_criteria_status="unresolved",
                   final_scientific_eligibility="eligible",adjudication_required="false")
        with self.assertRaises(ValueError): validate_eligibility_record(row,schema)
    def test_a_focal_committer_before(self): self.assertEqual(choose_reconstruction([c(1,PRE,PRE)],None,TFG)["status"],"reconstructed_focal_state")
    def test_b_focal_committer_equal(self): self.assertEqual(choose_reconstruction([c(1,AT,AT)],None,TFG)["selected"]["sha"],f"{1:040x}")
    def test_c_multiple_before_after(self):
        r=choose_reconstruction([c(1,PRE,PRE),c(2,PRE,PRE,(1,)),c(3,POST,POST,(2,))],None,TFG)
        self.assertEqual(r["selected"]["sha"],f"{2:040x}"); self.assertEqual(r["focal"]["first_post_tfg"]["sha"],f"{3:040x}"); self.assertEqual(r["focal"]["selected_to_first_post_relationship"],"ancestor")
    def test_d_committer_wins_cross_to_post(self):
        x=annotate_commit(c(1,PRE,POST),TFG,1); self.assertEqual((x["temporal_basis"],x["effective_time_relation"],x["author_time_sensitivity"]),("committer_time","after_tfg","crosses_tfg"))
    def test_e_committer_wins_cross_to_pre(self): self.assertEqual(annotate_commit(c(1,POST,PRE),TFG,1)["effective_time_relation"],"at_or_before_tfg")
    def test_f_author_fallback_pre(self): self.assertEqual(annotate_commit(c(1,PRE,None),TFG,1)["temporal_basis"],"author_time_fallback")
    def test_g_author_fallback_post(self): self.assertEqual(annotate_commit(c(1,POST,None),TFG,1)["effective_time_relation"],"after_tfg")
    def test_h_no_times(self): self.assertEqual(annotate_commit(c(1,None,None),TFG,1)["effective_time_relation"],"unknown")
    def test_i_mixed_bases(self):
        r=select_from_lineage([c(1,PRE,PRE),c(2,PRE,None,(1,))],TFG); self.assertEqual(r["selected"]["temporal_basis"],"author_time_fallback")
    def test_j_topology_temporal_conflict(self):
        r=choose_reconstruction([c(1,POST,POST),c(2,PRE,PRE,(1,))],None,TFG); self.assertEqual(r["reason"],"temporal_or_lineage_ambiguous")
    def test_k_no_focal_uses_base(self): self.assertEqual(choose_reconstruction([c(1,POST,POST)],[c(2,PRE,PRE)],TFG,"pr_base_ref")["status"],"reconstructed_base_state")
    def test_l_pr_base_ref_preserved(self): self.assertEqual(choose_reconstruction([], [c(2,PRE,PRE)],TFG,"pr_base_ref")["path"],"base")
    def test_m_unresolvable_base_ref(self): self.assertEqual(choose_reconstruction([],None,TFG)["status"],"unresolved")
    def test_n_default_substitution_explicit(self): self.assertEqual(choose_reconstruction([], [c(2,PRE,PRE)],TFG,"current_default_branch_substitution")["status"],"reconstructed_base_state")
    def test_o_incomplete_materialization_rejected(self):
        r=self._record(); r["materialization"]["complete_recursive_tree"]=False
        with self.assertRaises(ValueError): validate_record(r)
    def test_p_nonlinear_ancestry(self): self.assertEqual(select_from_lineage([c(1,PRE,PRE),c(2,PRE,PRE)],TFG)["temporal_consistency"],"temporal_or_lineage_ambiguous")
    def test_q_no_post_focal_needed(self): self.assertEqual(choose_reconstruction([c(1,PRE,PRE)],None,TFG)["status"],"reconstructed_focal_state")
    def test_r_exact_commit_tree_materialization(self): validate_record(self._record())
    def test_s_outcome_field_rejected(self):
        r=self._record(); r["provenance"]["outcome_class"]="PA"
        with self.assertRaises(ValueError): validate_record(r)
    def test_t_post_tfg_content_rejected(self):
        r=self._record(); r["focal_lineage"]["commits"][0]["commit_message"]="future"
        with self.assertRaises(ValueError): validate_record(r)
    def test_weak_base_route_uses_unique_external_parent(self):
        commits=[c(2,POST,POST,(1,)),c(3,POST,POST,(2,))]
        self.assertEqual(focal_root_external_parent(commits),(f"{1:040x}","unique_focal_root_external_parent"))
    def test_weak_base_route_rejects_ambiguous_root_parents(self):
        commit=c(3,POST,POST,(1,2))
        self.assertEqual(focal_root_external_parent([commit]),(None,"focal_root_external_parent_ambiguous"))
    def _record(self):
        lineage=select_from_lineage([c(1,PRE,PRE)],TFG); selected=lineage["selected"]
        return {"record_version":"historical-state-acquisition-v4","reconstruction_contract":"post-stage-c-reconstruction-v4",
                "reconstruction_status":"reconstructed_focal_state","selected_state":{"commit_sha":selected["sha"],"tree_sha":selected["tree_sha"]},
                "materialization":{"status":"materialized","complete_recursive_tree":True},"historical_observability":"not_confirmed",
                "focal_lineage":lineage,"provenance":{"outcome_inputs_enabled":False}}

if __name__ == "__main__": unittest.main()
