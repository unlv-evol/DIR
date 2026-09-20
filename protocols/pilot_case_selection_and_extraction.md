# Pilot Case Selection and Extraction Protocol

## Purpose

This protocol defines the current procedure for screening, selecting,
extracting, and conducting the initial exploratory analysis of
approximately 30 cases for the **Developer Intent Reconstruction**
study.

The current first-generation derived methodology is `dir-tfg-v1`.
Earlier primary-`tC` outputs are legacy records and must not be treated
as equivalent to current primary-`tFG` records.

The pilot is a **development corpus**, not the complete study dataset
and not the held-out evaluation corpus. Its first purpose is **method
discovery**: to identify recurring evidence needs, repository locations,
retrieval cues, and feasible leakage-free retrieval paths from close
analysis of real cases. These findings will guide the design and
subsequent validation of the automated localization, retrieval,
selection, Evidence Engineering, and intent-reconstruction pipeline.

The extraction stage must preserve historical information without
deciding which repository evidence is relevant to developer intent.

### Source Population and Relationship to PatchPrompt Outcome Classes

The existing
`data/raw/final_analysis_dataset_from_patchprompt_study.csv` is a
PatchPrompt-study analysis dataset used as a candidate-case index and
metadata source. Its `Outcome_Class` field is inherited from that prior
study, which defines the classes as follows:

-   **PA (Patch Applied):** ChatGPT generated a code snippet and the
    suggested code was incorporated into the pull request, directly or
    after modification.
-   **PN (Patch Not Applied):** ChatGPT generated a code snippet, but the
    suggested code was not incorporated into the pull request or was
    modified beyond recognizable correspondence.
-   **NE (No Existing Patch):** The interaction provided guidance or
    explanation without a code snippet evaluable as a candidate patch.
-   **CL (Closed):** The pull request closed without merging, regardless
    of whether generated code was present. This is a PR-level lifecycle
    outcome rather than the code-focused PA/PN distinction.

The DIR candidate source population is restricted to `PA` and `PN`:
both classes establish that a generated code artifact exists. This
artifact-centered study reconstructs intent associated with generated
software artifacts and later evaluates code-generation behavior against
historical developer implementations. `NE` and `CL` are outside this
specific candidate population because they do not define the same
generated-patch population; this is not a judgment that those cases are
bad or that `CL` never contains generated code. PA and PN describe
patch adoption, not intrinsic code/model quality or success of DIR.

``` text
PA or PN → generated code artifact exists → DIR candidate population
    → integrity validation → manageability/completeness screening
    → eligible pool → C/S/V and observable structural diversity
    → approximately 30 pilot cases
```

Use `PR_Link` and `Conversation_Link` to retrieve missing raw attributes
from their original sources, including PR changed files and lines,
commit count, complete conversation and developer-prompt count, and
conversation date/time. Use the corresponding Context, Specificity, and
Verification scores as pilot-selection metadata. The CSV is not a
complete raw-case source: obtain generated artifacts, PR history,
repository identifiers, and other required material from appropriate
original sources, or explicitly record it as unavailable. `PR_Size` is
inherited metadata from the PatchPrompt source dataset and is not used
by the current DIR pilot screening procedure. Do not modify the source
CSV or relabel its records.

