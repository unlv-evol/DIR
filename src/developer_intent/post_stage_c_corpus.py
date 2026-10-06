"""Corpus-wide orchestration for the frozen Post-C v4 procedure."""
from __future__ import annotations
import csv,json
from pathlib import Path
from urllib.parse import urlparse

from .post_stage_c import (BOUNDARY, CONTRACT, ELIGIBILITY_CONTRACT, ELIGIBILITY_SCHEMA,
                           ELIGIBILITY_TARGET, PROCEDURE, authority, read_csv,
                           sha256_bytes, validate_eligibility_record,
                           validate_eligibility_schema, validate_record)
from .post_stage_c_engine import execute_case,output_paths

MANIFEST=Path("cases/manifests/post_stage_c_v4_corpus_authority.csv")
ELIGIBILITY=Path("cases/manifests/post_stage_c_eligibility.csv")
ELIGIBILITY_SCHEMA_PATH=Path("schemas/post_stage_c_eligibility_v2.schema.json")
FIELDS=("case_id","reporting_stratum","authoritative_tFG","reconstruction_status","reconstruction_path","selected_commit_sha","selected_tree_sha","selected_author_time","selected_committer_time","selected_effective_time","temporal_basis","author_time_sensitivity","temporal_consistency","lineage_source","base_routing_source","materialization_status","historical_observability","unresolved_reasons","acquisition_record","boundary_record","execution_disposition")

def population(root: Path) -> list[dict[str,str]]:
    auth=authority(root)
    if len(auth)!=111: raise ValueError(f"authoritative Stage-C-processable population is {len(auth)}, expected 111")
    rows=[]
    for cid,stage in auth.items():
        link=json.loads((root/f"cases/manifests/linkage/{cid}.json").read_text()); parts=urlparse(link["canonical_pr_url"]).path.strip("/").split("/")
        rows.append({"case_id":cid,"reporting_stratum":link["Outcome_Class"],"repository":"/".join(parts[:2]),"pr_number":str(link["pr_number"]),"authoritative_tFG":stage["tFG"],"stage_c_authoritative_record":stage["authoritative_record_path"]})
    return rows

def _scientific(record: dict) -> dict:
    return {k:record[k] for k in ("case_id","repository","pr_number","tFG","reconstruction_path","reconstruction_status","unresolved_reasons","selected_state","temporal_consistency","lineage_source","base_routing_source","base_lineage_ref","historical_observability")}

def _row(source: dict,record: dict,disposition: str) -> dict[str,str]:
    selected=record["selected_state"]; paths=output_paths(source["case_id"])
    return {"case_id":source["case_id"],"reporting_stratum":source["reporting_stratum"],"authoritative_tFG":source["authoritative_tFG"],"reconstruction_status":record["reconstruction_status"],"reconstruction_path":record["reconstruction_path"],"selected_commit_sha":selected["commit_sha"],"selected_tree_sha":selected["tree_sha"],"selected_author_time":selected["author_time"] or "","selected_committer_time":selected["committer_time"] or "","selected_effective_time":selected["effective_time"] or "","temporal_basis":selected["temporal_basis"],"author_time_sensitivity":selected["author_time_sensitivity"],"temporal_consistency":record["temporal_consistency"],"lineage_source":record["lineage_source"],"base_routing_source":record["base_routing_source"],"materialization_status":record["materialization"]["status"],"historical_observability":record["historical_observability"],"unresolved_reasons":";".join(record["unresolved_reasons"]),"acquisition_record":str(paths["acquisition"]),"boundary_record":str(paths["boundary"]),"execution_disposition":disposition}

def _write(path: Path,rows: list[dict[str,str]]) -> None:
    temp=path.with_suffix(".csv.tmp")
    with temp.open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=FIELDS,lineterminator="\n");writer.writeheader();writer.writerows(rows)
    temp.replace(path)

