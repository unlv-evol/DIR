# Protocol v5 screening

Stage A starts with all PatchPrompt rows whose `Outcome_Class` is PA or PN. The source CSV is a candidate index, not a complete case source. Screening records integrity, availability, and processability. Size, prompt count, word count, and commit count are descriptive only. `PR_Size` is inherited metadata and unused. See [the protocol](../../protocols/experiment_protocol.md).

Stage A outputs are `cases/manifests/screened_PA_PN_cases.csv`, `eligible_PA_PN_cases.csv`, and `stage_a_summary.md`, marked `dir-screening-v9` / `dir-tfg-v2`. The screened manifest records scientific eligibility and Stage B readiness separately.

The stable 64-column screening CSV and seven-column researcher-only mapping CSV have versioned logical-record contracts in `schemas/`. Validate Stage A artifacts with `python3 pipeline/screening/validate_contracts.py --screened PATH --eligible PATH --mapping PATH`. Stage A manual reviews can also be checked with `--reviews-dir cases/manifests/correspondence_reviews`; Stage A loads them through `--correspondence-review-dir`. The validator does no retrieval and preserves blank versus unresolved semantics. See [schemas/README.md](../../schemas/README.md).

The offline manual-review workflow is:

```bash
python3 pipeline/screening/run.py --export-correspondence-review cases/manifests/stage_a_correspondence_review.csv
# Edit only pr_conversation_match and the six pr_conversation_match_* provenance cells.
python3 pipeline/screening/run.py \
  --evidence-dir data/intermediate/screening/cache/evidence \
  --prepare-correspondence-evidence cases/manifests/correspondence_reviews/stage_a_correspondence_review_original.csv
python3 pipeline/screening/run.py \
  --evidence-dir data/intermediate/screening/cache/evidence \
  --import-correspondence-review cases/manifests/stage_a_correspondence_review_ready.csv
# After archiving any existing final outputs, finalize Stage A from local evidence and canonical reviews:
python3 pipeline/screening/run.py
```

The export includes only stable identities, source-linkage provenance, automated status, and the conservative `identifiers_and_source_linkage_only` policy/reference. After manual review, the preparation command creates minimal packets under `cases/manifests/correspondence_evidence/`, changes the prepared CSV to `direct_share_reference_and_restricted_task_context_v1`, and binds both evidence-reference cells to the packet checksum. Packet support remains explicitly `archive_exact_pair`, `archive_conflicting_reference`, or `reviewer_attestation_only`. Packets omit PA/PN, assistant answers, diffs, implementations, merge/adoption outcomes, and unrelated project content. They are Stage A administrative inputs only. Blank judgment cells are skipped and remain unresolved. Completed rows become canonical JSON under `cases/manifests/correspondence_reviews/`; importing identical completed rows again is idempotent, while a conflicting existing JSON record fails closed.

The v9 CSV retains only `conversation_turn_pattern` from the former pilot secondary characteristics, as descriptive metadata computed from the complete developer-turn count. It does not persist lexical prompt signals, help-seeking cue lists, unassessed qualitative placeholders, or lexical-producer provenance. These old v6 values must not be passed to Stage G; Stage G derives cues afresh from frozen, permitted inputs after validation, freeze, and splitting.

The run also derives restricted `cases/manifests/case_mapping.csv` from the source index and screened rows. It is the researcher-only Protocol v5 mapping, not a Stage C input; the per-case linkage JSON remains separate. `--limit N` writes a separate `smoke_N_case_mapping.csv` under `data/intermediate/screening/`. All mapping outputs refuse overwrite.

## Safe local checks

Python 3.9.6 or newer is required. `.env` is ignored by Git. `GITHUB_TOKEN` remains optional for public GitHub API access; the configuration check never prints its value.

```bash
python3 pipeline/screening/run.py --check-config
make test
```

For an authorized future v5 run, `--live` retrieves sources into `data/intermediate/screening/cache/current/`; `--limit N` uses separate `screening/smoke_N*` paths. The CLI protects existing outputs and reserved paths against live writes. Overrides include `--source`, `--output`, `--eligible-output`, `--summary`, `--case-mapping-output`, `--cache-dir`, `--evidence-dir`, `--correspondence-review-dir`, `--export-correspondence-review`, `--import-correspondence-review`, `--correspondence-evidence-policy`, `--timeout`, `--retries`, `--archive`, `--no-archive-fallback`, and `--refresh`. Environment defaults use `DIR_V5_SCREENING_CACHE_DIR` and `DIR_V5_SCREENING_OUTPUT`.
An existing v5 manifest or summary also blocks a new run before retrieval; archive it explicitly before a rerun. The HTTP cache can still support acquisition without replacing a research output.

Stable DIR IDs derive from source `Case ID` without encoding outcome or role. Verified GitHub redirects preserve source and canonical PR URLs. Retrieval and parsing failures stay explicit. Archive fallback requires matching PR and conversation identities; summary-only archive records do not establish completeness. Date-only values stay date-only. Source bodies and parsed evidence are intermediate audit material, not supplied-C/S/V input.

Positive processability judgments require `processability.source` in case evidence JSON. Unreviewed first-generation boundary, project-history access, or historical-state reconstructibility stays pending. Full evidence discovery occurs after conversation freeze and the discovery/held-out split. Stage A records administrative source linkage separately from manual semantic correspondence.

Stage A stores one restricted `cases/manifests/correspondence_reviews/<case_id>.json` record for each candidate/processable case reaching manual screening. Required keys are `case_id`, `pr_url`, `conversation_url`, `judgment` (`yes`, `no`, or `unresolved`), `source`, `reviewer`, `timestamp`, `version`, `evidence_ref`, and `rationale`. PA/PN, final diffs, integrated implementations, adoption, downstream evaluation, and Stage G evidence are excluded from the review packet. PatchPrompt/PatchTrack association is provenance but does not automatically prove semantic correspondence.
The screened manifest and summary count `eligible`/`excluded`/`pending_resolution` independently from operational readiness. `ready_for_stage_b` requires all packaging prerequisites and permits a pending row only when its sole unresolved reasons are preliminary boundary identifiability and `tFG`-dependent historical-state reconstructibility. Correspondence unresolved/no, incomplete conversation, unresolved linkage, duplicates, unresolved Git access, temporal-anchor problems, integrity failures, and exclusions block Stage B.
