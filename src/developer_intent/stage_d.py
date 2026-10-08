"""Deterministic Stage D sampling and blinded reviewer-package preparation."""
from __future__ import annotations

import csv
import html
import hashlib
import json
import random
import re
import subprocess
import zipfile
from xml.etree import ElementTree
from pathlib import Path
from urllib.parse import urlparse

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
VALIDATION_VALUES = {
    "E2:E34": ("yes", "no", "uncertain"),
    "F2:F34": ("yes", "no", "uncertain"),
    "G2:G34": ("yes", "no", "uncertain"),
    "H2:H34": ("correct", "partially_correct", "incorrect", "uncertain"),
    "I2:I34": ("correct", "partially_correct", "incorrect", "uncertain"),
    "J2:J34": ("correct", "partially_correct", "incorrect", "uncertain"),
    "K2:K34": ("none", "context", "specificity", "verification", "multiple", "uncertain"),
    "L2:L34": ("no", "yes", "uncertain"),
    "M2:M34": ("correct", "needs_correction", "uncertain"),
}
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


def _html_text(value: object) -> str:
    return html.escape(str(value), quote=True)


def _safe_link(value: object) -> str:
    url = str(value)
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"unsafe source URL: {url!r}")
    return _html_text(url)


def _definition_rows(values: dict[str, object]) -> str:
    return "".join(
        f"<dt>{_html_text(label)}</dt><dd>{_html_text(value)}</dd>"
        for label, value in values.items()
    )


def _turn_html(turn: dict, css_class: str = "turn") -> str:
    return (
        f'<article class="{css_class}" data-turn-id="{_html_text(turn["turn_id"])}" '
        f'data-event-index="{_html_text(turn["event_index"])}">'
        f'<h3>{_html_text(turn["role"].title())} · turn {_html_text(turn["turn_id"])}</h3>'
        f'<p class="metadata">Event index: {_html_text(turn["event_index"])}</p>'
        f'<pre class="turn-text">{_html_text(turn["text"])}</pre></article>'
    )


