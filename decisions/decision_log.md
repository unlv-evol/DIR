# Decision Log

Record important research and engineering decisions.

- **2026-09-29 — Restore independent Stage B readiness under primary `tFG`.**
  - **Decision:** Preserve `tC` and `tFG` independently under unchanged methodology `dir-tfg-v2`; `tFG` remains the primary repository cutoff and historical information is `H_i(tFG)`. Keep `dir-screening-v9`, but restore the DIR-009 distinction between scientific disposition and operational packaging readiness. A pending case may be `ready_for_stage_b` only when established linkage, correspondence `yes`, complete conversation, temporal anchor, uniqueness, Git history access, and integrity pass, and its only pending reasons are preliminary first-generation boundary identifiability and `tFG`-dependent historical-state reconstructibility. Stage B validates this allowlist and preserves pending status. Correspondence unresolved/no, arbitrary pending reasons, exclusions, and other prepackaging failures block Stage B.
  - **Rationale:** Stage C requires a Stage B conversation package to identify the first-generation boundary and `tFG`; requiring those dependent judgments before packaging created a circular dependency.
  - **Impact:** No schema or methodology version changes. The strict resolved-case gate remains immediately before Stage E freeze and downstream split: eligibility, extraction, authoritative boundary, deferred processability, procedure validation, and applicable case checks must be resolved there. `AGENTS.md` now agrees with the current primary-`tFG` policy while retaining `tC` for provenance and separately versioned sensitivity analysis.
  - **Owner:** Study team. **Status:** Adopted.

- **2026-09-22 — Add a restricted Stage A correspondence CSV interface.**
  - **Decision:** Export applicable unresolved cases to `cases/manifests/stage_a_correspondence_review.csv`, allow manual editing of the controlled judgment and six provenance fields, and import completed rows into canonical `dir-correspondence-review-v1` JSON. Use the conservative `identifiers_and_source_linkage_only` evidence policy until temporal PR title/body rules are resolved. Blank judgments remain unresolved. This is an operational interface inside the single Stage A and does not change `dir-screening-v9` or `dir-tfg-v2`.
  - **Rationale:** A deterministic CSV supports practical review while canonical identity-bound JSON preserves validation, auditability, and pipeline consumption.

- **2026-09-22 — Restore semantic correspondence to Stage A.**
  - **Decision:** Reverse the temporary assignment of semantic PR-conversation correspondence to Stage D. One Stage A now contains automated/administrative screening and restricted manual correspondence screening for 100% of candidate/processable cases reaching that activity. Correspondence `yes` may satisfy the criterion, `no` excludes, and `unresolved` remains pending. Stage D returns to approximately 30% PA/PN-stratified validation of Stage C conversation extraction. Use `dir-screening-v9` with unchanged `dir-tfg-v2`; retain `dir-correspondence-review-v1` under `cases/manifests/correspondence_reviews/`. The former statement that production Stage B accepts only scientifically eligible cases is superseded by the 2026-09-29 progression correction below; unresolved correspondence still blocks Stage B.
  - **Rationale:** PR-conversation correspondence is a corpus/case-validity criterion, whereas Stage D validates the extraction procedure. Source linkage remains distinct from semantic correspondence.

- **2026-09-22 — Stage D owns semantic PR/conversation correspondence (superseded by the decision above).**
  - **Decision:** Version the Stage A screening contract as `dir-screening-v8` under unchanged methodology `dir-tfg-v2`. Stage A records administrative source linkage as established, conflicting, or unresolved and persists semantic correspondence as `pending_manual_validation`; that intentional deferral does not itself create a Stage A pending reason. Reuse `dir-correspondence-review-v1` unchanged in `annotations/correspondence_reviews/` for a restricted Stage D review of every candidate intended for Stage E. Stage E requires `yes`; `no` excludes and `unresolved` remains outside freeze. The approximately 30% extraction-validation sample remains a separate validation scope.
  - **Rationale:** Source association and semantic task correspondence are distinct. Deferring the human judgment avoids a separate Stage A review workflow while preserving a testable all-case integrity gate before freeze.

Suggested fields:

- Date
- Decision ID
- Decision
- Alternatives considered
- Rationale
- Evidence
- Impact
- Owner
- Status

## 2026-09-19 — Pilot extraction before method freeze

- **Decision ID:** DIR-001
- **Decision:** Extract approximately 30 pilot/development cases and use
  them to develop and validate the methodology before freezing and
  versioning it for held-out evaluation. Additional raw extraction may
  occur earlier only when mechanical; held-out evaluation cases do not
  develop, tune, or revise methodology.
- **Alternatives considered:** Reading the earlier architecture diagram
  as requiring method freeze before all raw extraction.
- **Rationale/evidence:** Pilot development requires extracted historical
  cases; see the pilot protocol, §11.
- **Impact:** Architecture and lineage diagrams must show pilot
  extraction before method freeze.
- **Owner:** Study team. **Status:** SUPERSEDED by DIR-006.

## 2026-09-19 — Candidate index and source boundaries

- **Decision ID:** DIR-002
- **Decision:** Use the existing PatchPrompt-study analysis CSV as the
  candidate-case index and metadata source for planned PA and PN case
  derivation, including its PR and conversation links and C/S/V scores.
  PA and PN establish the generated-code source population; their
  adoption distinction does not rank, prioritize, or balance pilot
  selection. See the pilot protocol for the source-class definitions.
  Obtain full raw-case material from original sources or record it as
  unavailable. Do not infer undocumented column meanings.
- **Alternatives considered:** Treating the CSV as a complete raw-case
  source.
