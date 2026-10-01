# Repository Structure — Protocol v5

[`docs/architecture.md`](architecture.md) defines stage order; the [operational protocol](../protocols/experiment_protocol.md) defines methodology. This document maps current and planned artifacts to locations.

```text
developer-intent-reconstruction/
├── AGENTS.md
├── README.md
├── pyproject.toml
├── Makefile
├── .gitignore
├── config/
├── schemas/
├── protocols/
├── decisions/
├── data/
│   ├── raw/                         # inherited index/archive, unchanged
│   ├── intermediate/                # screening outputs and isolated caches
│   └── derived/
│       └── historical_information/  # conceptual H_i(tFG) indexes
├── cases/
│   ├── README.md
│   ├── manifests/                   # stable IDs and study-role assignments
│   ├── conversations/               # isolated conversation-only packages
│   ├── reconstruction/              # Post-C acquisition records, not Stage C input
│   └── raw/                         # historical audit packages, never SAFE
├── pilot_analysis/
│   └── conversation/               # location for versioned conversation records
├── safe/reconstruction/
├── sealed/evaluation/
├── pipeline/
│   ├── screening/
│   ├── extraction/                 # conversation-first acquisition foundation
│   ├── stage_c/                    # two-pass conversation extraction CLI
│   ├── post_stage_c/               # offline eligibility/reconstruction contracts
│   ├── partitioning/
│   ├── family_construction/
│   ├── snapshot/
│   ├── localization/
│   ├── retrieval/
│   ├── selection/
│   ├── evidence_engineering/
│   ├── reconstruction/
│   └── evaluation/
├── src/developer_intent/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── leakage/
├── annotations/
├── experiments/
├── results/
├── provenance/
├── scripts/
└── docs/
```

`data/derived/historical_information/` is a planned Stage F location. No speculative raw or retrieval schema is implied by this tree.

## Case identity and manifests

Stable `case_id`, conversation, turn, response, and artifact identifiers do not change with study role.

Stage A writes versioned `screened_PA_PN_cases.csv`, `eligible_PA_PN_cases.csv`, and `stage_a_summary.md` after authorized execution. The screened manifest has scientific eligibility plus separate operational Stage B readiness metadata. The eligible manifest contains confirmed eligible records. A pending case may enter Stage B packaging only when its explicit readiness passes and its sole unresolved reasons are the Stage C/`tFG` deferred conditions; it remains absent from the eligible manifest. Future `discovery_cases.csv` and `heldout_cases.csv` represent the post-freeze resolved corpus split, with no duplicate case directories.

`cases/manifests/stage_a_correspondence_review.csv` is the restricted, temporary human interface between Stage A automated and manual activities. Completed rows import into canonical `cases/manifests/correspondence_reviews/<case_id>.json`; the CSV does not replace those schema-validated records.

`cases/manifests/correspondence_evidence/<case_id>.json` contains the checksum-bound, minimal evidence packet supporting a Stage A semantic correspondence judgment. These restricted administrative packets are not conversation packages, SAFE inputs, or downstream reconstruction evidence.

`cases/manifests/source_linkage_corrections/<case_id>.json` stores verified, versioned overlays for demonstrated errors in inherited conversation linkage. The inherited source CSV remains unchanged, and prior review/evidence versions remain in restricted history locations.

The Stage A run also derives restricted `cases/manifests/case_mapping.csv` deterministically from the PatchPrompt source index and screened rows. It maps neutral Case ID to PR identifier and PA/PN, with complementary source/conversation identifiers. It is a researcher-only deliverable outside the Stage B conversation package; the richer `linkage/*.json` records remain separate. Stage C never receives either mapping.

Restricted Stage A manual PR/conversation judgments are stored as `cases/manifests/correspondence_reviews/<case_id>.json` and retained outside Stage B/C model input. Correspondence `yes` may satisfy that eligibility criterion, `no` excludes, and `unresolved` remains pending. Stage A records source/provenance linkage separately; source-index pairing alone does not automatically establish semantic task correspondence. Stage A also records a separate Git commit-object accessibility probe; it does not inspect historical project evidence or establish reconstructibility at `tFG`.

## Conversation-only and frozen records

