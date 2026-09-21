# Protocol v5 Stage B preparation

This command prepares **one explicitly selected technical test case** from the PA/PN source index. It does not determine Protocol v5 eligibility, inspect GitHub, derive `tFG`, run C/S/V extraction, or assign a study role. Use a neutral DIR `case_id` from the candidate/screening index; the command verifies that it maps to exactly one PA/PN source row.

Safe configuration check (no network or research writes):

```bash
python3 pipeline/extraction/run.py --check-config
```

After authorizing a one-case Stage B smoke run:

```bash
python3 pipeline/extraction/run.py --case-id CASE_XXXXXXXXXXXX --live
```

Replace `CASE_XXXXXXXXXXXX` with the chosen stable neutral DIR Case ID. The command fails before retrieval if any destination already exists. It uses the existing ChatGPT share retriever and the separate Protocol v5 HTTP cache, with no ChatGPT credentials. `--refresh` refreshes HTTP acquisition only; it never overwrites a Stage B package. An old cached response without an original retrieval timestamp is marked `unknown_legacy_cache`, not assigned a new time.

Outputs are separate and keyed by the same neutral ID:

```text
cases/manifests/linkage_v5/<case_id>.json                 # restricted PR/source identity
cases/raw/<case_id>/conversation_source_archive.json     # exact retrieved source bytes, base64
cases/conversations/<case_id>/normalized_conversation.json
cases/conversations/<case_id>/stage_c_model_view.json
cases/conversations/<case_id>/package_status.json
```

Inspect `package_status.json` first. `complete` is written last, only after checksum, ordering, provenance, and model-view isolation checks pass. Retrieval/normalization failures retain only available diagnostic outputs and a non-complete status. An absent status file indicates interrupted persistence. Source archive and normalized conversation are not reconstruction-safe. The linkage file must never be passed to Stage C. Generated files are ignored by Git by default; review them before any data-management decision.