- **Rationale/evidence:** The CSV supplies indexing and analysis fields;
  the pilot protocol requires additional historical material. The
  PatchPrompt study defines both PA and PN as containing generated code
  snippets (Sserunjogi, Ogenrwot, and Businge, arXiv:2606.19644,
  2026).
- **Impact:** DIR screening derives its required measures from the
  documented PR and conversation sources. Inherited `PR_Size` metadata
  is not used by the current pilot screening procedure.
- **Owner:** Study team. **Status:** Retained source-boundary decision; pilot-selection portion SUPERSEDED by DIR-006.

## 2026-09-19 — Commit-count preference

- **Decision ID:** DIR-003
- **Decision:** Record the observed PR commit count. `<= 10` commits is
  preferred, not a hard eligibility threshold; exceeding it alone does
  not exclude a case that meets the hard requirements.
- **Alternatives considered:** Rejecting every case with more than 10
  commits.
- **Rationale/evidence:** The pilot protocol, §2.1, says “preferably.”
- **Impact:** Screening must distinguish this preference from hard
  limits.
- **Owner:** Study team. **Status:** SUPERSEDED by DIR-006.

## 2026-09-19 — Date precision and repository state

- **Decision ID:** DIR-004
- **Decision:** Preserve whether conversation start is known as a date
  or a timestamp. Do not invent a time or claim an exact repository
  state from a date alone. Record repository-state resolution as
  `exact`, `derivable`, `unresolved`, or `unavailable` according to
  supporting evidence.
- **Alternatives considered:** Assigning a default time to date-only
  records or assuming the PR base SHA is the conversation-start state.
- **Rationale/evidence:** The pilot protocol, §5.10, prohibits guessing
  repository state.
- **Impact:** Temporal metadata must retain source precision and
  uncertainty.
- **Owner:** Study team. **Status:** Temporal-precision rule retained; pilot-specific framing SUPERSEDED by DIR-006.

## 2026-09-19 — Versioned first-generation primary cutoff

- **Decision ID:** DIR-005
- **Decision:** For the current first-generation experiment, preserve
  conversation-start `tC` and first-generation `tFG` independently;
  `primary_repository_cutoff = tFG`. A validated, frozen
  conversation-side supplied-C/S/V record precedes repository forensics.
  The former primary-`tC` procedure and current `dir-tfg-v1` derived
  records are methodologically distinct. Never fill an unresolved
  `tFG` with `tC`.
- **Alternatives considered:** Continuing to use `tC` as primary or
  silently substituting it when `tFG` is unavailable.
- **Rationale/evidence:** Revised pilot protocol, §§9 and 12; explicit
  first-generation reconstruction design. `tC` remains available for
  sensitivity analysis or a separately versioned future method.
- **Impact:** Derived conversation and repository evidence contracts
  carry both temporal judgments and a methodology version. Screening
  retains historical `tC`; first-generation fields are derived only
  after raw artifact preservation.
- **Owner:** Study team. **Status:** Primary-`tFG` rule retained under DIR-006; pilot-specific framing SUPERSEDED.

## 2026-09-21 — Protocol v5 migration supersedes the pilot design

- **Decision ID:** DIR-006
- **Decision:** Protocol v5 supersedes the approximately-30-case primary
  development pilot and its manageability-based screening. Screen all PA/PN
  candidates for integrity, availability, temporal and first-generation
  processability, and historical project accessibility. Size, prompt,
  conversation-length, and commit measures remain descriptive and never
  exclude by magnitude alone. Package conversations without project/outcome
  metadata; extract supplied C/S/V; independently validate an approximately
  30% PA/PN-stratified sample; freeze/version conversation-side records;
  then make an approximately 70/30 PA/PN-stratified discovery/held-out split.
  Build historical information at `tFG`, derive and freeze Retrieval Algorithm
  v1 from discovery traces, and evaluate on held-out cases. Preserve `tC`
  independently and keep `tFG` primary, without fallback. Use reproducible
  historical indexes/references and defer large payload materialization.
- **Alternatives considered:** Continue the earlier 30-case selection and
  eager raw-extraction workflow.
- **Rationale/evidence:** Adopted Protocol v5 instructions; see the current
  operational protocol and architecture.
- **Impact:** DIR-001 and DIR-003 describe the superseded pilot design,
  not current eligibility or stage order. Existing `dir-screening-v3`
  manifests, smoke runs, and `pilot_cases.csv` are legacy/provisional,
  recoverable from Git history; ignored caches remain local. Current screening is
  `dir-screening-v4` under `dir-tfg-v2` at separate output paths; prior
  `dir-tfg-v1` derived schemas remain legacy. Held-out evidence cannot
  shape Algorithm v1; integrated implementation remains SEALED until
  both current-model outputs are fixed.
- **Owner:** Study team. **Status:** Adopted.

## 2026-09-21 — Retire the superseded pilot workflow from the active tree

- **Decision ID:** DIR-008
- **Decision:** Rename the operational Markdown to `protocols/experiment_protocol.md` (formerly `protocols/pilot_case_selection_and_extraction.md`). Remove tracked approximately-30-case selection manifests, smoke outputs, selection-only code/tests, and empty placeholders from the active tree. Git history retains those tracked artifacts; preserve ignored retrieval caches and unique external data locally. Keep prior derived schemas as explicit legacy contracts.
- **Rationale/evidence:** DIR-006 and the Protocol v5 Stage A–L workflow supersede manageability selection. Current Stage A and Stage B resolve neutral IDs from the authoritative source dataset and do not import the pilot-selection utility.
- **Impact:** Current outputs use versioned v5 paths. Historical judgments must not be reused as v5 eligibility. Retrieval caches and local one-case technical outputs remain outside Git and must not be assumed recoverable from Git history.
- **Owner:** Study team. **Status:** Adopted for repository cleanup.

