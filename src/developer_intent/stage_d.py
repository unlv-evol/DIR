"""Deterministic Stage D sampling and blinded reviewer-package preparation."""
from __future__ import annotations

import csv
import hashlib
import json
import random
import subprocess
from pathlib import Path

SEED = 20261005
PROCEDURE = "stage-d-stratified-validation-v1"
ELIGIBILITY = Path("cases/manifests/post_stage_c_eligibility.csv")
STAGE_C_AUTHORITY = Path("cases/manifests/stage_c_post_resolution_authority.csv")
SCREENING = Path("cases/manifests/screened_PA_PN_cases.csv")
OUTPUT = Path("cases/stage_d")
MANIFEST = OUTPUT / "stage_d_sampling_manifest.csv"
POPULATION_COUNTS = {"PA": 68, "PN": 43}
SAMPLE_COUNTS = {"PA": 20, "PN": 13}
JUDGMENT_FIELDS = (
    "first_generation_correct", "target_prompt_correct", "boundary_tFG_correct",
    "context_extraction", "specificity_extraction", "verification_extraction",
    "missing_information", "post_boundary_leakage", "overall_extraction",
    "correction_notes", "reviewer_notes",
)
REVIEW_FIELDS = ("case_id", "case_details", "conversation_url", "pr_url", *JUDGMENT_FIELDS)
MANIFEST_FIELDS = (
    "case_id", "stratum", "selection_order", "reviewer_order", "random_seed",
    "sampling_method", "population_size", "stratum_population_size",
    "stratum_sample_size", "sampling_fraction", "eligibility_source",
    "eligibility_source_sha256", "stage_c_authority_source",
    "stage_c_authority_sha256", "stage_c_record", "stage_c_record_sha256",
    "repository_remote", "reviewer_a_evidence_path", "reviewer_b_evidence_path",
    "sampling_procedure_version",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def repository_remote(root: Path) -> str:
    result = subprocess.run(
        ["git", "config", "--get", "remote.origin.url"], cwd=root,
        check=True, capture_output=True, text=True,
    )
    value = result.stdout.strip()
    if not value:
        raise ValueError("configured origin remote is empty")
    return value


def eligible_population(root: Path) -> dict[str, list[dict[str, str]]]:
    eligibility = read_csv(root / ELIGIBILITY)
    eligible = [row for row in eligibility if row["final_scientific_eligibility"] == "eligible"]
    if len(eligible) != 111 or len({row["case_id"] for row in eligible}) != 111:
        raise ValueError(f"eligible population is {len(eligible)}, expected 111 unique cases")
    screening = {row["case_id"]: row for row in read_csv(root / SCREENING)}
    population = {"PA": [], "PN": []}
    for row in eligible:
        case_id = row["case_id"]
        if case_id not in screening:
            raise ValueError(f"missing sampling stratum for {case_id}")
        stratum = screening[case_id]["Outcome_Class"]
        if stratum not in population:
            raise ValueError(f"invalid sampling stratum for {case_id}: {stratum}")
        population[stratum].append(row)
    for stratum, expected in POPULATION_COUNTS.items():
        population[stratum].sort(key=lambda row: row["case_id"])
        if len(population[stratum]) != expected:
            raise ValueError(f"{stratum} population is {len(population[stratum])}, expected {expected}")
    return population


def _rng(seed: int, purpose: str) -> random.Random:
    digest = hashlib.sha256(f"{seed}:{purpose}".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def sample_population(root: Path, seed: int = SEED) -> list[dict[str, str]]:
    population = eligible_population(root)
    selected: list[dict[str, str]] = []
    selection_order = 1
    for stratum in ("PA", "PN"):
        draw = _rng(seed, f"sample:{stratum}").sample(
            population[stratum], SAMPLE_COUNTS[stratum]
        )
        for row in draw:
            selected.append({**row, "stratum": stratum, "selection_order": str(selection_order)})
            selection_order += 1
    review = list(selected)
    _rng(seed, "review-order").shuffle(review)
    for order, row in enumerate(review, 1):
        row["reviewer_order"] = str(order)
    return review


def generate_sample(root: Path, seed: int = SEED) -> list[dict[str, str]]:
    selected = sample_population(root, seed)
    eligibility_hash = sha256(root / ELIGIBILITY)
    authority_hash = sha256(root / STAGE_C_AUTHORITY)
    remote = repository_remote(root)
    rows = []
    for row in selected:
        case_id = row["case_id"]
        record_path = Path(row["stage_c_authoritative_record"])
        if sha256(root / record_path) != row["stage_c_authoritative_record_sha256"]:
            raise ValueError(f"authoritative Stage C hash mismatch: {case_id}")
        rows.append({
            "case_id": case_id,
            "stratum": row["stratum"],
            "selection_order": row["selection_order"],
            "reviewer_order": row["reviewer_order"],
            "random_seed": str(seed),
            "sampling_method": "proportional_stratified_random_without_replacement",
            "population_size": "111",
            "stratum_population_size": str(POPULATION_COUNTS[row["stratum"]]),
            "stratum_sample_size": str(SAMPLE_COUNTS[row["stratum"]]),
            "sampling_fraction": "0.2972972973",
            "eligibility_source": str(ELIGIBILITY),
            "eligibility_source_sha256": eligibility_hash,
            "stage_c_authority_source": str(STAGE_C_AUTHORITY),
            "stage_c_authority_sha256": authority_hash,
            "stage_c_record": str(record_path),
            "stage_c_record_sha256": row["stage_c_authoritative_record_sha256"],
            "repository_remote": remote,
            "reviewer_a_evidence_path": f"cases/stage_d/reviewer_A/cases/{case_id}.json",
            "reviewer_b_evidence_path": f"cases/stage_d/reviewer_B/cases/{case_id}.json",
            "sampling_procedure_version": PROCEDURE,
        })
    _write_csv(root / MANIFEST, MANIFEST_FIELDS, rows)
    return rows


def _turn(turn: dict) -> dict:
    return {key: turn[key] for key in ("turn_id", "event_index", "role", "text")}


def _item(item: dict) -> dict:
    return {
        "item_id": item["id"],
        "normalized_text": item["text"],
        "source_turn_ids": item["source_turns"],
        "source_roles": item["source_roles"],
        "evidence_spans": item["evidence"],
    }


def _resolve_artifacts(first: dict, view: dict, case_id: str) -> list[dict]:
    candidates: dict[str, list[dict]] = {}
    for candidate in view.get("generated_technical_content_candidates", []):
        candidates.setdefault(candidate.get("candidate_id", ""), []).append(candidate)
    resolved = []
    for artifact_ref in first["artifact_refs"]:
        matches = candidates.get(artifact_ref, [])
        if len(matches) != 1:
            raise ValueError(
                f"artifact reference must resolve exactly once: {case_id}:{artifact_ref}:{len(matches)}"
            )
        candidate = matches[0]
        if candidate["source_response_id"] != first["response_turn_id"]:
            raise ValueError(f"selected artifact is not response-local: {case_id}:{artifact_ref}")
        artifact = {
            "artifact_id": candidate["candidate_id"],
            "source_response_id": candidate["source_response_id"],
            "artifact_type": candidate["kind"],
            "content": candidate["raw_text"],
        }
        if candidate.get("fence_language"):
            artifact["language"] = candidate["fence_language"]
        resolved.append(artifact)
    return resolved


def reviewer_case(root: Path, manifest_row: dict[str, str]) -> dict:
    source_path = root / manifest_row["stage_c_record"]
    if sha256(source_path) != manifest_row["stage_c_record_sha256"]:
        raise ValueError(f"Stage C record changed: {manifest_row['case_id']}")
    source = json.loads(source_path.read_text())
    linkage_path = root / "cases" / "manifests" / "linkage" / f"{source['case_id']}.json"
    linkage = json.loads(linkage_path.read_text())
    if linkage.get("case_id") != source["case_id"] or linkage.get("source_linkage_status") != "established":
        raise ValueError(f"authoritative linkage unavailable: {source['case_id']}")
    conversation_url = linkage.get("conversation_url", "")
    pr_url = linkage.get("pr_url", "")
    first = source["first_generation"]
    prior = source["admissible_prior_turns"]
    target = next((turn for turn in prior if turn["turn_id"] == first["target_prompt_id"]), None)
    if target is None:
        raise ValueError(f"target prompt absent from admissible turns: {source['case_id']}")
    view_path = root / source["input"]["stage_b_model_view_ref"]
    view = json.loads(view_path.read_text())
    # Stage C records the canonical JSON-object hash used as model input, not
    # the serialization-specific byte hash of the model-view file.
    if canonical_hash(view) != source["input"]["sha256"]:
        raise ValueError(f"Stage B canonical model-input hash mismatch: {source['case_id']}")
    response = next(
        (turn for turn in view["visible_turns"] if turn["turn_id"] == first["response_turn_id"]), None
    )
    if response is None or response["role"] != "assistant":
        raise ValueError(f"first-generation response unavailable: {source['case_id']}")
    if any(turn["event_index"] >= response["event_index"] for turn in prior):
        raise ValueError(f"post-boundary turn in authoritative prior turns: {source['case_id']}")
    artifacts = _resolve_artifacts(first, view, source["case_id"])
    return {
        "case_id": source["case_id"],
        "source_links": {"conversation_url": conversation_url, "pr_url": pr_url},
        "evidence_boundary": {
            "pre_boundary_conversation": "admissible_for_context_specificity_verification_validation",
            "resolved_first_generation_artifacts": "visible_only_for_first_generation_target_prompt_and_boundary_validation",
            "first_generation_response": "visible_only_for_first_generation_target_prompt_and_boundary_validation",
            "turns_after_first_generation_response": "excluded",
        },
        "first_generation": {
            "family": {
                "family_id": first["family_id"],
                "family_label": first["family_label"],
                "artifact_refs": first["artifact_refs"],
                "artifacts": artifacts,
            },
            "response_turn_id": first["response_turn_id"],
            "target_prompt_turn_id": first["target_prompt_id"],
            "boundary": first["boundary"],
            "tFG": source["temporal"]["tFG"]["value"],
        },
        "target_prompt": _turn(target),
        "pre_boundary_conversation": [_turn(turn) for turn in prior],
        "first_generation_response": _turn(response),
        "stage_c_extraction": {
            "Context": [_item(item) for item in source["context_supplied"]],
            "Specificity": [_item(item) for item in source["specificity_supplied"]],
            "Verification": [_item(item) for item in source["verification_supplied"]],
        },
        "provenance": {
            "authoritative_stage_c_record_sha256": manifest_row["stage_c_record_sha256"],
            "repository_relative_evidence_path": "",
            "checkpoint_commit": "assigned_after_reviewed_preparation_is_committed",
        },
    }


def prepare_review(root: Path) -> None:
    rows = read_csv(root / MANIFEST)
    if len(rows) != 33:
        raise ValueError("sampling manifest must contain 33 rows")
    for reviewer in ("A", "B"):
        review_rows = []
        for row in sorted(rows, key=lambda value: int(value["reviewer_order"])):
            relative = Path(row[f"reviewer_{reviewer.lower()}_evidence_path"])
            record = reviewer_case(root, row)
            record["provenance"]["repository_relative_evidence_path"] = str(relative)
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
            review_rows.append({"case_id": row["case_id"], "case_details": str(relative),
                                "conversation_url": record["source_links"]["conversation_url"],
                                "pr_url": record["source_links"]["pr_url"],
                                **{field: "" for field in JUDGMENT_FIELDS}})
        _write_csv(root / OUTPUT / f"reviewer_{reviewer}" / "stage_d_review.csv",
                   REVIEW_FIELDS, review_rows)


def validate(root: Path, seed: int = SEED) -> dict[str, int]:
    expected = generate_sample(root, seed)
    actual = read_csv(root / MANIFEST)
    if actual != expected or sample_population(root, seed) != sample_population(root, seed):
        raise ValueError("sampling is not deterministic")
    if len(actual) != 33 or len({row["case_id"] for row in actual}) != 33:
        raise ValueError("sample must contain 33 unique cases")
    counts = {s: sum(row["stratum"] == s for row in actual) for s in POPULATION_COUNTS}
    if counts != SAMPLE_COUNTS:
        raise ValueError(f"invalid sample counts: {counts}")
    reviewer_rows = []
    forbidden = ("reporting_stratum", "reconstruction_status", "reconstruction_path",
                 "historical_observability", "final_scientific_eligibility", "Outcome_Class",
                 "post_stage_c", "post_c_resolution")
    for reviewer in ("A", "B"):
        csv_path = root / OUTPUT / f"reviewer_{reviewer}" / "stage_d_review.csv"
        with csv_path.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream); rows = list(reader); fields = tuple(reader.fieldnames or ())
        if fields != REVIEW_FIELDS:
            raise ValueError(f"invalid reviewer {reviewer} CSV columns")
        if len(rows) != 33 or any(row[field] for row in rows for field in JUDGMENT_FIELDS):
            raise ValueError(f"invalid or prefilled reviewer {reviewer} CSV")
        reviewer_rows.append(rows)
        for row in rows:
            record = json.loads((root / row["case_details"]).read_text())
            if record["case_id"] != row["case_id"]:
                raise ValueError("review CSV/JSON case mismatch")
            linkage = json.loads((root / "cases" / "manifests" / "linkage" / f"{row['case_id']}.json").read_text())
            expected_links = {"conversation_url": linkage.get("conversation_url", ""),
                              "pr_url": linkage.get("pr_url", "")}
            if record.get("source_links") != expected_links:
                raise ValueError(f"reviewer links differ from authoritative linkage for {row['case_id']}")
            if row["conversation_url"] != expected_links["conversation_url"] or row["pr_url"] != expected_links["pr_url"]:
                raise ValueError(f"review CSV/JSON links differ for {row['case_id']}")
            serialized = json.dumps(record)
            if any(term in serialized for term in forbidden):
                raise ValueError(f"blinded field exposed for {row['case_id']}")
            response_index = record["first_generation_response"]["event_index"]
            if any(turn["event_index"] >= response_index for turn in record["pre_boundary_conversation"]):
                raise ValueError(f"post-boundary conversation exposed for {row['case_id']}")
            artifacts = record["first_generation"]["family"]["artifacts"]
            refs = record["first_generation"]["family"]["artifact_refs"]
            if [artifact["artifact_id"] for artifact in artifacts] != refs:
                raise ValueError(f"resolved artifact/reference mismatch for {row['case_id']}")
            if any(artifact["source_response_id"] != record["first_generation"]["response_turn_id"]
                   for artifact in artifacts):
                raise ValueError(f"later-response artifact exposed for {row['case_id']}")
    if [r["case_id"] for r in reviewer_rows[0]] != [r["case_id"] for r in reviewer_rows[1]]:
        raise ValueError("reviewer packages differ in cases or order")
    for row_a, row_b in zip(reviewer_rows[0], reviewer_rows[1]):
        if ((row_a["conversation_url"], row_a["pr_url"]) !=
                (row_b["conversation_url"], row_b["pr_url"])):
            raise ValueError(f"reviewer source links differ for {row_a['case_id']}")
        case_a = json.loads((root / row_a["case_details"]).read_text())
        case_b = json.loads((root / row_b["case_details"]).read_text())
        if case_a["first_generation"]["family"]["artifacts"] != case_b["first_generation"]["family"]["artifacts"]:
            raise ValueError(f"reviewer artifact evidence differs for {row_a['case_id']}")
    first = actual[0]
    if sha256(root / ELIGIBILITY) != first["eligibility_source_sha256"]:
        raise ValueError("eligibility ledger changed")
    if sha256(root / STAGE_C_AUTHORITY) != first["stage_c_authority_sha256"]:
        raise ValueError("Stage C authority changed")
    return {"eligible": 111, "PA_population": 68, "PN_population": 43,
            "sample": 33, "PA_sample": 20, "PN_sample": 13}
