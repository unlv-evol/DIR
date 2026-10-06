"""Canonical live engine for Post-Stage-C v4 reconstruction."""
from __future__ import annotations
from pathlib import Path
from typing import Callable
from urllib.parse import quote

from .post_stage_c_transport import atomic_json, provider_get, utc_now
from .post_stage_c import (ACQUISITION, BOUNDARY, CONTRACT, PROCEDURE,
                              annotate_commit, choose_reconstruction, focal_root_external_parent,
                              read_csv, validate_record)
from .post_stage_c_transport import (_base_candidate, _commit, _get_json, _paged_commits,
                                   materialize)

def output_paths(cid: str) -> dict[str,Path]:
    return {"acquisition":Path(f"cases/reconstruction/{cid}/historical_state_acquisition_v4.json"),"boundary":Path(f"data/derived/historical_information/{cid}/historical_information_boundary_v4.json")}

def _ancestry_from_anchor(api: str, repository: str, anchor: str, tfg: str, config: dict,
                          get: Callable, limit: int=1000) -> tuple[list[dict],list[dict],str]:
    newest_to_oldest=[]; sources=[]; sha=anchor
    for _ in range(limit):
        body,source=_get_json(f"{api}/commits/{sha}",config,get); sources.append(source)
        if not isinstance(body,dict): return [],sources,"acquisition_failed"
        item=_commit(body,repository,None,source); newest_to_oldest.append(item)
        if annotate_commit(item,tfg,1)["effective_time_relation"]=="at_or_before_tfg":
            return list(reversed(newest_to_oldest)),sources,"complete"
        parents=item["parent_shas"]
        if not parents: return [],sources,"base_ancestry_exhausted"
        # First-parent traversal follows the established base branch through merges;
        # every parent remains preserved in the acquired commit record.
        sha=parents[0]
    return [],sources,"base_ancestry_truncated"

def execute_case(root: Path,row: dict[str,str],config: dict,*,get: Callable=provider_get,materializer: Callable=materialize,
                 persist: bool=True) -> dict:
    repo,num,tfg=row["repository"],int(row["pr_number"]),row["authoritative_tFG"]; api=f"https://api.github.com/repos/{repo}"
    pr,pr_source=_get_json(f"{api}/pulls/{num}",config,get)
    focal,focal_sources,focal_state=_paged_commits(f"{api}/pulls/{num}/commits",repo,num,config,get)
    base=[]; base_sources=[]; route=""; route_evidence={}; base_ref=pr.get("base",{}).get("ref","") if isinstance(pr,dict) else ""; ref_resolves=False
    focal_probe=choose_reconstruction(focal,None,tfg)
    if isinstance(pr,dict) and focal_state=="complete" and focal_probe["focal"]["selected"] is None:
        ref_body,ref_source=_get_json(f"{api}/git/ref/heads/{quote(base_ref,safe='/')}",config,get); base_sources.append(ref_source)
        ref_resolves=isinstance(ref_body,dict) and bool(ref_body.get("object",{}).get("sha"))
        if ref_resolves:
            base,more,state=_base_candidate(f"{api}/commits?sha={quote(base_ref,safe='')}&until={quote(tfg,safe='')}",repo,config,get); base_sources.extend(more)
            if state=="complete" and base: route="pr_base_ref"; route_evidence={"rule":"recorded_pr_base_ref_resolves","ref_object_sha":ref_body["object"]["sha"]}
        else:
            anchor,reason=focal_root_external_parent(focal)
            if anchor:
                base,more,state=_ancestry_from_anchor(api,repo,anchor,tfg,config,get); base_sources.extend(more)
                if state=="complete" and base: route="other_explicitly_justified_route"; route_evidence={"rule":"unique_focal_root_external_parent_then_first_parent_ancestry","anchor_sha":anchor,"anchor_reason":reason}
                else: route_evidence={"rule":"unique_focal_root_external_parent_ancestry","anchor_sha":anchor,"failure":state}
            else: route_evidence={"rule":"focal_root_external_parent","failure":reason}
    result=choose_reconstruction(focal,base if route else None,tfg,route)
    if focal_state!="complete" or not isinstance(pr,dict): result.update(status="unresolved",reason="acquisition_failed",selected=None)
    if result["path"]=="base" and not route: result.update(status="unresolved",reason="applicable_base_lineage_unresolved",selected=None)
    selected=result.get("selected"); mat=materializer(repo,selected["sha"],timeout=max(config["timeout"],180)) if selected else {"status":"not_attempted","complete_recursive_tree":False}
    if selected and not(mat.get("status")=="materialized" and mat.get("tree_sha")==selected["tree_sha"] and mat.get("parent_shas")==selected["parent_shas"]): result.update(status="unresolved",reason="tree_materialization_failed" if mat.get("status")!="materialized" else "commit_validation_failed")
    chosen=selected or {}; eligibility=next(r for r in read_csv(root/"cases/manifests/post_stage_c_eligibility.csv") if r["case_id"]==row["case_id"])
    record={"record_version":ACQUISITION,"reconstruction_contract":CONTRACT,"procedure_version":PROCEDURE,"case_id":row["case_id"],"repository":repo,"pr_number":num,
      "tFG":{"value":tfg,"source":"cases/manifests/stage_c_post_resolution_authority.csv"},"tC":{"value":eligibility["tC"],"source":eligibility["tC_source"]+"; not a selection input"},
      "reconstruction_path":result["path"],"reconstruction_status":result["status"],"unresolved_reasons":[result["reason"]] if result["reason"] else [],
      "selected_state":{"commit_sha":chosen.get("sha",""),"tree_sha":chosen.get("tree_sha",""),"author_time":chosen.get("author_time"),"committer_time":chosen.get("committer_time"),"effective_time":chosen.get("effective_time"),"temporal_basis":chosen.get("temporal_basis","unavailable"),"author_time_sensitivity":chosen.get("author_time_sensitivity","not_applicable")},
      "temporal_consistency":(result.get(result["path"]) or result["focal"])["temporal_consistency"],"lineage_source":"established_focal_pr","base_routing_source":route if result["path"]=="base" else "","base_lineage_ref":base_ref,
      "focal_lineage":result["focal"],"base_lineage":result.get("base"),"materialization":mat,"historical_observability":"not_confirmed",
      "provenance":{"pr":pr_source,"focal_pages":focal_sources,"base_pages":base_sources,"recorded_pr_base_ref_resolves":ref_resolves,"base_route_evidence":route_evidence,"current_default_branch_candidate_used":False,"current_pr_base_sha_provenance_only":pr.get("base",{}).get("sha","") if isinstance(pr,dict) else "","outcome_inputs_enabled":False,"post_tfg_content_admitted":False},"executed_at":utc_now()}
    validate_record(record)
    boundary={"boundary_record_version":BOUNDARY,"reconstruction_contract":CONTRACT,"case_id":row["case_id"],"repository":repo,"tFG":record["tFG"],"reconstruction_status":record["reconstruction_status"],"reconstruction_path":record["reconstruction_path"],"selected_state":record["selected_state"],"temporal_consistency":record["temporal_consistency"],"base_routing_source":record["base_routing_source"],"base_lineage_ref":base_ref,"materialization":mat,"historical_observability":"not_confirmed","unresolved_reasons":record["unresolved_reasons"],"provenance_references":[str(output_paths(row["case_id"])["acquisition"]),row["stage_c_authoritative_record"]]}
    if persist:
        paths=output_paths(row["case_id"]); atomic_json(root/paths["acquisition"],record); atomic_json(root/paths["boundary"],boundary)
    return record
