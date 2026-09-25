# AGENTS.md — Developer Intent Reconstruction

This research repository requires both software correctness and methodological validity. **The revised Word Protocol v5 (`Developer_Intent_Reconstruction_Experiment_Protocol_v5 (2).docx`) is authoritative** for the current experiment. Read the revised Word protocol when accessible, `protocols/experiment_protocol.md`, `docs/architecture.md`, `docs/repository_structure.md`, `docs/research_questions.md`, `docs/data_dictionary.md`, `decisions/decision_log.md`, relevant schemas/configuration/tests, and this file before changing a pipeline stage. Surface conflicts instead of silently choosing an interpretation.

Write Stage A intermediate outputs under `data/intermediate/screening/` and distinguish methodologies with record/schema versions. Preserve acquired source material and retrieval provenance. Never commit real `.env` secrets or emit tokens into logs, CSVs, or caches.

## Current stage order

```text
PA/PN candidate corpus
  -> integrity / availability / processability screening
  -> automated/administrative and manual correspondence screening within Stage A
  -> scientifically eligible PA/PN cases
  -> isolated conversation-only packaging
  -> first-generation + supplied-C/S/V extraction
  -> independent human validation (~30% PA/PN-stratified sample)
  -> confirmed eligible, resolved-case gate and versioned conversation-side freeze
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

Screen the complete PA/PN candidate corpus. Do not exclude otherwise valid cases because of changed files/lines, prompt count, conversation words, PR size, or commits. These measures can be descriptive. PA/PN defines the source population and later split strata; it is not a retrieval cue or success signal before evaluation. Pending or unverified source facts remain pending, not silently repaired or treated as negative evidence.
Source linkage and semantic task correspondence are distinct Stage A criteria. Stage A records administrative linkage and performs restricted, identity-bound manual correspondence screening for all candidate/processable cases. Correspondence `yes` may satisfy the criterion, `no` excludes, and `unresolved` remains pending; PA/PN and outcome information cannot influence the judgment. Use `cases/manifests/stage_a_correspondence_review.csv` only as the restricted Stage A human interface. Canonical review records remain `cases/manifests/correspondence_reviews/<case_id>.json`. The conservative review export contains identifiers and source-linkage provenance only; do not add mutable PR text until its temporal policy is resolved. PR API retrieval alone does not establish Git history accessibility; a separate non-substantive commit-object probe may do so, while historical reconstructibility remains `tFG`-relative.
Stage B readiness is operational metadata, not a competing scientific status. Production Stage B accepts only scientifically eligible cases. A complete package does not establish freeze readiness. Stage A boundary identifiability is preliminary; Stage C authoritatively identifies the first family, artifact, response, target prompt, and `tFG`. The researcher-only case mapping and per-case linkage stay outside the conversation package. Before freeze, PR/repository access is limited to administrative integrity, mapping, accessibility, and processability checks; substantive project evidence enters only after freeze.
Stage A `conversation_turn_pattern` is descriptive. Do not pass lexical characteristics from complete Stage A conversations to Stage G or use them to precondition retrieval. Stage G derives cues from frozen permitted inputs after the split.

## Isolation and temporal rules

Stage C receives only neutral ID, temporal source, complete conversation, and stable turn/artifact provenance. It must not receive PR/repository identity, PA/PN, project history, final diff, or eventual implementation. Extract supplied Context/Specificity/Verification solely from the target developer prompt and permitted earlier turns. Exclude the first artifact-bearing assistant response and all later turns. Freeze the validated conversation account before project-evidence analysis; subsequent repository findings cannot rewrite it without a new record version.
Stage D assesses only the extraction procedure on an approximately 30% PA/PN-stratified sample. Stage A owns correspondence screening. Track procedure validation, individual extraction validation, extraction completion, and boundary/processability status separately. A frozen v5 record can be unsampled for extraction validation if Stage A eligibility is confirmed, the validated procedure completed successfully, and its boundary and checks are resolved; do not call it individually extraction validated. Unresolved records cannot enter the discovery/held-out split. Keep the restricted PR/case-linkage record separate from the retrieved source archive, lossless normalized conversation, and Stage C model view. All use the same neutral DIR Case ID; PR identity never enters the model view.

Preserve `tC` (first developer prompt) and `tFG` (immediately before the first generated artifact response in the first snippet family) independently with value, precision, status, and source. Current `primary_repository_cutoff = tFG`; never infer `tFG = tC`, fabricate a time from a date, or guess a repository snapshot. Preserve `available_by_tC` and `available_by_tFG` separately where determinable. Current first-generation methodology is `dir-tfg-v2`.

`cases/raw/` is historical audit material and may expose the future; `cases/conversations/` is isolated conversation-only input; `safe/reconstruction/` contains only admitted information; `sealed/evaluation/` holds future/outcome material. Integrated implementation stays sealed until both controlled current-model outputs are fixed. Held-out project evidence must not shape Retrieval Algorithm v1. Historical availability is not successful retrieval, relevance, or additional evidence. Every retained evidence item needs a justified retrieval trace, temporal check, task relevance, novelty beyond frozen conversation, and C/S/V contribution. A no-additional-evidence result is valid. Evidence Engineering follows frozen retrieval and separates semantic reduction from payload reduction.

## Implementation discipline

Keep the source CSV unchanged. Preserve useful existing retrieval, parsing, caching, configuration, and stable-ID code while versioning changed outputs. Screening may use processability evidence but must not perform full retrieval-method discovery. Historical project indexes use stable references and deferred payload materialization, not indiscriminate copies of trees, diffs, or logs. Do not create speculative schemas or invent methodological thresholds. Keep normal unit tests offline. Check documented producer/consumer contracts and report unresolved methodology rather than coding an unsupported assumption.