def render_review_html(record: dict) -> str:
    """Render one reviewer-safe JSON record as deterministic standalone HTML."""
    case_id = record["case_id"]
    links = record["source_links"]
    first = record["first_generation"]
    family = first["family"]
    boundary = record["evidence_boundary"]
    artifacts = []
    for position, artifact in enumerate(family["artifacts"], 1):
        metadata = {
            "Artifact ID": artifact["artifact_id"],
            "Order": position,
            "Source response": artifact["source_response_id"],
            "Type": artifact["artifact_type"],
            "Language": artifact.get("language", "not supplied"),
        }
        artifacts.append(
            f'<article class="artifact" data-artifact-id="{_html_text(artifact["artifact_id"])}">'
            f'<h3>Artifact {position}: {_html_text(artifact["artifact_id"])}</h3>'
            f'<dl>{_definition_rows(metadata)}</dl>'
            f'<pre class="artifact-content"><code>{_html_text(artifact["content"])}</code></pre>'
            '</article>'
        )
    extraction_sections = []
    for category in ("Context", "Specificity", "Verification"):
        items = []
        for item in record["stage_c_extraction"][category]:
            spans = "".join(
                f'<li><pre class="evidence-span">{_html_text(span)}</pre></li>'
                for span in item["evidence_spans"]
            ) or "<li>No evidence spans supplied.</li>"
            items.append(
                f'<article class="extraction-item" data-item-id="{_html_text(item["item_id"])}">'
                f'<h3>{_html_text(item["item_id"])}</h3>'
                f'<p class="normalized-text">{_html_text(item["normalized_text"])}</p>'
                f'<dl>{_definition_rows({"Source turn IDs": ", ".join(map(str, item["source_turn_ids"])), "Source roles": ", ".join(item["source_roles"])})}</dl>'
                f'<h4>Evidence spans</h4><ul class="evidence-spans">{spans}</ul></article>'
            )
        body = "".join(items) if items else '<p class="empty">No items extracted.</p>'
        extraction_sections.append(f'<section class="extraction"><h2>{category}</h2>{body}</section>')
    prior_turns = "".join(_turn_html(turn) for turn in record["pre_boundary_conversation"])
    boundary_rows = {key: value for key, value in boundary.items()}
    provenance = record["provenance"]
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Stage D evidence package · {_html_text(case_id)}</title>
<style>
:root {{ color-scheme: light; --navy:#17365d; --blue:#d9eaf7; --gold:#fff4cc; --ink:#1f2937; --line:#cbd5e1; --muted:#52606d; }}
* {{ box-sizing:border-box; }} body {{ margin:0; font:16px/1.5 Arial,sans-serif; color:var(--ink); background:#f6f8fa; }}
main {{ max-width:1120px; margin:auto; padding:24px; }} h1,h2,h3,h4 {{ color:var(--navy); }} h1 {{ margin-bottom:.25rem; }}
section,.turn,.artifact,.extraction-item {{ background:white; border:1px solid var(--line); border-radius:8px; margin:16px 0; padding:18px; }}
.restriction {{ background:var(--gold); border-left:6px solid #b58105; }} .admissible {{ background:#e8f5e9; border-left:6px solid #2e7d32; }}
dl {{ display:grid; grid-template-columns:minmax(180px,1fr) 3fr; gap:6px 16px; }} dt {{ font-weight:bold; }} dd {{ margin:0; overflow-wrap:anywhere; }}
pre {{ white-space:pre-wrap; overflow-wrap:anywhere; background:#f3f4f6; border:1px solid #e5e7eb; border-radius:5px; padding:14px; font:14px/1.45 ui-monospace,SFMono-Regular,Consolas,monospace; }}
.artifact-content {{ white-space:pre; overflow:auto; }} .metadata,.empty {{ color:var(--muted); }} a {{ color:#0563c1; }} ul.evidence-spans {{ padding-left:22px; }}
</style>
</head>
<body><main>
<header><p>Stage D reviewer evidence package</p><h1>{_html_text(case_id)}</h1><p>Human-readable companion to the authoritative reviewer-safe JSON.</p></header>
<section id="source-links"><h2>Source URLs</h2><p><a href="{_safe_link(links["conversation_url"])}" rel="noopener noreferrer">Authoritative conversation</a></p><p><a href="{_safe_link(links["pr_url"])}" rel="noopener noreferrer">Authoritative pull request</a> — provenance only; PR content is inadmissible for independent Context/Specificity/Verification validation.</p></section>
<section id="evidence-boundary"><h2>Evidence boundary</h2><div class="admissible"><strong>Admissible C/S/V evidence:</strong> only the pre-boundary conversation shown below.</div><div class="restriction"><strong>Restricted:</strong> resolved artifacts and the full first-generation response are visible only to validate first-generation identity, target prompt, boundary, and tFG. Turns after the response are excluded. The PR URL is provenance only.</div><dl>{_definition_rows(boundary_rows)}</dl></section>
<section id="first-generation"><h2>First-generation family and boundary</h2><dl>{_definition_rows({"Family ID": family["family_id"], "Family label": family["family_label"], "Artifact references": ", ".join(family["artifact_refs"]), "Response turn ID": first["response_turn_id"], "Target prompt turn ID": first["target_prompt_turn_id"], "Boundary": first["boundary"], "tFG": first["tFG"]})}</dl></section>
<section id="target-prompt"><h2>Target prompt</h2>{_turn_html(record["target_prompt"], "target-prompt")}</section>
<section id="pre-boundary-conversation"><h2>Pre-boundary conversation</h2><p class="admissible">These ordered turns are the only admissible conversation evidence for C/S/V validation.</p>{prior_turns}</section>
<section id="selected-artifacts"><h2>Selected first-generation artifacts</h2><p class="restriction">Use only for first-generation, target-prompt, boundary, and tFG validation.</p>{''.join(artifacts)}</section>
<section id="first-generation-response"><h2>Full first-generation response</h2><p class="restriction">This response cannot supply C/S/V evidence.</p>{_turn_html(record["first_generation_response"], "first-generation-response")}</section>
<section id="stage-c-extraction"><h2>Authoritative Stage C extraction</h2><p>Review each supplied item against admissible pre-boundary evidence and its recorded provenance.</p>{''.join(extraction_sections)}</section>
<section id="provenance"><h2>Provenance</h2><dl>{_definition_rows({"Authoritative Stage C record SHA-256": provenance["authoritative_stage_c_record_sha256"], "Reviewer-safe JSON": provenance["repository_relative_evidence_path"], "Checkpoint commit": provenance["checkpoint_commit"]})}</dl></section>
</main></body></html>
'''


def prepare_review_html(root: Path) -> dict[str, int]:
    result: dict[str, int] = {}
    for reviewer in ("A", "B"):
        directory = root / OUTPUT / f"reviewer_{reviewer}"
        rows = read_csv(directory / "stage_d_review.csv")
        if len(rows) != 33:
            raise ValueError(f"reviewer {reviewer} CSV must contain 33 rows")
        expected = set()
        for row in rows:
            json_path = root / row["case_details"]
            record = json.loads(json_path.read_text(encoding="utf-8"))
            if record["case_id"] != row["case_id"]:
                raise ValueError(f"reviewer {reviewer} CSV/JSON case mismatch")
            html_path = json_path.with_suffix(".html")
            html_path.write_text(render_review_html(record), encoding="utf-8")
            expected.add(html_path)
        actual = set((directory / "cases").glob("*.html"))
        if actual != expected:
            raise ValueError(f"reviewer {reviewer} HTML set differs from reviewer JSON set")
        result[f"reviewer_{reviewer}"] = len(actual)
    return result


def validate_review_html(root: Path, reviewer: str) -> int:
    directory = root / OUTPUT / f"reviewer_{reviewer}"
    rows = read_csv(directory / "stage_d_review.csv")
    expected_paths = {(root / row["case_details"]).with_suffix(".html") for row in rows}
    actual_paths = set((directory / "cases").glob("*.html"))
    if len(rows) != 33 or actual_paths != expected_paths:
        raise ValueError(f"reviewer {reviewer} HTML package is not the expected 33-case set")
    for row in rows:
        json_path = root / row["case_details"]
        record = json.loads(json_path.read_text(encoding="utf-8"))
        html_path = json_path.with_suffix(".html")
        if html_path.read_text(encoding="utf-8") != render_review_html(record):
            raise ValueError(f"reviewer {reviewer} HTML differs from reviewer-safe JSON: {row['case_id']}")
    return len(actual_paths)


def _xlsx_cells(archive: zipfile.ZipFile, sheet_name: str) -> tuple[dict[str, str], dict[str, str], dict[str, tuple[str, ...]]]:
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
          "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
          "p": "http://schemas.openxmlformats.org/package/2006/relationships"}
    workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
    relationship_id = next(sheet.attrib[f"{{{ns['r']}}}id"] for sheet in workbook.findall("x:sheets/x:sheet", ns)
                           if sheet.attrib["name"] == sheet_name)
    rels = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    target = next(rel.attrib["Target"] for rel in rels.findall("p:Relationship", ns)
                  if rel.attrib["Id"] == relationship_id)
    target = target.lstrip("/")
    if not target.startswith("xl/"):
        target = "xl/" + target
    sheet = ElementTree.fromstring(archive.read(target))
    values, formulas = {}, {}
    for cell in sheet.findall(".//x:c", ns):
        address = cell.attrib["r"]
        value = cell.find("x:v", ns); formula = cell.find("x:f", ns)
        values[address] = "" if value is None or value.text is None else value.text
        if formula is not None and formula.text is not None:
            formulas[address] = formula.text
    validations = {}
    for item in sheet.findall("x:dataValidations/x:dataValidation", ns):
        formula = item.find("x:formula1", ns)
        raw = "" if formula is None or formula.text is None else formula.text.strip('"')
        validations[item.attrib["sqref"]] = tuple(raw.split(",")) if raw else ()
    return values, formulas, validations


def validate_workbook(root: Path, reviewer: str) -> dict[str, int]:
    csv_path = root / OUTPUT / f"reviewer_{reviewer}" / "stage_d_review.csv"
    xlsx_path = root / OUTPUT / f"reviewer_{reviewer}" / "stage_d_review.xlsx"
    rows = read_csv(csv_path)
    if not xlsx_path.is_file():
        raise ValueError(f"missing reviewer {reviewer} XLSX")
    with zipfile.ZipFile(xlsx_path) as archive:
        values, formulas, validations = _xlsx_cells(archive, "Review")
        instructions, _, instruction_validations = _xlsx_cells(archive, "Instructions")
        names = set(archive.namelist())
    if tuple(values.get(f"{chr(65 + index)}1", "") for index in range(15)) != REVIEW_FIELDS:
        raise ValueError(f"reviewer {reviewer} XLSX columns differ from CSV")
    if len(rows) != 33 or any(re.match(r"^[A-O](?:3[5-9]|[4-9]\d)", address) for address in values):
        raise ValueError(f"reviewer {reviewer} XLSX row count is not 33")
    for row_number, row in enumerate(rows, 2):
        expected = [row[field] for field in REVIEW_FIELDS]
        actual = [values.get(f"{chr(65 + index)}{row_number}", "") for index in range(15)]
        if actual != expected:
            raise ValueError(f"reviewer {reviewer} XLSX/CSV mismatch at row {row_number}")
        html_relative = f'cases/{row["case_id"]}.html'
        if formulas.get(f"B{row_number}", "") != f'HYPERLINK("{html_relative}","{row["case_details"]}")':
            raise ValueError(f"reviewer {reviewer} case-details hyperlink mismatch at B{row_number}")
        for column, field in (("C", "conversation_url"), ("D", "pr_url")):
            formula = formulas.get(f"{column}{row_number}", "")
            if formula != f'HYPERLINK("{row[field]}","{row[field]}")':
                raise ValueError(f"reviewer {reviewer} hyperlink mismatch at {column}{row_number}")
    if validations != VALIDATION_VALUES or instruction_validations:
        raise ValueError(f"reviewer {reviewer} dropdown validation mismatch")
    if any(range_name.startswith(("N", "O")) for range_name in validations):
        raise ValueError(f"reviewer {reviewer} free-text columns have dropdowns")
    instruction_text = " ".join(instructions.values())
    for phrase in ("case_details is the primary Stage D evidence package",
                   "Only pre-boundary conversation information is admissible",
                   "PR content is not admissible evidence"):
        if phrase not in instruction_text:
            raise ValueError(f"reviewer {reviewer} workbook guidance is incomplete")
    serialized = " ".join(values.values()) + " " + instruction_text
    if "/Users/" in serialized or "\\Users\\" in serialized:
        raise ValueError(f"reviewer {reviewer} workbook contains an absolute local path")
    if "xl/worksheets/sheet1.xml" not in names or "xl/worksheets/sheet2.xml" not in names:
        raise ValueError(f"reviewer {reviewer} workbook structure is incomplete")
    return {"rows": len(rows), "columns": len(REVIEW_FIELDS), "dropdowns": len(validations)}


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
        scientific_a = {key: value for key, value in case_a.items() if key != "provenance"}
        scientific_b = {key: value for key, value in case_b.items() if key != "provenance"}
        if scientific_a != scientific_b:
            raise ValueError(f"reviewer scientific evidence differs for {row_a['case_id']}")
    first = actual[0]
    if sha256(root / ELIGIBILITY) != first["eligibility_source_sha256"]:
        raise ValueError("eligibility ledger changed")
    if sha256(root / STAGE_C_AUTHORITY) != first["stage_c_authority_sha256"]:
        raise ValueError("Stage C authority changed")
    workbook_a = validate_workbook(root, "A")
    workbook_b = validate_workbook(root, "B")
    if workbook_a != workbook_b:
        raise ValueError("reviewer workbook structures differ")
    html_count = validate_review_html(root, "A") + validate_review_html(root, "B")
    return {"eligible": 111, "PA_population": 68, "PN_population": 43,
            "sample": 33, "PA_sample": 20, "PN_sample": 13,
            "reviewer_workbooks": 2,
            "reviewer_html_files": html_count}