## 2026-09-21 — Authoritative Word Protocol v5 conformance

- **Decision ID:** DIR-007
- **Decision:** Human validation assesses the conversation extraction procedure
  on an approximately 30% PA/PN-stratified sample. Freeze a case record after
  that procedure is validated and its extraction, first-generation boundary,
  and structural/processability checks are resolved. Preserve whether the case
  was individually sampled/validated, adjudicated, or not sampled; frozen does
  not imply individual human validation. Exclude unresolved or affected cases
  from a downstream discovery/held-out split until resolved.
- **Rationale/evidence:** Authoritative Word Protocol v5, §§5–7, and the
  user's conformance clarification. Systematic extraction defects require a
  versioned procedure revision, affected-population identification,
  regeneration of affected outputs, and revalidation as needed.
- **Historical interpretation (SUPERSEDED by DIR-010):** The earlier Word version referred to packaging PR identity through the complete case/linkage record. The revised Word protocol explicitly limits the Stage B conversation package to neutral Case ID, conversation date/time, and complete conversation. The Stage C model view
  remains conversation-only under §3. The same neutral DIR Case ID links the
  restricted record, retrieved source archive, lossless normalized
  conversation, and model view. Preservation in normalized/source layers
  does not make a turn admissible for supplied-C/S/V extraction.
- **Impact:** No real outputs or v1 schemas are rewritten. Current v5 freeze
  code distinguishes procedure and case statuses; the real split remains
  uncreated.
- **Owner:** Study team. **Status:** Adopted; clarified by study team.

## 2026-09-21 — Separate Stage B readiness from scientific eligibility

- **Decision ID:** DIR-009
- **Decision:** Retain Stage A `eligible` / `excluded` / `pending_resolution` judgments and add independently versioned `ready_for_stage_b` / `blocked` progression. An unresolved Stage C first-generation boundary or `tFG`-dependent historical-state judgment does not by itself block conversation packaging. A demonstrated required failure can block and exclude. Stage B completion does not promote eligibility; Stage E/F still require confirmed eligibility and resolved extraction, boundary, validation, and processability checks.
- **Rationale/evidence:** Protocol v5 assigns first-generation identification to Stage C using the Stage B package. The one-case smoke yielded a complete package while scientific eligibility remained pending.
- **Impact:** Stage A CSV contract advances to `dir-screening-v5`; earlier `dir-screening-v4` smoke outputs remain unchanged prior-version records. Restricted Stage B linkage/status may carry the pending Stage A judgment, while the Stage C model view does not.
- **Owner:** Study team. **Status:** Adopted as an operational clarification.

## 2026-09-21 — Revised Word Protocol v5 conversation-side alignment

- **Decision ID:** DIR-010
- **Decision:** Treat `Developer_Intent_Reconstruction_Experiment_Protocol_v5 (2).docx` as authoritative. Stage A boundary identifiability is a preliminary processability determination; Stage C authoritatively identifies the first family/artifact/response/target prompt and `tFG`. Keep scientific eligibility separate from Stage B readiness, with a strict resolved-case gate before freeze and split. Limit pre-freeze PR/repository access to administrative integrity, mapping, accessibility, duplicate, and processability checks; substantive evidence inspection begins after freeze. Keep `tC` alongside primary `tFG`. Generate researcher-only `case_mapping.csv` deterministically alongside richer restricted per-case linkage; neither enters Stage C.
- **Rationale/evidence:** Revised Word Protocol v5 §§2–3, 8.4, 15–16 clarifies the conversation-only package, immediate mapping deliverable, and core additional-evidence criteria.
- **Impact:** Operational documentation clarifies protocol-required versus complementary fields. Source archives, normalized records, model views, retrieval/provenance statuses, and historical schemas remain intact. The former DIR-007 interpretation of PR identity as part of the complete Stage B package is superseded; administrative linkage remains outside that package.
- **Owner:** Study team. **Status:** Adopted.

## 2026-09-21 — Source-bound Stage A correspondence and history access

- **Decision:** Version the Stage A CSV contract as `dir-screening-v6` while retaining `dir-tfg-v2`. Treat the inherited PR/share pairing and archived grouping as linkage leads rather than independent proof of task correspondence. Require a source- and identity-bound administrative review for `pr_conversation_match`; list unresolved cases for researcher review. Separately probe Git commit-object access using a known PR base SHA without inspecting project content. A successful PR API request cannot establish Git history accessibility, and Git access cannot establish historical reconstructibility at `tFG`.
- **Impact:** Preserve separate scientific eligibility and Stage B readiness. Positive and negative judgments gain auditable sources and can affect existing pending/exclusion decisions; inconclusive results stay pending. Restricted review records remain outside Stage C input.

## 2026-09-21 — Remove pilot lexical fields from Stage A v7

- **Decision:** Version the Stage A CSV contract as `dir-screening-v7` while keeping methodology `dir-tfg-v2`. Retain only `conversation_turn_pattern` as descriptive metadata from the former pilot secondary-characteristics fields. Retire the complete-conversation lexical signals, cue lists, unassessed placeholders, and lexical-producer provenance from current Stage A outputs.
- **Rationale/evidence:** Revised Word Protocol v5 §§2–3 and 8.1 assign Stage A to screening, first-generation identification to Stage C, and retrieval-cue derivation to Stage G from frozen permitted inputs. Full-conversation lexical screening could include turns after the target prompt.
- **Impact:** Historical v6 outputs remain historical. Stage A eligibility and Stage B readiness rules are unchanged; no v6 lexical field is migrated into Stage G.

