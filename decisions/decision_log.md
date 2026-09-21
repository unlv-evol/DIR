# Decision Log

Record important research and engineering decisions.

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
- **Owner:** Study team. **Status:** Adopted.

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
- **Owner:** Study team. **Status:** Adopted.

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
- **Owner:** Study team. **Status:** Adopted.

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
- **Owner:** Study team. **Status:** Adopted.

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
- **Owner:** Study team. **Status:** Adopted for current version.

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
  manifests, smoke runs, caches, and `pilot_cases.csv` remain
  legacy/provisional and unchanged. Future screening is
  `dir-screening-v4` under `dir-tfg-v2` at separate output paths; prior
  `dir-tfg-v1` derived schemas remain legacy. Held-out evidence cannot
  shape Algorithm v1; integrated implementation remains SEALED until
  both current-model outputs are fixed.
- **Owner:** Study team. **Status:** Adopted; migration in progress.

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
- **Resolved interpretation:** Word references to packaging PR identity
  apply to the complete research case/linkage record. The Stage C model view
  remains conversation-only under §3. The same neutral DIR Case ID links the
  restricted record, retrieved source archive, lossless normalized
  conversation, and model view. Preservation in normalized/source layers
  does not make a turn admissible for supplied-C/S/V extraction.
- **Impact:** No real outputs or v1 schemas are rewritten. Current v5 freeze
  code distinguishes procedure and case statuses; the real split remains
  uncreated.
- **Owner:** Study team. **Status:** Adopted; clarified by study team.