def run(root: Path,config: dict) -> list[dict[str,str]]:
    sources=population(root); summary=[]
    checkpoint={r["case_id"]:r for r in read_csv(root/MANIFEST)} if (root/MANIFEST).exists() else {}
    for index,source in enumerate(sources,1):
        paths=output_paths(source["case_id"]); existing_path=root/paths["acquisition"]
        if source["case_id"] in checkpoint:
            existing=json.loads(existing_path.read_text()); validate_record(existing)
            row=checkpoint[source["case_id"]]
            if row["reconstruction_status"]!=existing["reconstruction_status"]: raise RuntimeError(f"checkpoint_record_discrepancy:{source['case_id']}")
            summary.append(row); continue
        if existing_path.exists():
            existing=json.loads(existing_path.read_text()); validate_record(existing)
            candidate=execute_case(root,source,config,persist=False)
            if _scientific(existing)!=_scientific(candidate):
                raise RuntimeError(f"accepted_v4_record_discrepancy:{source['case_id']}")
            disposition="previously_executed_revalidated_identical"
        else:
            candidate=execute_case(root,source,config,persist=True); disposition="corpus_execution"
        summary.append(_row(source,candidate,disposition)); _write(root/MANIFEST,summary)
    if len(summary)!=111 or len({r['case_id'] for r in summary})!=111: raise ValueError("corpus authority manifest is not one-to-one")
    return summary

def validate_complete(root: Path) -> list[dict[str,str]]:
    rows=read_csv(root/MANIFEST)
    if len(rows)!=111 or {r['case_id'] for r in rows}!={r['case_id'] for r in population(root)}: raise ValueError("invalid corpus authority population")
    for row in rows:
        record=json.loads((root/row["acquisition_record"]).read_text()); validate_record(record)
        if row["reconstruction_status"]!=record["reconstruction_status"]: raise ValueError("summary/record status mismatch")
        if not (root/row["boundary_record"]).is_file(): raise ValueError("missing boundary record")
    return rows