## 2026-09-29 — Restricted Stage A correspondence evidence packets

- **Decision:** Record semantic PR/conversation review support in checksum-bound `dir-correspondence-evidence-v1` packets using policy `direct_share_reference_and_restricted_task_context_v1`. Packets contain only identity-bound share references, minimal developer-authored task context, archive provenance where available, and reviewer observation. Preserve `archive_exact_pair`, `archive_conflicting_reference`, and `reviewer_attestation_only` as distinct support states.
- **Rationale/evidence:** Completed manual rationales relied on direct PR share references and task context, which was broader than the earlier `identifiers_and_source_linkage_only` label. The record must describe the evidence actually reviewed without importing raw mixed PatchTrack records into later stages.
- **Impact:** Prepared review CSV rows reference packet paths and SHA-256 checksums. Import fails on missing, changed, or identity-mismatched packets. Packets exclude PA/PN, outcomes, final diffs, integrated implementations, and assistant-generated solutions. They are Stage A administrative material only and cannot enter Stage B/C, Stage G, SAFE inputs, or reconstruction evidence without a separate temporal and admissibility determination.
- **Owner:** Study team. **Status:** Adopted for the completed Stage A correspondence review.

## 2026-09-29 — Versioned correction of a demonstrated conversation-link error

- **Decision:** Correct the inherited conversation linkage for `CASE_B0A21EE800C0` through a verified `dir-source-linkage-correction-v1` overlay while preserving the PatchPrompt CSV, stable case ID, original `review-v1 = no`, and original evidence packet. The corrected conversation is `8cb16814-2855-4fbd-87e5-bde8ba349728`; reacquire it from the preserved PatchTrack archive and issue an identity-bound `review-v2`.
- **Rationale/evidence:** The PR comment directly references the corrected share, while the inherited candidate points to a different share. The study team independently verified the corrected URL and authorized the correction.
- **Impact:** Current Stage A and Stage B source resolution apply verified overlays. Correction history remains auditable; no inherited source data is overwritten, and the correction does not itself satisfy unrelated eligibility criteria.
- **Owner:** Study team. **Status:** Adopted.

## 2026-09-29 — Version Stage B authorization traceability

- **Decision:** Version the restricted Stage B linkage as `case-linkage-v2`.
  Preserve the Stage A canonical PR URL, reference the exact authorizing Stage A
  manifest row and canonical correspondence-review JSON, and snapshot only
  `source_linkage_status = established` and `pr_conversation_match = yes`.
  Keep review rationale and evidence owned by Stage A and outside Stage C input.
- **Rationale/evidence:** The one-case Stage B smoke showed that v1 dropped the
  canonical PR URL and did not make the already-enforced Stage A authorization
  traceable from the package's restricted linkage record.
- **Impact:** This is a restricted provenance-contract change only. It does not
  change eligibility, readiness, correspondence judgments, temporal policy, or
  the conversation-only Stage C view.
- **Owner:** Study team. **Status:** Adopted as an engineering correction.

## 2026-09-30 — Two-pass production Stage C contract

- **Decision:** Implement Stage C as two independent, tool-free OpenAI Responses
  API calls using one environment-configured research model. Pass 1 receives the
  complete isolated Stage B view and selects the first family, artifact-bearing
  response, triggering prompt, and boundary. Deterministic code validates those
  references, derives `tFG`, and constructs Pass 2 input from all and only turns
  strictly before the boundary. Pass 2 extracts textual C/S/V with turn, role,
  and evidence provenance. Use `conversation-draft-v2` and
  `conversation-extraction-v2` under unchanged `dir-tfg-v2`.
- **Decision:** Place the unlettered Post-Stage-C processability/eligibility
  workflow before Stage D. It resolves boundary identifiability, evaluates
  `H_i(tFG)`, resolves historical reconstructibility, and determines final
  eligibility. Stage C never updates eligibility.
- **Rationale/evidence:** The authoritative production Stage C instruction and
  Protocol v5 require a structural hindsight barrier and independent temporal
  provenance. C/S/V are information categories, not PatchPrompt scores.
- **Impact:** Prompts and schemas are version-controlled; runtime configuration
  is externalized; model tools are disabled; Stage D samples only the resolved
  scientifically eligible corpus. Repository acquisition remains unimplemented.
- **Owner:** Study team. **Status:** Adopted for implementation; live smoke pending review.

## 2026-09-30 — Deterministic Stage C first-family identity

- **Decision:** Version Pass 1 as `dir-stage-c-first-generation-v2` and the final draft/extraction contracts as `conversation-draft-v3` / `conversation-extraction-v3`. The model supplies the semantic selection and descriptive `family_label`; deterministic code derives `family_id` as `FGF_` plus 24 lowercase hexadecimal characters from SHA-256 over compact, key-sorted UTF-8 JSON containing the case ID and canonically ordered selected artifact IDs. Canonical order is response event, order within response, then artifact ID. The case ID is included so identifiers remain globally unique outside a case record.
- **Impact:** Model wording, rationale, execution time, and randomness cannot change family identity. Existing v2 development results are retained unchanged and may produce separate v3 records through an offline deterministic migration that preserves the original record hash, model family value, and model provenance. Pass 2 and all substantive Stage C, C/S/V, boundary, and temporal rules are unchanged.
- **Observation:** Wave 1 classified the admissible assistant recommendation that custom errors should extend native `Error` as Verification. This is defensible under the current definition and will be examined across later pilot cases; no prompt or classification rule changes now.
- **Owner:** Study team. **Status:** Adopted before development Wave 2.