`cases/conversations/<case_id>/` holds only neutral ID, temporal source/precision, complete original-order conversation, and stable turn/artifact references needed for conversation-side extraction. It excludes all repository/PR identity, PA/PN outcome, project history, and final implementation. The Stage C extractor must accept this isolated data type, not a screening row or raw package. `pilot_analysis/conversation/<case_id>/record_<version>.json` is a suitable versioned location for validated conversation-side records; independent validation judgments need their own retained provenance.
The Stage B foundation has three representations: retrieved source archive in the raw provenance layer; lossless normalized conversation under `cases/conversations/<case_id>/`; and a derived Stage C model view there. The restricted case-linkage record belongs under `cases/manifests/` and is never Stage C input. All resolve through the same stable neutral DIR Case ID. The one-case preparation command is implemented. Freeze records only after procedure validation and case-level boundary/processability checks; retain sampled versus unsampled validation status.
The one-case Stage B command uses `cases/manifests/linkage/<case_id>.json`, `cases/raw/<case_id>/conversation_source_archive.json`, and `cases/conversations/<case_id>/{normalized_conversation,stage_c_model_view,package_status}.json`. It writes a completion marker last and refuses existing files. See [`pipeline/extraction/README.md`](../pipeline/extraction/README.md). A cached HTTP response without a recorded retrieval time stays explicitly unknown; cache acquisition and the research source archive remain separate.

Stage B corpus orchestration writes operational `cases/manifests/stage_b_summary.{csv,md}`. Explicit legacy imports retain prior incomplete attempts under `cases/manifests/stage_b_attempts/<case_id>/<checksum>/` before creating the validated package; valid packages are never replaced.

Current Stage C execution reads `cases/conversations/<case_id>/stage_c_model_view_v2.json` and writes `stage_c_extraction_v6.json` beside immutable historical outputs. Version-controlled prompts live under `prompts/stage_c/`; response and final-record schemas live under `schemas/`. Extraction-v6 uses `stage-c-pass2-v2` positional provenance and `conversation-draft-v4` with an independent Pass 2 outcome. Runtime configuration is centralized in `src/developer_intent/stage_c_config.py`; extraction, validation, deterministic family identity, temporal derivation, and the tool-free OpenAI Responses adapter live in `src/developer_intent/stage_c.py`.

The offline Post-Stage-C initializer writes `cases/manifests/post_stage_c_eligibility.csv` and `post_stage_c_reconstruction_pilot.csv`. Future acquisition records live at `cases/reconstruction/<case_id>/historical_state_acquisition_v1.json`; compact component indexes live under `data/derived/historical_information/<case_id>/`. These records are researcher-side processability and provenance artifacts, never Stage C model input.

## Historical information, traces, and evidence

Compact `historical-information-index-v1` records under `data/derived/historical_information/` hold stable historical references, timestamps, the focal-PR base boundary SHA/tree, and separately statused PR/issue/CI/discussion/history identifiers. Large payloads are materialized on demand. `pipeline/snapshot/` resolves historical states without guessing; `pipeline/retrieval/` records justified operations and traces; `pipeline/selection/` assesses temporal validity, relevance, novelty, C/S/V contribution and uncertainty reduction. `pipeline/evidence_engineering/` performs semantic reduction before deferred materialization and payload reduction. Retrieval Algorithm v1 is derived only from discovery cases and frozen before held-out application. Experimental and provenance directories remain available for later runs; no held-out evidence may enter v1 development.

## RAW / SAFE / SEALED

`cases/raw/<case_id>/` is an optional reproducible historical audit package and may contain the final diff or other future information. It is never the conversation-only input and never reconstruction-safe. `safe/reconstruction/<case_id>/` contains information admissible under the frozen `tFG` method; `sealed/evaluation/<case_id>/` holds future/outcome material. The eventual integrated implementation remains sealed until both current-model generation outputs are fixed. Preserve separate `tC` and `tFG` provenance for a possible separately versioned sensitivity analysis.

## Schemas, configuration, and tests

Current Protocol v5 records carry `dir-tfg-v2`. Versioned schemas validate Stage A contracts, restricted linkage, both Stage C model responses, and the final Stage C draft. Earlier `dir-tfg-v1` conversation and repository-evidence schemas remain legacy. `.env.example`, `stage_c_config.py`, and the existing screening configuration keep secrets out of versioned artifacts. Unit tests run without network; later integration and leakage tests verify frozen and held-out boundaries.