def proposed_eligibility(root: Path) -> tuple[list[dict[str, str]], dict]:
    """Derive the complete eligibility ledger in memory from final authority."""
    schema=json.loads((root/ELIGIBILITY_SCHEMA_PATH).read_text()); validate_eligibility_schema(schema)
    stage=authority(root); corpus=read_csv(root/MANIFEST); previous=read_csv(root/ELIGIBILITY)
    if len(stage)!=111 or len(corpus)!=111 or len(previous)!=111:
        raise ValueError("eligibility populations must each contain 111 rows")
    corpus_by={r["case_id"]:r for r in corpus}; previous_by={r["case_id"]:r for r in previous}
    if len(corpus_by)!=111 or len(previous_by)!=111 or set(stage)!=set(corpus_by) or set(stage)!=set(previous_by):
        raise ValueError("eligibility population mismatch or duplicate case")
    fields=schema["required"]; rows=[]
    for case_id in stage:
        source,old,summary=stage[case_id],previous_by[case_id],corpus_by[case_id]
        acquisition_path=root/summary["acquisition_record"]; boundary_path=root/summary["boundary_record"]
        acquisition=json.loads(acquisition_path.read_text()); boundary=json.loads(boundary_path.read_text())
        validate_record(acquisition)
        tfg=source["tFG"]; selected=acquisition.get("selected_state",{}); material=acquisition.get("materialization",{})
        boundary_ok=(boundary.get("boundary_record_version")==BOUNDARY and
                     boundary.get("reconstruction_contract")==CONTRACT and
                     boundary.get("case_id")==case_id and
                     boundary.get("tFG",{}).get("value")==tfg and
                     boundary.get("reconstruction_status")==acquisition.get("reconstruction_status") and
                     boundary.get("selected_state",{}).get("commit_sha")==selected.get("commit_sha") and
                     boundary.get("selected_state",{}).get("tree_sha")==selected.get("tree_sha") and
                     boundary.get("materialization",{}).get("status")=="materialized" and
                     boundary.get("materialization",{}).get("complete_recursive_tree") is True)
        reconstructed=(acquisition.get("reconstruction_status") in {"reconstructed_focal_state","reconstructed_base_state"} and
                       acquisition.get("temporal_consistency")=="consistent" and
                       len(selected.get("commit_sha",""))==40 and len(selected.get("tree_sha",""))==40 and
                       material.get("status")=="materialized" and material.get("complete_recursive_tree") is True and
                       boundary_ok)
        boundary_identifiable=(source["stage_c_processability_status"]=="processable" and bool(tfg) and
                               source["authoritative_record_path"] and source["authority_basis"])
        if not boundary_identifiable or not reconstructed:
            raise ValueError(f"authoritative eligibility criterion unresolved:{case_id}")
        stage_record=root/source["authoritative_record_path"]
        row=dict(old)
        row.update({
            "manifest_schema_version":ELIGIBILITY_SCHEMA,
            "reconstruction_contract_version":CONTRACT,
            "reconstruction_procedure_version":PROCEDURE,
            "eligibility_contract_version":ELIGIBILITY_CONTRACT,
            "stage_c_authoritative_record":source["authoritative_record_path"],
            "stage_c_authoritative_record_sha256":sha256_bytes(stage_record.read_bytes()),
            "tFG":tfg,"tFG_precision":"timestamp","tFG_status":"derivable","tFG_source":source["authoritative_record_path"],
            "first_generation_boundary_identifiable":"yes",
            "first_generation_boundary_basis":"authoritative_stage_c_boundary_and_tFG",
            "reconstruction_target_rule":ELIGIBILITY_TARGET,
            "candidate_target_identifier":"",
            "authoritative_target_identifier":selected["commit_sha"],
            "target_identity_status":"established",
            "target_identity_basis":"final_post_stage_c_selected_commit_and_tree",
            "historical_availability_status":"at_or_before",
            "historical_availability_basis":f"{selected['temporal_basis']}:effective_time_at_or_before_tFG",
            "historical_state_reconstructible":"yes",
            "repository_component_status":"available",
            "pr_component_status":"not_assessed","issue_component_status":"not_assessed",
            "ci_component_status":"not_assessed","discussion_component_status":"not_assessed",
            "reconstruction_status":acquisition["reconstruction_status"],
            "reconstruction_attempt_id":f"post-stage-c-v4:{case_id}",
            "reconstruction_evidence_ref":summary["acquisition_record"],
            "reconstruction_log_ref":summary["boundary_record"],
            "reconstruction_authority_ref":f"{MANIFEST}#{case_id}",
            "failure_category":"","failure_reason":"","retry_disposition":"not_applicable",
            "remaining_criteria_status":"all_satisfied","final_scientific_eligibility":"eligible",
            "exclusion_reason":"","adjudication_required":"false",
            "notes":"Eligibility derived from authoritative Stage C and final Post-C v4 records; PA/PN and historical observability were not eligibility inputs.",
        })
        row={field:row[field] for field in fields}; validate_eligibility_record(row,schema); rows.append(row)
    return rows,schema


def write_eligibility(root: Path) -> list[dict[str, str]]:
    """Atomically replace the active ledger after complete in-memory validation."""
    rows,schema=proposed_eligibility(root); path=root/ELIGIBILITY; temp=path.with_suffix(".csv.tmp")
    with temp.open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=schema["required"],lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    temp.replace(path)
    return rows


def validate_eligibility(root: Path) -> list[dict[str, str]]:
    schema=json.loads((root/ELIGIBILITY_SCHEMA_PATH).read_text()); validate_eligibility_schema(schema)
    rows=read_csv(root/ELIGIBILITY)
    if len(rows)!=111 or len({r["case_id"] for r in rows})!=111 or {r["case_id"] for r in rows}!=set(authority(root)):
        raise ValueError("invalid eligibility population")
    for row in rows: validate_eligibility_record(row,schema)
    return rows