## 2026-09-30 — Explicit offline legacy raw-source import for Stage B

- **Decision:** Admit preserved legacy public ChatGPT responses only through an explicit offline Stage B import. Require paired raw body and metadata, canonical-key and conversation-identity agreement, public/HTTP-200 status, current-parser completeness, and normal package validation. Record imported archives as `chatgpt-source-v2` with `source_origin = legacy_cache_import`, raw hashes and paths, null retrieval time, `unknown_legacy_cache`, and a separate import timestamp. Derived evidence and parsed-cache objects cannot replace raw bytes.
- **Decision:** Provide resumable offline orchestration for all Stage-A-ready cases and an operational `stage-b-summary-v1` report. Preserve existing valid packages; retain replaced incomplete attempts by checksum. Stage B readiness for Stage C remains operational and does not change scientific eligibility.
- **Impact:** Stage C contracts, model configuration, C/S/V definitions, `dir-tfg-v2`, and temporal policy are unchanged. Legacy imports are distinguishable from fresh and current-cache acquisition.
- **Owner:** Study team. **Status:** Adopted for Stage B materialization.

## 2026-09-30 — Provenance-based Stage B model-view isolation

- **Decision:** Determine Stage B isolation through the allowlisted model-view structure and exact deterministic derivation from the normalized source conversation. Prohibit independent injection of linkage, repository, PR, outcome, or source-administration metadata. Preserve unmodified user/assistant text even when it contains an identical repository name, URL, PR reference, path, or identifier.
- **Rationale:** Lexical equality between source-authored conversation text and an administrative value does not establish leakage. The deterministic source-to-normalized-to-model-view derivation provides the required provenance check and detects added fields, changed text, and altered artifact content.
- **Impact:** This corrects validation of the existing `conversation-only-v1` representation; it does not change Stage C inputs, temporal policy, methodology, or any Stage C contract version.
- **Owner:** Study team. **Status:** Adopted before corpus-wide Stage B materialization.

## 2026-09-30 — Original archived HTTP recovery for Stage B

- **Decision:** Admit an identity-matched original historical HTTP response preserved as `ChatgptSharing.HTMLContent` in `data/raw/allPullRequestSharings.zip` through an explicit offline pathway. Require exact share ID and PR association, HTTP 200, nonempty HTML, and current-parser completeness. Select the earliest qualifying archive filename timestamp, with lexical member/source/sharing indexes as deterministic tie-breaks. Never substitute the derived `Conversations` list, screening evidence, parsed caches, correspondence material, or Stage A evidence.
- **Decision:** Version this materially different provenance as `chatgpt-source-v3` with `source_origin = archived_http_response`. Preserve ZIP/member/content hashes, all qualifying candidates, raw archival dates, parser/normalization versions, null `retrieved_at`, `unknown_archive_timezone`, and a separate import time. Keep `case-linkage-v2`, `lossless-conversation-v1`, `conversation-only-v1`, `dir-tfg-v2`, and Stage C contracts unchanged.
- **Rationale:** The five remaining Stage B cases have complete historical structured responses in the replication ZIP. Newer cached pages either lack conversation content or are absent. Control cases reproduce identical canonical model-visible semantic projections from archived HTTP bytes.
- **Impact:** Stage B can recover those sources without network access or derived-data substitution. Completion remains operational and does not change scientific eligibility or run Stage C.
- **Owner:** Study team. **Status:** Adopted for the five-case recovery.

## 2026-09-30 — Preserve modality in Stage C supplied C/S/V extraction

- **Decision:** Version Pass 2 as `dir-stage-c-csv-extraction-v2` and the extraction procedure as `conversation-extraction-v4`. Preserve descriptive versus normative modality: symptoms, failures, historical behavior, and environment/branch/platform differences remain Context unless an admissible source explicitly supplies a desired condition, expected behavior, correctness condition, check/test/assertion, acceptance or verification activity, or prescriptive guidance. Keep observation and expectation atomic when both are present. Retain the Context, Specificity, and Verification categories.
- **Versioning:** Keep `dir-tfg-v2` because the first-generation boundary and temporal method did not change. Keep `stage-c-pass2-v1` and `conversation-draft-v3` because their JSON shapes and field meanings remain compatible. Record the behavioral change through prompt version/hash and `conversation-extraction-v4`; revised outputs use `stage_c_extraction_v4.json` beside preserved v3 development records.
- **Rationale/evidence:** During the Stage C development pilot, `CASE_193801513E85` transformed descriptive branch/local diagnostic observations into the unsupported normative claim that a fix “should account for” them. The v1 prompt generally prohibited inference but did not explicitly forbid this modality shift.
- **Impact:** Existing outputs for the first three development cases remain immutable. The revised procedure must be validated on those cases before continuing the frozen pilot order. Pass 1, deterministic family identity, `tC`, `tFG`, Stage A, and Stage B are unchanged.
- **Owner:** Study team. **Status:** Adopted as a Stage C development-pilot methodology refinement.

## 2026-09-30 — Preserve Stage C provenance for rejected Pass 2 results