Source: Richard Sserunjogi, Daniel Ogenrwot, and John Businge,
“[Prompt Quality and Pull Request Outcomes: A Stage-Based Empirical
Study of LLM-Assisted Development](https://arxiv.org/abs/2606.19644),”
arXiv:2606.19644, 2026.

------------------------------------------------------------------------

## 1. Unit of Selection

The pilot is selected at the conversation/case level from the available
source data.

A case must retain stable relationships among the case, repository and
PR, ChatGPT conversation, developer prompts, assistant responses,
generated artifacts, and temporal repository identifiers.

Later stages may define one or more reconstruction points and snippet
families within a selected conversation.

Stable identifiers should be introduced so prompts, responses,
artifacts, comments, commits, linked issues, and conditionally included
CI/check items can be referenced reproducibly.

------------------------------------------------------------------------

## 2. Stage 1 --- Screen for Availability, Integrity, and Pilot Workload

Apply the pilot screening rules before selecting cases for diversity.

### 2.1 Development-pilot workload / manageability criteria

Current pilot constraints include:

-   changed files `<= 10`;
-   changed lines `<= 300`;
-   developer prompts `<= 10`;
-   conversation length `<= 8,000` words;
-   commits preferably `<= 10`;
-   complete ChatGPT conversation required;
-   conversation date/time required; and
-   repository/PR identity required.

Compute the measures as follows:

-   **Changed files:** count unique files in the PR diff.
-   **Changed lines:** PR additions + deletions.
-   **Developer prompts:** count developer/user turns, not assistant
    turns.
-   **Conversation length:** count all prompt and response text in the
    complete shared conversation.
-   **PR commits:** obtain the PR commit count from the source/API.

The first four numeric limits are hard pilot screening limits. Record
the observed commit count, but `<= 10` commits is a preference: a case
with more than 10 commits may remain eligible when all hard requirements
are satisfied. Do not exclude it solely for exceeding that preference.

These are **development-pilot workload constraints**, not scientific
definitions of valid DIR cases, definitions of a small PR, or claims
about the full population. Keep cases exceeding a workload limit in the
screening manifest with their specific failed limit and
`pilot_manageability_exclusion`; distinguish this from source
availability/integrity and broader scientific/data eligibility.

Do not relax them merely to obtain 30 cases. If fewer than the desired
number qualify, report the eligible pool and discuss the methodological
consequence before changing thresholds.

Pilot thresholds are not automatically permanent eligibility thresholds
for later full-scale evaluation.

### 2.2 Scientific/data availability and completeness

A case should provide enough source information to support reproducible
extraction, including:

-   repository identity;
-   PR identity;
-   conversation identity/link where available;
-   complete observed ChatGPT conversation;
-   first-prompt/conversation-start date or timestamp;
-   PR metadata needed for screening; and
-   source C/S/V metadata where available.

Do not infer missing source information merely to make a case eligible.
Record source availability separately from development-pilot workload
eligibility. Historical `C_score`, `S_score`, and `V_score` are inherited
PatchPrompt numerical metadata for pilot diversity and description only;
they are not supplied information items or retrieval rules.

### 2.3 Case-integrity validation

Before a case enters the eligible pool, verify that the repository/PR,
ChatGPT conversation, and conversation timestamp belong to the same
source case.

Detect and record, where observable:

-   duplicate PR/conversation pairs;
-   duplicate conversations associated with multiple candidate rows;
-   missing or conflicting repository/PR identities;
-   conversation links that appear unrelated to the associated PR; and
-   other obvious source-linkage inconsistencies.

Do not silently repair ambiguous mappings.

Record at minimum:

``` text
case_integrity_status
duplicate_of
integrity_notes
```

Cases with unresolved integrity failures should not enter pilot
selection until the relationship is resolved.

The screening sequence is:

``` text
candidate case
    ↓
source linkage / integrity check
    ↓
manageability and completeness screening
    ↓
eligible pool
```

------------------------------------------------------------------------

## 3. Stage 2 --- Select Approximately 30 Varied Pilot Cases

Selection occurs from the eligible pool. Do not simply select the 30
shortest or smallest cases.

The `PA`/`PN` restriction defines the generated-code source population;
the PA-versus-PN distinction is not a pilot-selection score. Once that
population is formed, do not rank, prioritize, balance, or prefer cases
by PA versus PN adoption outcome. Select the pilot using case integrity,
manageability, completeness, C/S/V diversity, and observable structural
characteristics as specified below.

### 3.1 Primary diversity --- C/S/V

Variation should be driven primarily by the existing Context,
Specificity, and Verification scores.

Use C/S/V scores as **selection metadata only**. They do not later
control evidence retrieval and numerical scores are not reconstruction
inputs.

Where available:

-   include low, medium, and high Context cases;
-   include low, medium, and high Specificity cases;
-   include low, medium, and high Verification cases;
-   include mixed C/S/V profiles;
-   include some comparatively well-specified prompts as contrasts; and
-   preserve naturally occurring combinations.

Do not force all 27 possible `(C,S,V)` combinations or equal cell
counts.

### 3.2 Secondary diversity --- observable characteristics

After C/S/V diversity, prefer structural diversity where possible:

-   single-turn and multi-turn conversations;
-   one generated artifact and multiple/revised generated artifacts;
-   prompts containing explicit identifiers;
-   file paths;
-   code fragments;
-   errors/exceptions/logs;
-   tests/assertions;
-   URLs;
-   mostly behavioral natural language;
-   ChatGPT links shared by PR authors, reviewers, or other contributors
    where role can be determined; and
-   different observable help-seeking contexts such as
    implementation/change request, bug/error investigation, test or
    CI/build failure, refactoring, API/library usage, design question,
    code-review feedback, issue/requirement interpretation, or
    configuration/dependency problems.

Do not require fixed quotas for these secondary characteristics. Do not
invent a task category when the source evidence does not establish one.

### 3.3 Prohibited selection signals

Do **not** use downstream success or expected study success to select
pilot cases.

Do not select based on:

-   similarity between ChatGPT-generated code and the final PR;
-   whether generated code was adopted;
-   integration depth;
-   whether the PR merged or was otherwise successful;
-   whether a case appears likely to contain useful repository evidence;
-   whether a case appears easy for the proposed method;
-   whether the eventual implementation supports the study hypothesis;
    or
-   whether the later Developer Intent method succeeds.

------------------------------------------------------------------------

## 4. Screening Output

Before packaging selected cases, produce a screening manifest for all
screened cases.

At minimum, include:

``` text
case_id
source_case_id
conversation_id
conversation_url
repository
pr_number
pr_url
canonical_pr_url
Outcome_Class
C_score
S_score
V_score
changed_files
additions
deletions
changed_lines
pr_commits
developer_prompts
assistant_responses
conversation_words
conversation_start
temporal_precision
conversation_temporal_status
conversation_source
conversation_retrieval_status
conversation_parsing_status
pr_retrieval_status
complete_conversation_available
data_completeness_status
case_integrity_status
duplicate_of
integrity_notes
scientific_data_eligible
pilot_manageability_eligible
screening_eligible
exclusion_reason
screening_schema_version
```

Also produce a short summary of:

1.  C/S/V distribution in the eligible pool;
2.  C/S/V distribution in the selected pilot;
3.  complexity distribution in the eligible pool; and
4.  complexity distribution in the selected pilot.

The manifest may also retain observable structural characteristics
when reliably obtained; they do not include reconstruction-point
metadata or speculative repository evidence. A later pilot-selection
manifest records study role without changing stable case identity.
`screening_eligible` (where used) means both source/data eligibility
and pilot workload eligibility passed. Keep the two component judgments
separate. A failed workload limit receives
`pilot_manageability_exclusion`, not a claim that the case is
scientifically invalid. `tFG` and reconstruction-point counts are not
screening fields; derive them only after raw artifact preservation.

Reconstruction points are not screening metadata. Do not estimate or
infer them during screening, or use later reconstruction-point
information to revise pilot eligibility or selection. Select pilot
cases at the conversation/case level using the manageability,
completeness, integrity, C/S/V, and observable structural criteria
above.

------------------------------------------------------------------------

## 5. Stage 3 --- Extract and Package Each Selected Case

Preserve raw text as much as possible. Do not summarize source material
merely to reduce storage. Do not decide which repository evidence is
relevant during extraction.

The preferred architecture stores each selected case under:

``` text
cases/raw/<case_id>/
```

A human-readable consolidated `case.md` may coexist with structured
metadata and separately addressable generated artifacts.

### 5.1 Case metadata

Collect stable case ID; repository name and URL; PR number and URL; C,
S, and V scores; ChatGPT/share URL if available; location where the
ChatGPT link appeared; identity/role of the person sharing the link when
available; and study split/membership metadata.

### 5.2 Complete ChatGPT conversation

Collect the date/time shown at the top or associated with the first
prompt; complete conversation in original order; developer turns labeled
with stable prompt identifiers; assistant turns labeled with stable
response identifiers; code blocks and generated software artifacts
preserved exactly where possible; and all later observed turns rather
than truncating after the first generated artifact.

The raw conversation may contain future information and is therefore not
reconstruction-safe by itself.

### 5.3 Generated artifacts

Generated software artifacts are first-class research objects. In
addition to preserving them in conversational context, extract them as
independently addressable objects where possible.

Record stable artifact ID, source response ID, order within the
response, artifact type, language where identifiable without unsupported
inference, original content, and extraction provenance.

Do not discard earlier artifact versions merely because later responses
revise them. Snippet-family relationships are established in a later
stage.

### 5.4 PR metadata

Collect PR title and description; PR author; `created_at`; `updated_at`;
`closed_at`; `merged_at` where applicable; base/head branches and SHAs
where available; changed-file count; additions; deletions; commit count;
labels; and linked references where available.

### 5.5 Commits

For every PR commit, preserve sequential/stable identifier, SHA, author
name/login, author timestamp, committer timestamp, commit message, and
patch/diff if reasonably obtainable.

If the patch is unavailable, retain the SHA and retrieval metadata
rather than inventing content.

### 5.6 PR conversation and reviews

Preserve issue/general PR comments, review records, and inline review
comments.

For each, record stable identifier, author, `created_at`/`updated_at`,
comment/review type, body text, file path and line/hunk/commit
identifier when applicable, and chronological ordering.

### 5.7 Linked issues

Identify issues explicitly linked or referenced by the PR or
conversation.

For each, preserve where available: issue number/URL, title, author,
created/closed timestamps, body, and comments with authors/timestamps.

Do not manually select only sentences that appear relevant. Preserve
timestamps so later analysis can evaluate availability by both `tC`
and the current primary cutoff `tFG`.

### 5.8 CI/check/build information --- collect only when referenced

Do not collect CI/check/build information by default.

Include it only when a ChatGPT prompt/response or PR discussion/review
explicitly references a CI check, workflow, build failure, test failure,
compiler/type-check failure, deployment failure, or related
automated-check result.

When included, collect only the relevant check/job: check/workflow/job
name, status/conclusion, timestamps, URL or stable identifier, and
specific failure/error excerpt with enough surrounding context to
interpret it.

Do not store complete logs unless the referenced failure cannot
otherwise be understood.

Record the identifier of the prompt, response, PR comment, or review
item that triggered inclusion. If the referenced log is unavailable,
record that fact rather than reconstructing or guessing its contents.

### 5.9 Full PR diff

Store the complete PR diff for the selected raw case and preserve file
paths and diff hunk headers.

Because the pilot screening caps changed lines, the whole diff can be
retained rather than manually selecting apparently relevant hunks.

**Important:** storing the final/full PR diff in the raw historical
package does not make it reconstruction-safe. It must be excluded from
reconstruction whenever it is future/outcome-revealing under the
temporal protocol.

### 5.10 Temporal repository identifiers

Record the ChatGPT conversation-start timestamp/date (`tC`); PR base
SHA; available head/base/commit SHAs and timestamps that may help
reconstruct repository state at both `tC` and the later derived `tFG`;
and snapshot-resolution status where available. Preserve the raw
identifiers even before the first-generation boundary is identified.

If the exact conversation-start repository state is not automatically
derivable, do not guess.

Record whether the source provides a date only or a timestamp. A date
alone does not establish a time of day or an exact repository state; do
not fabricate either.

Appropriate status values include:

``` text
exact
derivable
unresolved
unavailable
```

Distinguish historical availability of an artifact/state from whether
the extractor/API successfully retrieved it.

------------------------------------------------------------------------

## 6. Preferred Raw Case Layout

``` text
cases/raw/CASE_000001/
├── case.md
├── metadata.json
├── conversation.md
├── artifacts/
│   ├── ARTIFACT_001.txt
│   ├── ARTIFACT_002.txt
│   └── artifact_manifest.json
├── pr/
│   ├── metadata.json
│   ├── commits.md
│   ├── conversation_and_reviews.md
│   ├── linked_issues.md
│   ├── ci_and_checks.md        # only if referenced
│   └── full_diff.patch
└── temporal/
    └── repository_identifiers.json
```

The exact serialization may evolve, but stable identity, provenance,
completeness, and traceability must be preserved.

------------------------------------------------------------------------

## 7. What the Extraction Stage Must NOT Do

The extraction stage must not:

-   identify or label the "relevant repository evidence";
-   select only PR files that appear related to the ChatGPT
    conversation;
-   use the final implementation to infer developer intent during
    automated extraction;
-   use the eventual PR diff to localize the task;
-   discard comments, linked-issue text, commits, or generated artifact
    versions merely because they appear unrelated;
-   use downstream success to determine case eligibility;
-   silently repair unavailable source information;
-   guess repository snapshots or SHAs;
-   collapse the complete conversation into a single prompt/response
    pair;
-   rewrite, paraphrase, or summarize the ChatGPT conversation or GitHub
    text;
-   use C/S/V scores as evidence-retrieval rules; or
-   expose raw historical packages directly to reconstruction-time
    stages.

CI/check logs remain the explicit exception to broad historical
collection: collect them only when the ChatGPT conversation or PR
discussion/review points to CI/check/build/test-failure information as
specified in Section 5.8.

------------------------------------------------------------------------

## 8. Raw, Safe, and Sealed Are Different Products

The raw case package preserves historical material for reproducibility.
It is **not** reconstruction-safe.

A later temporal partitioning stage derives:

``` text
safe/reconstruction/<case_id>/
sealed/evaluation/<case_id>/
```

Only temporally admissible information may enter the safe reconstruction
package. Future or outcome-revealing information belongs in the sealed
package and must remain inaccessible during localization, retrieval,
evidence selection, Evidence Engineering, and intent reconstruction.

------------------------------------------------------------------------

## 9. Conversation-First Pilot Analysis and Forensic Discovery

After the selected raw case packages have been created, complete the
conversation-side first-generation analysis in §9.1, validate and freeze
it in §9.2, then inspect repository evidence using §9.3–9.5. Raw
conversation and generated-artifact preservation precede these derived
analyses; neither a derived record nor a safe package replaces raw data.

The purpose is to establish what developers actually supplied before
first generation, then discover what additional task-relevant evidence
existed in the repository by the first-generation cutoff (`tFG`), where
it occurred, and how admissible cues could have found it.

This stage is **method discovery**, not the final evidence-selection or
annotation framework.

Do not force every case to contain useful repository evidence. **"No
useful additional repository evidence found" is a valid pilot result.**

### 9.1 First-generation conversation-side extraction

Using the preserved raw conversation and generated artifacts, identify
the first snippet family, its first generated software artifact, the
assistant response containing it, and the developer prompt immediately
triggering that response. The first-generation boundary (`tFG`) is
immediately **before** that assistant response. Preserve both the
response ID and its source-supported date/timestamp or unresolved
status; do not assign `tFG = tC` merely because `tFG` is unknown.

The target prompt and only permitted earlier conversation turns may be
used to extract the Context, Specificity, and Verification information
actually supplied before initial generation. Exclude the first
artifact-bearing response and every later turn. Record each supplied
item with a stable prompt/response ID and source span. Supplied C/S/V
are information categories, not the inherited 0–2 numerical scores.
Do not inspect repository evidence, infer missing information, or use
PA/PN outcome while producing this conversation-side record. Keep tool
traces and all later turns in raw provenance; they do not enter visible
conversation metrics or supplied-C/S/V extraction.

### 9.2 Human validation and frozen conversation-side record

Validate the first family, first artifact-bearing response, target
prompt, `tFG`, allowed turns, each supplied item and category,
provenance, and absence of future-information leakage. Validate the
approximately 30 pilot cases comprehensively where feasible. Preserve
independent judgments before reconciliation; compute inter-rater
agreement only for defined categorical judgments, not free-form text.
Systematic errors require an extraction-version change and assessment
of which earlier records need regeneration.

After validation, freeze/version a conversation-side record containing
stable IDs; both independent temporal anchors and their precision,
status, and source; target prompt and allowed prior turns; supplied
C/S/V items and provenance; extraction version; validation status; and
`primary_repository_cutoff = tFG`. Repository inspection may add
evidence, but may not rewrite what the developer supplied. A genuine
later correction requires an explicit new record version, preserving
the previous version. Do not freeze an unvalidated or unresolved
first-generation boundary as if it were established.

### 9.3 Retrospective discovery versus reconstruction-time admissibility

During exploratory forensic analysis, researchers may inspect historical
and downstream information such as the historical ChatGPT response, full
PR diff, later PR discussion/reviews, linked issues, later commits, and
eventual implementation when doing so helps determine retrospectively
what mattered.

This retrospective inspection is permitted **only for exploratory
method discovery and explanation**. It does not make downstream
information admissible reconstruction evidence. Any repository-side
evidence proposed for reconstruction must independently have been
available by `tFG` in the current methodology. Preserve separate
`available_by_tC` and `available_by_tFG` judgments where determinable.
Evidence created after `tC` but before `tFG` can pass the current
temporal test; evidence after `tFG` cannot. When either boundary or
artifact time is uncertain, record uncertainty rather than guessing.
Trace proposed evidence to its historical artifact/version. This is a
versioned change from the former `tC` primary cutoff (§12).

Retrieval paths must also be initiable using admissible conversation
cues: for target prompt `i`, the target prompt and only permitted earlier
conversation turns preceding that target prompt may supply cues or
context. Later turns cannot be used.

### 9.4 Six questions for each case

For each selected case, answer:

1.  What did the frozen conversation-side record establish as supplied
    before first generation?
2.  What additional task-relevant Context, Specificity, or Verification
    evidence existed in the repository by `tFG`?
3.  Where was each item, why was it task-relevant, and did it add beyond
    the frozen conversation record? A relevant duplicate is not an
    incremental contribution.
4.  What target-prompt or permitted earlier-turn cue could initiate
    retrieval?
5.  What reproducible operation and path could find it?
6.  What reusable lesson, including a no-evidence result, follows?

### 9.5 Minimal per-case analysis template

Store each exploratory analysis separately from the raw case package:

``` text
pilot_analysis/cases/<case_id>.md
```

Use:

``` text
CASE: <case_id>
PR: <URL>
Conversation URL/date: <URL / source-supported date>
Methodology version: <version>

TEMPORAL ANCHORS
tC / conversation start: <value; precision; status; source>
tFG / first-generation boundary: <value; precision; status; source>
Primary repository cutoff: tFG

FIRST GENERATION
First snippet family: <stable ID / unresolved>
First-generation response: <stable ID / unresolved>
Target prompt: <stable ID / unresolved>
Allowed prior turns: <stable IDs>

FROZEN CONVERSATION-SIDE INFORMATION
Context supplied: <item IDs, items + prompt/response provenance>
Specificity supplied: <item IDs, items + provenance>
Verification supplied: <item IDs, items + provenance>
Validation status / frozen record version: <status / version>

ADDITIONAL REPOSITORY EVIDENCE (repeat per item)
Evidence ID; artifact/location; historical version/SHA:
Evidence dimension: Context / Specificity / Verification
Bounded excerpt or structural fact; why task-relevant:
Adds beyond frozen conversation: YES / NO / UNCERTAIN
Available by tC: YES / NO / UNCERTAIN / UNAVAILABLE
Available by tFG: YES / NO / UNCERTAIN / UNAVAILABLE
Availability basis/status; provenance:

AUTOMATED RETRIEVAL
Admissible cue + target/prior-turn ID; retrieval operation; retrieval path:

CASE LESSON
<reusable insight, or "No useful additional repository evidence found">
```

The `pilot_analysis/` output is researcher interpretation and must not
be mixed into `cases/raw/` or consumed as reconstruction input.

------------------------------------------------------------------------

## 10. Cross-Case Synthesis and Retrieval Algorithm Development

Complete the lightweight exploratory analysis for the selected pilot
cases before synthesizing recurring retrieval mechanisms.

Do not repeatedly redesign the retrieval algorithm case-by-case while
progressing through the pilot.

The intended sequence is:

``` text
Extract selected pilot cases
        ↓
Extract/validate first-generation conversation information
        ↓
Freeze the versioned conversation-side record
        ↓
Resolve historical repository state and analyze each case
with the same lightweight template
        ↓
Complete pilot case lessons
        ↓
Compare lessons across the pilot
        ↓
Identify recurring evidence needs, cues, locations, and retrieval paths
        ↓
Design Retrieval Algorithm v1
        ↓
Subsequent formal method development and validation
```

Only after the pilot analyses have been reviewed together should the
team derive recurring retrieval mechanisms that inform version 1 of the
automated retrieval approach.

Do not prematurely construct a detailed taxonomy, confidence scheme,
false-positive annotation framework, or other additional machinery
unless the pilot findings demonstrate that it is needed.

------------------------------------------------------------------------

## 11. Relationship to Snippet Families and Reconstruction Points

After generated artifacts are preserved, later processing constructs
snippet families representing successive versions of the same logical
artifact.

Identify reconstruction points only after raw extraction and
generated-artifact preservation. Store their stable IDs and counts in
the appropriate derived case or snippet-family representation, not in
the screening manifest. They must not retroactively affect pilot
eligibility or selection.

For each family, preserve family ID, member artifacts, generation order,
developer prompt associated with each version, evidence supporting
family membership, and eventual integration relationship as evaluation
metadata only.

The primary first-generation reconstruction point for the first
snippet family is immediately before the assistant response that
produced its first artifact. Its boundary is `tFG`; preserve `tC`
independently. Later family members and later reconstruction points may
be studied under explicitly versioned procedures.

The same developer prompt may initialize more than one snippet family.
Later family members and later prompts must not become inputs to
reconstruction of the family's initial request.

Identifying the first family and its first artifact-bearing response is
a prerequisite for conversation-side extraction. Fuller family
construction and later reconstruction-point formalization remain
subsequent methodology-development work.

------------------------------------------------------------------------

## 12. Temporal Rule for Later Reconstruction

For conversation `C`, preserve both anchors:

``` text
tC = timestamp/date of the first developer prompt in conversation C
tFG = boundary immediately before the assistant response containing
      the first generated artifact in the first snippet family
primary_repository_cutoff = tFG  # current methodology version
```

For the current first-generation experiment, repository-side evidence
must have been available no later than `tFG` and otherwise admissible.
An item may be unavailable by `tC` but available by `tFG`. Preserve
both availability judgments when supported. `tC` remains historical
metadata, a conservative sensitivity cutoff, and a diagnostic
comparison point. Do not silently substitute `tC` if `tFG` is
unresolved; an explicit future methodology/version decision would be
required to make `tC` primary again. The former primary-`tC` and
current primary-`tFG` outputs must carry distinguishable methodology
versions. Do not overwrite a known `tC` while deriving `tFG`.

Keep timestamp versus date-only precision, temporal status, and source
separately for each anchor. An exact repository state cannot be claimed
from a date alone. If source times or ordering are insufficient, mark
the relevant anchor or evidence availability uncertain, unresolved, or
unavailable. `tFG = tC` must never be assigned as a fallback.

For target prompt `i`, the target prompt and only permitted earlier
conversation turns preceding that target prompt may supply
conversational context or retrieval cues. Later turns are inadmissible.

Raw historical packages remain lossless but are not reconstruction-safe.
The current SAFE partition admits only evidence established by `tFG`
and otherwise allowed; post-`tFG` or outcome-revealing material remains
SEALED. Preserve the information needed for a later, separately
versioned `tC` sensitivity partition. The eventual integrated
implementation is evaluation-only.

The retrospective exploratory analysis in Section 9 does not alter this
reconstruction-time temporal rule.

------------------------------------------------------------------------

## 13. Pilot Development, Method Freeze, and Later Evaluation

The approximately 30 cases are used to discover, develop, and validate
the methodology.

The pilot proceeds broadly as:

1.  screen and select pilot cases;
2.  extract complete raw case packages;
3.  identify the first snippet family, first artifact-bearing response,
    target prompt, and `tFG` from conversation/raw-artifact sources;
4.  extract supplied C/S/V from allowed conversation only, validate
    it, and freeze/version the conversation-side record;
5.  resolve the historical repository state and conduct lightweight
    exploratory forensic analysis using the frozen record;
6.  complete case lessons and compare them across the pilot;
7.  identify recurring retrieval mechanisms and design Retrieval
    Algorithm v1;
8.  develop and validate later stages such as snippet-family
    construction, reconstruction points, temporal partitioning,
    localization, retrieval, selection, Evidence Engineering, and
    reconstruction;
9.  resolve consequential methodological ambiguities; and
10. freeze/version the stable methodology before applying it to held-out
    evaluation cases.

Raw extraction of additional cases may occur earlier when it is purely
mechanical. Held-out evaluation cases must not be used to develop, tune,
or revise the methodology.

If evaluation-case inspection reveals a need for a methodological
change, record it and version any future procedure. Do not revise the
frozen primary evaluation procedure using those held-out cases.

Use manifests such as:

``` text
cases/manifests/
├── screened_cases.csv
├── pilot_cases.csv
├── evaluation_cases.csv
├── excluded_cases.csv
└── artifact_manifest.csv
```

Study role is metadata; it must not alter stable case identity.

------------------------------------------------------------------------

## 14. Pilot Deliverables

The pilot should produce at least:

``` text
cases/manifests/screened_cases.csv
cases/manifests/pilot_cases.csv
cases/manifests/selection_summary.md
cases/raw/<case_id>/
pilot_analysis/cases/<case_id>.md
pilot_analysis/conversation/<case_id>/record_<version>.json
    # derived, validated/frozen when ready; retain older versions
```

The screening output should cover the full screened pool and preserve
transparent eligibility, integrity, and exclusion information.

The pilot-case manifest should identify the selected development cases
and their relevant selection characteristics.

The selection summary should report eligible-pool and selected-pilot
characteristics, C/S/V and manageability distributions, exclusions,
case-integrity findings, and important missing-data observations.

Each raw case package should preserve the complete historical material
specified in this protocol.

Each `pilot_analysis/cases/<case_id>.md` should contain the six-question
exploratory analysis from §9.4–9.5. Conversation-side records must be
versioned and frozen before repository evidence analysis.

Reproduction instructions should document the exact commands,
APIs/libraries, source mappings, and field definitions needed to
reproduce screening and extraction.

------------------------------------------------------------------------

## 15. Pilot Completion Criteria

Before scaling or treating the retrieval method as stable, the pilot
should demonstrate at least:

-   reproducible case screening;
-   explicit case-integrity validation;
-   transparent inclusion/exclusion reasons;
-   complete conversation preservation;
-   complete preservation of generated artifacts;
-   reproducible first-snippet-family, first-generation-response, and
    target-prompt identification;
-   supplied-C/S/V items with prompt/response provenance, human
    validation, and versioned frozen conversation-side records;
-   independent preservation of `tC` and `tFG` with precision, status,
    source, and `tFG` as the current primary repository cutoff;
-   distinguishable old primary-`tC` and current primary-`tFG`
    methodology versions;
-   stable identifiers and provenance;
-   reproducible raw-case packaging;
-   documented handling of temporal repository identifiers;
-   completion of the lightweight exploratory analyses;
-   explicit separation of retrospective discovery from
    reconstruction-time admissibility;
-   cross-case synthesis of recurring retrieval mechanisms;
-   defensible snippet-family construction when that later stage is
    introduced;
-   reproducible `tFG` repository-state handling and retained `tC`
    sensitivity information;
-   evidence traceability with separate task relevance, incremental
    contribution beyond frozen conversation, and availability by both
    temporal anchors where determinable;
-   safe/sealed temporal partitioning when that later stage is
    introduced;
-   no use of sealed information during reconstruction-time stages; and
-   documented no-evidence, uncertain, unresolved, and failed cases
    rather than silent omission.

The broader study should not scale merely to compensate for unresolved
temporal, representation, integrity, or leakage problems.

------------------------------------------------------------------------

## Guiding Principle

The pilot may use historical information retrospectively to **discover
what retrieval mechanisms are needed**, but the later reconstruction
system may use only information that the study defines as admissible at
the reconstruction point.

Every substantive addition to reconstructed intent must remain traceable
to its source.
