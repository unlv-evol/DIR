# AGENTS.md — Developer Intent Reconstruction

This research repository requires both software correctness and methodological validity. **The Word Protocol v5 is authoritative** for the current experiment. Read `Developer_Intent_Reconstruction_Experiment_Protocol_v5.docx` when accessible, `protocols/pilot_case_selection_and_extraction.md`, `docs/architecture.md`, `docs/repository_structure.md`, `docs/research_questions.md`, `docs/data_dictionary.md`, `decisions/decision_log.md`, relevant schemas/configuration/tests, and this file before changing a pipeline stage. Surface conflicts instead of silently choosing an interpretation.

Existing `dir-screening-v3` manifests, old smoke runs/cache, and the approximately-30-case `pilot_cases.csv` are legacy/provisional outputs. Preserve them and their provenance. Do not rerun, overwrite, or treat them as Protocol v5 eligibility, validation, discovery, or held-out assignments. Use separately versioned paths for future v5 execution. Never commit real `.env` secrets or emit tokens into logs, CSVs, or caches.

## Current stage order

```text
PA/PN candidate corpus
  -> integrity / availability / processability screening
  -> eligible PA/PN corpus
  -> isolated conversation-only packaging
  -> first-generation + supplied-C/S/V extraction
  -> independent human validation (~30% PA/PN-stratified sample)
  -> versioned conversation-side freeze
  -> reproducible PA/PN-stratified discovery / held-out split (~70/30)
  -> H_i(tFG) historical information indexes
  -> discovery-only evidence-pattern traces
  -> derive and FREEZE Retrieval Algorithm v1
  -> frozen retrieval on held-out cases
  -> Retrieved Evidence Index / Evidence Engineering
  -> intent reconstruction
  -> same-current-model original/reconstructed generation
  -> fix both outputs, reveal integrated implementation, evaluate
```

Do not select a primary approximately-30-case development corpus or exclude otherwise valid cases because of changed files/lines, prompt count, conversation words, PR size, or commits. These measures can be descriptive. PA/PN defines the source population and later split strata; it is not a retrieval cue or success signal before evaluation. Pending or unverified source facts remain pending, not silently repaired or treated as negative evidence.

## Isolation and temporal rules

Stage C receives only neutral ID, temporal source, complete conversation, and stable turn/artifact provenance. It must not receive PR/repository identity, PA/PN, project history, final diff, or eventual implementation. Extract supplied Context/Specificity/Verification solely from the target developer prompt and permitted earlier turns. Exclude the first artifact-bearing assistant response and all later turns. Freeze the validated conversation account before project-evidence analysis; subsequent repository findings cannot rewrite it without a new record version.
Human validation assesses the extraction procedure on an approximately 30% PA/PN-stratified sample. Track procedure validation, individual human validation, extraction completion, and boundary/processability status separately. A frozen v5 record can be unsampled if the validated procedure completed successfully and its boundary and checks are resolved; do not call it individually human validated. Unresolved records cannot enter the discovery/held-out split. Keep the restricted PR/case-linkage record separate from the retrieved source archive, lossless normalized conversation, and Stage C model view. All use the same neutral DIR Case ID; PR identity never enters the model view.

Preserve `tC` (first developer prompt) and `tFG` (immediately before the first generated artifact response in the first snippet family) independently with value, precision, status, and source. Current `primary_repository_cutoff = tFG`; never infer `tFG = tC`, fabricate a time from a date, or guess a repository snapshot. Preserve `available_by_tC` and `available_by_tFG` separately where determinable. Current v5 first-generation methodology is `dir-tfg-v2`; older primary-`tC` and `dir-tfg-v1` artifacts remain distinct.

`cases/raw/` is historical audit material and may expose the future; `cases/conversations/` is isolated conversation-only input; `safe/reconstruction/` contains only admitted information; `sealed/evaluation/` holds future/outcome material. Integrated implementation stays sealed until both controlled current-model outputs are fixed. Held-out project evidence must not shape Retrieval Algorithm v1. Historical availability is not successful retrieval, relevance, or additional evidence. Every retained evidence item needs a justified retrieval trace, temporal check, task relevance, novelty beyond frozen conversation, and C/S/V contribution. A no-additional-evidence result is valid. Evidence Engineering follows frozen retrieval and separates semantic reduction from payload reduction.

## Implementation discipline

Keep the source CSV unchanged. Preserve useful existing retrieval, parsing, caching, configuration, and stable-ID code while versioning changed outputs. Screening may use processability evidence but must not perform full retrieval-method discovery. Historical project indexes use stable references and deferred payload materialization, not indiscriminate copies of trees, diffs, or logs. Do not create speculative schemas or invent methodological thresholds. Keep normal unit tests offline. Check documented producer/consumer contracts and report unresolved methodology rather than coding an unsupported assumption.