- **Decision:** When Pass 2 has been invoked but its returned result fails API completion, parsing, structured-contract validation, or deterministic provenance validation, preserve the available invocation, prompt, schema, model, reasoning, and tools-policy provenance in the failed draft. Keep parsing and validation outcomes separate and emit no accepted C/S/V items from the rejected result.
- **Rationale/evidence:** The `CASE_193801513E85` v4 development run correctly rejected an item with incomplete provenance, but the generic failure record then erased the known Pass 1/Pass 2 invocation configuration and could not satisfy the extraction/prompt-version consistency check.
- **Impact:** Successful extraction validation and item provenance requirements are unchanged. This is a failure-record construction correction within the existing `conversation-draft-v3` shape; it neither accepts the rejected model payload nor changes Stage C methodology.
- **Owner:** Study team. **Status:** Adopted as an engineering correction during the Stage C development pilot.

## 2026-09-30 — Preserve rejected Stage C model proposals outside authoritative fields

- **Decision:** Generalize failure provenance to Pass 1 and Pass 2. Preserve available invocation/response metadata in the failed draft and retain a parsed rejected proposal only in a separate `stage-c-rejected-output-v1` diagnostic sidecar marked non-authoritative. Never copy rejected family, response, target, boundary, temporal, or C/S/V values into authoritative extraction fields.
- **Rationale/evidence:** `CASE_C482978A9FE9` correctly failed because a selected artifact did not belong to the selected response, but the generic Pass 1 failure path discarded the parsed proposal and provider provenance needed to diagnose the model output.
- **Impact:** The scientific `conversation-draft-v3` contract, prompts, extraction version, temporal method, and fail-closed validators remain unchanged. Diagnostics contain no credentials or complete request objects and are ignored generated development artifacts.
- **Owner:** Study team. **Status:** Adopted as an execution/provenance correction.

## 2026-09-30 — Define the authoritative first-generation family as response-local

- **Decision:** Version the Pass 1 prompt as `dir-stage-c-first-generation-v3`. Conceptual artifact-family relationships may span assistant responses, but the authoritative first-generation family contains only coherent artifacts generated in the earliest assistant response that generates the conceptual family's first artifact. Later turns may aid relationship interpretation only and later-response artifacts cannot enter authoritative `artifact_ids`. Every selected artifact must have `source_response_id` equal to the selected `response_turn_id`; deterministic validation continues to reject violations without repair.
- **Rationale/evidence:** Two controlled attempts for `CASE_C482978A9FE9` selected artifacts from several responses while naming the earliest response, explicitly treating later artifacts as demonstrations or reiterations of the same fix. This exposed ambiguity in the v2 prompt's conceptual use of “family,” while the deterministic response-ownership contract consistently rejected the proposal.
- **Impact:** Preserve `first_generation_v2.md` unchanged. Retain `stage-c-pass1-v2`, `dir-stage-c-csv-extraction-v2`, `stage-c-pass2-v1`, `conversation-draft-v3`, `conversation-extraction-v4`, and `dir-tfg-v2`; their structures and meanings remain compatible. Family identity uses only validated response-local selected artifact IDs. The boundary and `tFG` remain tied solely to the selected earliest response. `candidate_artifact_ids` remains auxiliary model output with no new scientific interpretation and does not control the response-local selection.
- **Owner:** Study team. **Status:** Adopted as a Stage C development-pilot prompt clarification.

## 2026-09-30 — Make the Stage C SDK retry allowance explicit

- **Decision:** Configure the OpenAI SDK with `DIR_STAGE_C_MAX_RETRIES`, defaulting to the current value `2` and accepting only integers from `0` through `5`. Pass it explicitly as `OpenAI(max_retries=...)` and persist the configured allowance as `sdk_max_retries` in future Stage C record and rejected-output provenance. Do not infer an observed retry or HTTP-attempt count.
- **Rationale/evidence:** The successful `CASE_C482978A9FE9` v3 development execution used an OpenAI client whose inherited SDK default was `max_retries=2`, but its record did not persist that setting. Making the same bounded value explicit removes environment-dependent inference while retaining transient provider/transport handling.
- **Impact:** SDK automatic retries remain distinct from application-level retries and separately authorized controlled development reruns. Stage C has no application retry loop, and deterministic, semantic, provenance, or human-audit failure remains an explicit failed attempt. This execution/reproducibility configuration does not change prompts, schemas, extraction version, temporal methodology, family identity, boundary, `tFG`, or C/S/V rules. Historical records remain immutable.
- **Owner:** Study team. **Status:** Adopted as Stage C execution configuration.

## 2026-10-01 — Version Stage B generated technical candidates

- **Decision:** Introduce `conversation-only-v2` with deterministic producer `generated-technical-content-v2`. Represent all V2 candidates uniformly as `GTC_<event>_<start>_<end>_<raw-hash-prefix>`, where offsets identify an exact Unicode substring of one assistant response. Candidate kind, Markdown containment, completeness, continuation, and detector evidence are metadata and do not contribute to identity. Declarative XML/HTML/SVG resources and explicit incomplete fragments are candidate-eligible. Candidate status requires later semantic review and does not establish a scientific generated artifact.
- **Decision:** Preserve `conversation-only-v1` and all existing Stage C records unchanged. Record exact V1 equivalence with a required nullable `legacy_artifact_id`; `ARTIFACT_*` remains V1 provenance only. Never synthesize a candidate across responses. Version future V2 Stage C consumption as Pass 1 `dir-stage-c-first-generation-v4` and `conversation-extraction-v5`, retaining response-local selection, the existing deterministic family-ID algorithm, `stage-c-pass1-v2`, `conversation-draft-v3`, Pass 2, and temporal methodology `dir-tfg-v2`.
- **Rationale/evidence:** The development pilot showed that column-zero Markdown fences omitted valid indented fences and that fence-only extraction omitted generated declarative resources such as Android XML. The approved corpus audit supported standalone fences with arbitrary horizontal indentation and found no reviewed inline/prose false positives under the strict delimiter-line rule.
- **Impact:** Stage B gains deterministic line parsing and conservative XML, source, shell, configuration, and bounded JSON classification. Stage C remains responsible for scientific first-family selection, target prompt, boundary, and `tFG`. Full-corpus V2 materialization and migration reporting remain separate checkpoints.
- **Owner:** Study team. **Status:** Adopted for first-phase implementation.

