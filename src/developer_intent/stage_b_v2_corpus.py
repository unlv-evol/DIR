"""Offline corpus materialization and V1-to-V2 representation impact reporting."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .generated_technical_content import build_v2_model_view, validate_v2_model_view

REPORT_VERSION = "stage-b-v1-v2-migration-report-v1"
IMPLEMENTATION_COMMIT = "092d30027b31c19b4b6a5bacbceab174a4025af6"
IMPLEMENTATION_CORRECTIONS = ["unambiguous-nested-markdown-fence-pairing-v1"]


def _read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", dir=path.parent, prefix=".stage_b_v2_",
                                         suffix=".tmp", encoding="utf-8",
                                         delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, indent=2, ensure_ascii=False, sort_keys=True)
            stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def _legacy_details(normalized: dict, v2: dict) -> tuple[dict[str, str], list[str]]:
    old = {item["artifact_id"]: item for item in normalized["artifact_candidates"]}
    mapped = {}
    duplicates = []
    for item in v2["generated_technical_content_candidates"]:
        legacy_id = item["legacy_artifact_id"]
        if legacy_id is None:
            continue
        if legacy_id in mapped:
            duplicates.append(legacy_id)
        if legacy_id not in old:
            raise ValueError(f"Unknown legacy mapping {legacy_id}")
        mapped[legacy_id] = item["candidate_id"]
    missing = sorted(set(old) - set(mapped))
    if duplicates or missing or len(mapped) != len(old):
        raise ValueError(f"Legacy mapping failure: duplicates={duplicates}, missing={missing}")
    return mapped, missing


def _current_stage_c_record(case_dir: Path) -> tuple[Path | None, dict | None]:
    records = []
    for path in case_dir.glob("stage_c_extraction*.json"):
        if path.name.endswith(".diagnostic.json"):
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        records.append((path, value))
    if not records:
        return None, None
    complete = [(path, value) for path, value in records
                if value.get("status", {}).get("stage_c_status") == "complete"]
    choices = complete or records
    return sorted(choices, key=lambda pair: pair[0].name)[-1]


def _brief(candidate: dict) -> str:
    text = " ".join(candidate["raw_text"].split())
    return text[:157] + ("..." if len(text) > 157 else "")


def _position_flags(new_candidates: list[dict], selected_event: int | None) -> dict:
    if selected_event is None:
        return {"before_selected_response": False, "in_selected_response": False,
                "after_selected_response": False}
    events = [item["source_event_index"] for item in new_candidates]
    return {"before_selected_response": any(event < selected_event for event in events),
            "in_selected_response": selected_event in events,
            "after_selected_response": any(event > selected_event for event in events)}


def _impact_category(v1_count: int, v2_count: int, relation: str,
                     new_candidates: list[dict], old_response_events: set[int]) -> str:
    if v1_count and v2_count < v1_count:
        return "migration_failure"
    if v1_count == 0:
        return "newly_recovered_from_zero" if v2_count else "still_zero_candidates"
    if not new_candidates:
        return "candidate_universe_unchanged"
    if relation == "T2":
        return "earlier_response_additions"
    new_events = {item["source_event_index"] for item in new_candidates}
    if new_events.issubset(old_response_events):
        return "same_response_additions_only"
    return "later_response_additions_only"


def build_corpus_report(root: Path, *, materialize: bool,
                        run_timestamp: str | None = None) -> dict:
    """Build or verify all ready V2 views and return a complete impact report."""
    timestamp = run_timestamp or datetime.now(timezone.utc).isoformat()
    screened = _read_csv(root / "cases/manifests/screened_PA_PN_cases.csv")
    ready = {row["case_id"]: row for row in screened
             if row["stage_b_readiness_status"] == "ready_for_stage_b"}
    summary = _read_csv(root / "cases/manifests/stage_b_summary.csv")
    complete_ids = {row["case_id"] for row in summary
                    if row["ready_for_stage_b"] == "true"
                    and row["ready_for_stage_c"] == "true"
                    and row["package_validation_status"] == "validated"
                    and row["model_view_status"] == "complete"
                    and row["stage_b_package_status"] == "existing_valid"}
    if set(ready) != complete_ids or len(ready) != 122:
        raise ValueError("Authoritative Stage-A-ready and Stage-B-complete populations disagree")

    case_rows = []
    kind_counts, container_counts = Counter(), Counter()
    completeness_counts, continuation_counts = Counter(), Counter()
    evidence_counts = Counter()
    kind_cases, container_cases = defaultdict(set), defaultdict(set)
    completeness_cases, continuation_cases = defaultdict(set), defaultdict(set)
    evidence_cases = defaultdict(set)
    generated = valid = total_v1 = total_v2 = exact = 0
    historical_paths = []

    for case_id in sorted(ready):
        stratum = ready[case_id]["Outcome_Class"]
        case_dir = root / "cases/conversations" / case_id
        normalized_path = case_dir / "normalized_conversation.json"
        v1_path = case_dir / "stage_c_model_view.json"
        v2_path = case_dir / "stage_c_model_view_v2.json"
        if not normalized_path.is_file() or not v1_path.is_file():
            raise ValueError(f"Missing Stage B input for {case_id}")
        normalized = json.loads(normalized_path.read_text(encoding="utf-8"))
        v1 = json.loads(v1_path.read_text(encoding="utf-8"))
        expected = build_v2_model_view(normalized)
        if v2_path.exists():
            actual = json.loads(v2_path.read_text(encoding="utf-8"))
            if actual != expected:
                raise ValueError(f"Existing V2 package differs from frozen producer: {case_id}")
        elif materialize:
            _atomic_json(v2_path, expected)
            generated += 1
            actual = expected
        else:
            raise ValueError(f"V2 package missing: {case_id}")
        validate_v2_model_view(actual); valid += 1

        v1_candidates = v1["artifact_candidates"]
        v2_candidates = actual["generated_technical_content_candidates"]
        legacy_map, missing = _legacy_details(normalized, actual)
        if missing:
            raise ValueError(f"V1 candidates missing for {case_id}: {missing}")
        new = [item for item in v2_candidates if item["legacy_artifact_id"] is None]
        total_v1 += len(v1_candidates); total_v2 += len(v2_candidates)
        exact += len(legacy_map)

        for item in v2_candidates:
            kind_counts[item["kind"]] += 1; kind_cases[item["kind"]].add(case_id)
            container_counts[item["container"]] += 1; container_cases[item["container"]].add(case_id)
            completeness_counts[item["completeness"]] += 1; completeness_cases[item["completeness"]].add(case_id)
            continuation_counts[item["continuation_status"]] += 1; continuation_cases[item["continuation_status"]].add(case_id)
            for value in item["detector_evidence"]:
                evidence_counts[value] += 1; evidence_cases[value].add(case_id)

        old_events = sorted({item["response_event_index"] for item in v1_candidates})
        new_events = sorted({item["source_event_index"] for item in v2_candidates})
        old_earliest = old_events[0] if old_events else None
        new_earliest = new_events[0] if new_events else None
        if old_earliest is None:
            relation = "TZ" if new_earliest is not None else "TN"
        elif new_earliest == old_earliest:
            relation = "T0"
        elif new_earliest is not None and new_earliest < old_earliest:
            relation = "T2"
        else:
            relation = "T1"

        stage_c_path, stage_c = _current_stage_c_record(case_dir)
        stage_status = stage_c.get("status", {}).get("stage_c_status", "") if stage_c else ""
        fg = stage_c.get("first_generation", {}) if stage_c else {}
        selected = fg.get("artifact_refs", [])
        selected_mapped = [legacy_map[item] for item in selected if item in legacy_map]
        selected_event = fg.get("response_event_index")
        flags = _position_flags(new, selected_event)
        if stage_c is None:
            triage = "NOT_APPLICABLE_NO_EXISTING_STAGE_C"
        elif (stage_status != "complete" and not v1_candidates and v2_candidates) \
                or len(selected_mapped) != len(selected) or flags["before_selected_response"]:
            triage = "STAGE_C_V2_RERUN_REQUIRED"
        elif flags["in_selected_response"]:
            triage = "HUMAN_IMPACT_REVIEW"
        else:
            triage = "NO_RERUN_INDICATED"

        turns = actual["visible_turns"]
        assistant_count = sum(turn["role"] == "assistant" for turn in turns)
        marker_count = sum(turn["text"].count("```") for turn in turns
                           if turn["role"] == "assistant")
        primary = _impact_category(len(v1_candidates), len(v2_candidates), relation,
                                   new, set(old_events))
        relationships = []
        for item in v2_candidates:
            legacy_id = item["legacy_artifact_id"]
            if legacy_id is not None:
                relationships.append({"v2_candidate_id": item["candidate_id"],
                                      "v1_artifact_id": legacy_id,
                                      "relationship": "exact_v1_equivalent",
                                      "addition_position": None})
                continue
            event = item["source_event_index"]
            if old_earliest is not None and event < old_earliest:
                position = "earlier_response_addition"
            elif event in old_events:
                position = "same_response_addition"
            else:
                position = "later_response_addition"
            relationships.append({"v2_candidate_id": item["candidate_id"],
                                  "v1_artifact_id": None,
                                  "relationship": "new_v2_candidate",
                                  "addition_position": position})
        earliest_candidates = [item for item in v2_candidates
                               if item["source_event_index"] == new_earliest]
        earlier_candidates = [item for item in new
                              if old_earliest is not None
                              and item["source_event_index"] < old_earliest]
        case_rows.append({
            "case_id": case_id, "stratum": stratum,
            "v1_candidate_count": len(v1_candidates), "v2_candidate_count": len(v2_candidates),
            "v1_candidate_response_count": len(old_events),
            "v2_candidate_response_count": len(new_events),
            "exact_legacy_mapping_count": len(legacy_map),
            "new_v2_candidate_count": len(new), "missing_v1_candidate_count": 0,
            "earliest_v1_response": (f"turn_{old_earliest:06d}" if old_earliest is not None else ""),
            "earliest_v2_response": (f"turn_{new_earliest:06d}" if new_earliest is not None else ""),
            "earliest_response_classification": relation,
            "representation_impact_category": primary,
            "candidate_relationships": relationships,
            "assistant_response_count": assistant_count,
            "triple_backtick_marker_count": marker_count,
            "zero_candidate_review_status": ("requires_manual_representation_review"
                                             if not v2_candidates else "not_applicable"),
            "prior_candidate_like_diagnostic": "not_locally_recorded",
            "earliest_v2_candidates": [{"candidate_id": item["candidate_id"],
                "kind": item["kind"], "container": item["container"],
                "completeness": item["completeness"],
                "continuation_status": item["continuation_status"],
                "detector_evidence": item["detector_evidence"],
                "source_description": _brief(item)} for item in earliest_candidates],
            "new_earlier_candidates": [{"candidate_id": item["candidate_id"],
                "kind": item["kind"], "container": item["container"],
                "completeness": item["completeness"],
                "detector_evidence": item["detector_evidence"],
                "source_description": _brief(item)} for item in earlier_candidates],
            "stage_c_record": (stage_c_path.relative_to(root).as_posix() if stage_c_path else ""),
            "stage_c_status": stage_status,
            "stage_c_extraction_version": stage_c.get("extraction_version", "") if stage_c else "",
            "stage_c_selected_v1_ids": selected,
            "stage_c_exact_mapped_v2_ids": selected_mapped,
            "all_selected_v1_map_exactly": len(selected_mapped) == len(selected),
            **flags, "future_stage_c_triage": triage,
            "development_case_flag": (
                "semantic_impact_review_required"
                if stage_status == "complete" and triage != "NO_RERUN_INDICATED"
                else "no_semantic_rerun_indicated_by_representation"
                if stage_status == "complete" else "not_applicable"),
            "v1_sha256": _sha(v1_path), "v2_sha256": _sha(v2_path),
        })
        historical_paths.extend([normalized_path, v1_path, case_dir / "package_status.json"])

    if exact != total_v1 or valid != 122:
        raise ValueError("Corpus validation invariant failed")

    def distribution(counts: Counter, cases: dict) -> dict:
        return {key: {"candidate_count": counts[key], "case_count": len(cases[key])}
                for key in sorted(counts)}

    def metrics(rows: list[dict], prefix: str) -> dict:
        key = f"{prefix}_candidate_count"
        response_key = f"{prefix}_candidate_response_count"
        return {"cases": len(rows), "zero_candidate_cases": sum(r[key] == 0 for r in rows),
                "one_candidate_cases": sum(r[key] == 1 for r in rows),
                "multiple_candidate_cases": sum(r[key] > 1 for r in rows),
                "total_candidates": sum(r[key] for r in rows),
                "candidate_bearing_responses": sum(r[response_key] for r in rows)}

    report = {
        "report_version": REPORT_VERSION, "implementation_commit": IMPLEMENTATION_COMMIT,
        "implementation_corrections": IMPLEMENTATION_CORRECTIONS,
        "run_timestamp": timestamp, "methodology_version": "dir-tfg-v2",
        "v1_package_version": "conversation-only-v1",
        "v2_package_version": "conversation-only-v2",
        "candidate_producer_version": "generated-technical-content-v2",
        "corpus": {"case_count": 122, "strata": dict(Counter(r["stratum"] for r in case_rows)),
                   "expected_v2_files": 122, "generated_v2_files": valid,
                   "created_in_this_invocation": generated,
                   "valid_v2_files": valid, "failures": 0},
        "v1": metrics(case_rows, "v1"), "v2": metrics(case_rows, "v2"),
        "difference": {"zero_candidate_cases_recovered": sum(
            r["v1_candidate_count"] == 0 and r["v2_candidate_count"] > 0 for r in case_rows),
            "cases_with_additional_candidates": sum(r["v2_candidate_count"] > r["v1_candidate_count"] for r in case_rows),
            "total_new_candidates": total_v2 - total_v1,
            "cases_unchanged_in_count": sum(r["v2_candidate_count"] == r["v1_candidate_count"] for r in case_rows),
            "cases_with_fewer_candidates": sum(r["v2_candidate_count"] < r["v1_candidate_count"] for r in case_rows),
            "missing_v1_candidates": 0},
        "zero_candidate_analysis": {
            "previous_v1_zero_candidate_cases": 22,
            "previous_diagnostic_candidate_like_cases": 17,
            "previous_diagnostic_case_mapping_locally_available": False,
            "recovered_from_v1_zero": [r["case_id"] for r in case_rows
                                       if r["v1_candidate_count"] == 0
                                       and r["v2_candidate_count"] > 0],
            "remaining_v2_zero_cases": [r["case_id"] for r in case_rows
                                        if r["v2_candidate_count"] == 0]},
        "by_stratum": {value: {"v1": metrics([r for r in case_rows if r["stratum"] == value], "v1"),
                                "v2": metrics([r for r in case_rows if r["stratum"] == value], "v2")}
                        for value in ("PA", "PN")},
        "legacy_mapping": {"total_v1_candidates": total_v1,
                           "exact_legacy_mappings": exact,
                           "new_v2_only_candidates": total_v2 - exact,
                           "v1_candidate_missing": 0, "changed_span": 0},
        "candidate_relationship_vocabulary": ["exact_v1_equivalent", "new_v2_candidate",
            "v1_candidate_missing", "changed_span", "same_response_addition",
            "later_response_addition", "earlier_response_addition"],
        "distributions": {"kind": distribution(kind_counts, kind_cases),
                          "container": distribution(container_counts, container_cases),
                          "completeness": distribution(completeness_counts, completeness_cases),
                          "continuation_status": distribution(continuation_counts, continuation_cases),
                          "detector_evidence": distribution(evidence_counts, evidence_cases)},
        "earliest_response_counts": dict(Counter(r["earliest_response_classification"] for r in case_rows)),
        "earliest_response_cases": {key: [r["case_id"] for r in case_rows
                                          if r["earliest_response_classification"] == key]
                                    for key in ("T0", "T1", "T2", "TZ", "TN")},
        "representation_impact_precedence": ["migration_failure", "newly_recovered_from_zero",
            "still_zero_candidates", "earlier_response_additions",
            "same_response_additions_only", "later_response_additions_only",
            "candidate_universe_unchanged"],
        "representation_impact_counts": dict(Counter(r["representation_impact_category"] for r in case_rows)),
        "future_stage_c_triage_counts": dict(Counter(r["future_stage_c_triage"] for r in case_rows)),
        "case_records": case_rows,
        "validation": {"package_validation": "passed", "legacy_mapping": "passed",
                       "historical_inputs_written": False, "openai_api_calls": 0,
                       "network_requests": 0, "stage_c_model_invocations": 0},
    }
    return report


def write_reports(root: Path, report: dict) -> tuple[Path, Path, Path]:
    base = root / "cases/manifests/stage_b_v1_v2_migration_report_v1"
    json_path, csv_path, md_path = base.with_suffix(".json"), base.with_suffix(".csv"), base.with_suffix(".md")
    for path in (json_path, csv_path, md_path):
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite migration report: {path}")
    _atomic_json(json_path, report)
    columns = ["case_id", "stratum", "v1_candidate_count", "v2_candidate_count",
               "exact_legacy_mapping_count", "new_v2_candidate_count",
               "earliest_v1_response", "earliest_v2_response",
               "earliest_response_classification", "representation_impact_category",
               "stage_c_status", "stage_c_extraction_version", "all_selected_v1_map_exactly",
               "before_selected_response", "in_selected_response", "after_selected_response",
               "future_stage_c_triage", "zero_candidate_review_status", "v2_sha256"]
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in report["case_records"]:
            writer.writerow({key: row[key] for key in columns})
    lines = ["# Stage B V1 → V2 migration report", "",
             f"- Report: `{report['report_version']}`",
             f"- Implementation commit: `{report['implementation_commit']}`",
             f"- Run timestamp: `{report['run_timestamp']}`",
             f"- Corpus: {report['corpus']['case_count']} cases ({report['corpus']['strata']})",
             f"- V2 files: {report['corpus']['valid_v2_files']} valid / {report['corpus']['expected_v2_files']} expected",
             f"- V1 candidates: {report['v1']['total_candidates']}",
             f"- V2 candidates: {report['v2']['total_candidates']}",
             f"- Exact legacy mappings: {report['legacy_mapping']['exact_legacy_mappings']}",
             f"- New V2-only candidates: {report['legacy_mapping']['new_v2_only_candidates']}",
             f"- Missing V1 candidates: {report['legacy_mapping']['v1_candidate_missing']}", "",
             "## Earliest-response impact", ""]
    for key in ("T0", "T1", "T2", "TZ", "TN"):
        cases = ", ".join(report["earliest_response_cases"][key]) or "none"
        lines.append(f"- {key}: {report['earliest_response_counts'].get(key, 0)} — "
                     + cases)
    lines += ["", "## Representation-impact categories", ""]
    for key, value in sorted(report["representation_impact_counts"].items()):
        lines.append(f"- `{key}`: {value}")
    lines += ["", "## Existing Stage C triage", ""]
    for key, value in sorted(report["future_stage_c_triage_counts"].items()):
        lines.append(f"- `{key}`: {value}")
    lines += ["", "## Candidate distributions", ""]
    for dimension in ("kind", "container", "completeness", "continuation_status"):
        lines.append(f"### {dimension}")
        lines.append("")
        for key, value in report["distributions"][dimension].items():
            lines.append(f"- `{key}`: {value['candidate_count']} candidates in "
                         f"{value['case_count']} cases")
        lines.append("")
    lines += ["## Zero-candidate comparison", "",
              f"- V1 zero-candidate cases: {report['v1']['zero_candidate_cases']}",
              f"- Recovered in V2: {report['difference']['zero_candidate_cases_recovered']}",
              f"- Remaining V2 zero-candidate cases: {report['v2']['zero_candidate_cases']}",
              "- The prior 17-of-22 candidate-like diagnostic is available only as an aggregate; no local case-level mapping was found.",
              "", "## Existing Stage C cases", ""]
    for row in report["case_records"]:
        if row["stage_c_record"]:
            lines.append(f"- `{row['case_id']}`: {row['stage_c_status']}; "
                         f"{row['earliest_response_classification']}; "
                         f"`{row['future_stage_c_triage']}`")
    lines += ["", "This report is structural representation analysis. It does not revise scientific family selection, boundaries, `tFG`, or eligibility.", ""]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, csv_path, md_path


def validate_report(report: dict) -> None:
    if (report.get("report_version") != REPORT_VERSION
            or report.get("implementation_commit") != IMPLEMENTATION_COMMIT
            or report.get("corpus", {}).get("case_count") != 122
            or report["corpus"].get("valid_v2_files") != 122
            or report["legacy_mapping"]["total_v1_candidates"]
            != report["legacy_mapping"]["exact_legacy_mappings"]
            or report["legacy_mapping"]["v1_candidate_missing"] != 0
            or len(report.get("case_records", [])) != 122
            or sum(report["representation_impact_counts"].values()) != 122):
        raise ValueError("Migration report invariant failed")
