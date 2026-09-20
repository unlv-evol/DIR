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