## 2026-10-01 — Correct balanced nested-fence parsing in Stage B V2

- **Context:** The first fail-closed corpus materialization stopped because one V1 outer fenced candidate contained a balanced, differently indented Markdown fence pair inside a source-language string. The V2 parser selected the inner example rather than preserving the exact V1 outer span.
- **Decision:** While seeking an outer fence closer, treat a differently indented delimiter as a nested literal region only when it has an unambiguous same-indentation, unlabeled closer before the outer closer. Skip that balanced nested pair and retain the first compatible outer closer. An unmatched or ambiguous nested region remains fail closed. Apply this rule uniformly and restart corpus materialization from clean V1 inputs.
- **Impact:** The correction restores exact V1 migration for the affected case without case-specific logic, threshold tuning, or changes to candidate identity, Stage C semantics, temporal methodology, or scientific eligibility. The migration report records the committed V2 baseline and correction label `unambiguous-nested-markdown-fence-pairing-v1`.
- **Owner:** Study team. **Status:** Adopted as an engineering correction required by corpus validation.

## 2026-10-01 — Approve the first controlled Stage C V2 wave

- **Decision:** Use a separate V2 development manifest for four ordered cases: `CASE_C482978A9FE9`, `CASE_AADA2C787EEE`, `CASE_5A3A043A5011`, and `CASE_E8F12807DBDC`. Preserve the eight completed V1 cases classified `PRESERVE_V1_NO_V2_RERUN`, including `CASE_5C203B1DBF11` after same-response human impact review.
- **Impact:** The manifest records planned V2 execution only. It does not establish a family, boundary, `tFG`, or scientific eligibility, and it does not alter the historical V1 pilot manifest. The auxiliary `candidate_artifact_ids` prompt wording remains a nonblocking future clarification candidate.
- **Owner:** Study team. **Status:** Adopted for pre-API preparation; live execution remains separately authorized.

## 2026-10-01 — Complete Stage C V2 Phase 1

- **Decision:** Accept the Phase 1 V2 results for `CASE_C482978A9FE9` and
  `CASE_AADA2C787EEE`. C482 selected an earlier first-generation response than
  its V1 result. AADA recovered from the V1 zero-candidate representation.
- **Execution record:** AADA's first V2 Pass 2 result failed deterministic
  provenance validation because its source-turn and source-role arrays were
  structurally incomplete. One controlled rerun under the unchanged prompt,
  schema, validator, Stage B package, and methodology was accepted.
- **Preservation:** Retain the failed AADA canonical record, its
  non-authoritative diagnostic, and the accepted retry as separate artifacts.
  The versioned Phase 1 summary records their paths and hashes.
- **Scope:** These two development cases do not establish V2 performance. No
  Phase 2 case was executed, and scientific eligibility remains unchanged.
- **Owner:** Study team. **Status:** Phase 1 checkpoint accepted.

## 2026-10-01 — Complete Stage C V2 Phase 2

- **Decision:** Accept the Phase 2 V2 results for `CASE_5A3A043A5011` and
  `CASE_E8F12807DBDC`. Stage C grouped three response-local listener-removal
  alternatives for 5A and four response-local TypeScript null-or-empty examples
  for E8 into one semantic family per case.
- **Representation impact:** Both cases selected turn 3, earlier than the
  earliest V1 Stage B represented response at turn 5. Neither case has an
  accepted V1 Stage C scientific result, so this is a representation-impact
  comparison rather than a V1-versus-V2 scientific-result comparison.
- **Execution:** Both cases completed without a controlled rerun. No remaining
  recovered-zero case was executed during Phase 2.
- **Scope:** These development observations do not establish general
  multi-candidate performance or change scientific eligibility.
- **Owner:** Study team. **Status:** Phase 2 checkpoint accepted.

## 2026-10-01 — Make Stage C Pass 2 provenance positional and preserve its outcome

- **Context:** The completed offline corpus audit found four historical extraction-v5 Pass 2 diagnostics (`CASE_51918C8EB470`, `CASE_CE6B20EEAAB5`, `CASE_F7BED13B8119`, and `CASE_27C861787A74`) whose cited turns and roles had unequal cardinality. The v2 prompt required all contributing turns and actual roles, and the v1 response schema required both arrays, but neither explicitly defined positional one-to-one serialization. Deterministic validation already required equal lengths and paired each turn with its role. Separately, two scientifically unresolved records did not preserve the model's non-complete Pass 2 reason.
- **Decision:** Version future execution as Pass 2 prompt `dir-stage-c-csv-extraction-v3`, response schema `stage-c-pass2-v2`, extraction procedure `conversation-extraction-v6`, and final record `conversation-draft-v4`. `source_turns` and `source_roles` are equal-length parallel arrays; `source_roles[i]` is the actual role of `source_turns[i]`, including repeated roles. Evidence remains textually attributable to a cited admissible turn. Add `pass_2_outcome` to future v4 records so Pass 2 status and every non-complete reason survive independently. Keep Pass 1 v4, family identity, boundaries, `tFG`, C/S/V definitions, admissible information, and `dir-tfg-v2` unchanged.
- **Audit evidence:** All 107 accepted extraction-v5 records and all 447 accepted C/S/V items satisfy the clarified positional rule; zero accepted items had a cardinality or positional-role mismatch.
- **Impact:** Historical v4/v5 records and rejected diagnostics remain immutable. The four affected cases are not repaired or promoted and require separately authorized fresh v6 execution. Historical v1/v2 execution mappings remain available; the new `v3` execution contract reads the same `conversation-only-v2` model view and writes `stage_c_extraction_v6.json` without overwriting v5.
- **Owner:** Study team. **Status:** Adopted as a provenance serialization and observability correction.

## 2026-10-01 — Freeze the Post-Stage-C historical reconstruction contract

- **Decision:** Under unchanged `dir-tfg-v2`, define `H_i(tFG)` as the repository, PR, issue/work-item, CI, discussion/review, and temporal-provenance information demonstrably available at or before authoritative `tFG`. Freeze the core repository target as the historically evidenced focal-PR base state applicable at `tFG`; a Stage A base SHA is a candidate, not historical authority. Keep target identity, historical applicability, present materializability, and component availability separate.
- **Decision:** Exact timestamps use `historical_timestamp <= tFG`; date-only same-day ordering remains unresolved without independent evidence. `historical_state_reconstructible = no` requires affirmative scientific evidence. Repository deletion/private transition, missing authentication, rate limits, transport failure, timeout, and present retrieval failure remain unresolved absent such evidence. Missing nonrepository `H_i(tFG)` components do not automatically fail the core repository state.
- **Versioning:** Add `post-stage-c-reconstruction-v1`, `post-stage-c-eligibility-v1`, `post-stage-c-eligibility-manifest-v1`, `historical-state-acquisition-v1`, and `historical-information-index-v1`. Preserve legacy `dir-tfg-v1` contracts unchanged.
- **Impact:** Initialize only the 111 Stage C processable authority rows, resolve their first-generation criterion deterministically, and retain pending final eligibility until historical acquisition resolves the remaining criterion. Stage D still requires final eligibility. No acquisition, pilot execution, or eligibility decision is authorized by this contract implementation.
- **Owner:** Study team. **Status:** Adopted for offline implementation before the reconstruction pilot.

## 2026-10-01 — Freeze the historical target-identity evidence hierarchy

- **Decision:** Determine the focal PR base applicable at `tFG` using, in order: direct historical PR-state evidence; derivable immutable historical relationships; adequately corroborated contemporaneous provider evidence; present-day PR metadata; and present-day Git object/ref evidence. The last two levels are supporting only. Git-object validation and present materialization answer different questions from historical applicability.
- **Conflict rule:** Retain all claims. Stronger historical SHA A is not displaced by later current SHA B. Unresolved disagreement among comparably authoritative historical claims is ambiguous; fetchability cannot decide it. Missing historical evidence remains unresolved rather than scientific `no`.
- **Adjudication:** Humans may apply the hierarchy, compare provenance, and verify derivations. They may not invent values, use final outcomes or implementation, use post-`tFG` substantive evidence to infer identity, or select by fetchability.
- **Impact:** Extend the existing `historical-state-acquisition-v1` and `historical-information-index-v1` representations without changing `dir-tfg-v2`, the 111-case Post-C population, the eight-case pilot, or Stage D entry semantics.
- **Owner:** Study team. **Status:** Adopted before live reconstruction.

## 2026-10-02 — Version Post-C around the historically justified development baseline

- **Problem:** `post-stage-c-reconstruction-v1` operationalized the repository target as the focal-PR base applicable at `tFG`. Its eight-case pilot produced eight unresolved results because the acquisition path supplied only present-day Level 4 PR metadata. The 111-case audit found 82 PRs existed by `tFG`, 29 were created later, and no already-qualified Level 1–3 PR-base evidence; 50 archived commit lists remain derivation leads.
- **Protocol reconciliation:** The experiment needs a repository state at the first-generation boundary, while PR information belongs in `H_i(tFG)` only when it existed. A later PR cannot definitionally supply a contemporaneous boundary.
- **Decision:** Preserve v1 and its pilot unchanged. Introduce `post-stage-c-reconstruction-v2` and define `R_i(tFG)` as the historically justified repository revision representing the project baseline relevant to the focal development task. Use B1 direct evidence, B2 immutable derivation, B3 historically versioned metadata, B4 archived leads, and B5 supporting-only current information. Identity/linkage and temporal applicability precede materialization; B4 is not automatically authoritative and B5 cannot establish identity.
- **Stage alignment:** Post-C establishes minimum repository processability only. Stage F1 assigns discovery/held-out cases; F2 consumes authoritative `R_i(tFG)` and constructs complete `H_i(tFG)`. Stage J1 builds a provenance-bearing structured intent record and J2 reconstructs the prompt without reopening evidence selection. Stage L1 freezes intent-record fidelity before outcome revelation; Stage L2 evaluates generation effectiveness afterward. Fidelity and effectiveness remain separate conclusions.
- **Impact:** No v1 result or current eligibility disposition changes. The same eight cases are prepared unexecuted for a v2 pilot. Stage D and Stage F execution remain blocked pending resolved eligibility and authorization.
- **Owner:** Study team. **Status:** Adopted as the current Post-C contract.
