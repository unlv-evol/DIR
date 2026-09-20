# Repository Structure

This document explains what each directory is for and what it should contain.
It complements `docs/architecture.md`: architecture describes research
data flow; this document describes where the corresponding artifacts
belong.

## Recommended top-level structure

``` text
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
├── cases/
│   ├── README.md
│   ├── manifests/
│   └── raw/
├── pilot_analysis/
│   ├── README.md
│   ├── conversation/
│   ├── cases/
│   └── synthesis/
├── safe/
│   └── reconstruction/
├── sealed/
│   └── evaluation/
├── pipeline/
│   ├── screening/
│   ├── extraction/
│   ├── partitioning/
│   ├── family_construction/
│   ├── snapshot/
│   ├── localization/
│   ├── retrieval/
│   ├── selection/
│   ├── evidence_engineering/
│   ├── reconstruction/
│   └── evaluation/
├── annotations/
├── experiments/
├── results/
├── provenance/
├── scripts/
├── src/
│   └── developer_intent/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── leakage/
└── docs/
```

Directories and schemas may be populated incrementally. An empty
directory does not imply that its data contract has already been
finalized.

------------------------------------------------------------------------

## 1. Research protocol and configuration

### `config/`

Central configuration for reproducible runs.

-   `config/default.yaml` --- default project configuration.
-   `config/pilot.yaml` --- pilot-study settings.
-   `config/retrieval.yaml` --- retrieval settings.
-   `config/experiments/` --- experiment-specific configurations.

Keep experiment parameters and methodologically meaningful thresholds
out of source code where practical. Do not silently change research
thresholds merely to make cases or tests pass.

### `schemas/`

Machine-readable data contracts shared across workstreams.

Current derived contracts are `frozen_conversation_v1.schema.json` and
`repository_evidence_v1.schema.json`, both marked `dir-tfg-v1`. The
validated frozen conversation record precedes repository evidence
analysis; neither schema is a raw-package schema. See the pilot
protocol, §§9 and 12.

Expected schemas may eventually include:

-   `conversation.schema.json`
-   `turn.schema.json`
-   `artifact.schema.json`
-   `snippet_family.schema.json`
-   `reconstruction_case.schema.json`
-   `repository_snapshot.schema.json`
-   `task_anchor.schema.json`
-   `evidence_candidate.schema.json`
-   `evidence_selected.schema.json`
-   `reconstruction.schema.json`
-   `annotation.schema.json`

These schemas define pipeline outputs and exchange formats between
Developer 1 and Developer 2. The directory may initially be sparse or
empty. Do not create speculative schemas merely to populate it. Add them
as persistent research objects stabilize, keeping schemas synchronized
with producers, consumers, validation, documentation, and tests.

### `protocols/`

Human-readable research procedures. The current pilot protocol is:

``` text
protocols/pilot_case_selection_and_extraction.md
```

Future protocols may cover temporal cutoff rules, reconstruction, task
localization, evidence retrieval, annotation/adjudication, Evidence
Engineering, and evaluation. Protocols explain research procedure rather
than implement it.

### `decisions/`

Research and engineering decisions.

-   `decisions/ADR/` --- Architecture/Research Decision Records.
-   `decisions/decision_log.md` --- chronological decisions and
    rationale.

Record consequential choices such as temporal-cutoff policy,
family-construction rules, retrieval strategy, safe/sealed semantics,
pilot-threshold changes, or annotation/evaluation changes.

------------------------------------------------------------------------

## 2. Data and research cases

### `data/`

Dataset-oriented layers:

-   `data/raw/` --- original source material; do not silently modify.
-   `data/intermediate/` --- deterministic processing outputs.
-   `data/derived/` --- analysis-ready derived datasets.

Large external artifacts should be referenced through manifests,
checksums, or reproducible acquisition instructions where appropriate
rather than unnecessarily committed to Git.

### `cases/`

The central representation of individual research cases.
The updated design uses stable raw cases plus manifests:

``` text
cases/
├── README.md
├── manifests/
│   ├── screened_cases.csv
│   ├── pilot_cases.csv
│   ├── selection_summary.md
│   ├── evaluation_cases.csv
│   ├── excluded_cases.csv
│   └── artifact_manifest.csv
└── raw/
    ├── CASE_000001/
    ├── CASE_000002/
    └── ...
```
 A case should not be renamed or moved merely because it
participates in pilot/development, convergence, or evaluation. Those
roles belong in manifests and metadata.

Use stable `case_id`, `conversation_id`, `reconstruction_point_id`,
`response_id`, `artifact_id`, and `family_id` values.

### `cases/raw/`

Complete historical case packages. Preferred layout:

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
│   ├── ci_and_checks.md        # only when inclusion rule is satisfied
│   └── full_diff.patch
└── temporal/
    └── repository_identifiers.json
```

Raw packages preserve complete historical information for
reproducibility, including information that may later be sealed.

**`cases/raw/` is not reconstruction-safe input.**

### `cases/manifests/`

Tracks screening, study membership, exclusions, and artifact
inventories. The initial \~30 cases are the **pilot/development
corpus**, not the complete study. Later scale-up/evaluation cases should
use the same stable case representation after method freeze/versioning.
`cases/manifests/selection_summary.md` records eligible-pool and
selected-pilot characteristics, C/S/V and manageability distributions,
exclusions, case-integrity findings, and important missing-data
observations after screening has run.

### `pilot_analysis/`

`pilot_analysis/conversation/<case_id>/record_<version>.json` stores a derived,
human-validated and versioned conversation-side record before repository
inspection; it is not raw or reconstruction-safe input by itself.
`pilot_analysis/cases/<case_id>.md` stores the lightweight, researcher-generated
repository forensic analysis of each selected pilot case. After the individual
analyses are complete, `pilot_analysis/synthesis/` stores cross-case
lessons used to develop Retrieval Algorithm v1. These interpretations
are separate from complete historical material in `cases/raw/` and
from later formal independent validation in `annotations/`.

Pilot analysis may inspect downstream history retrospectively for
method discovery. It is not reconstruction-safe evidence and must not
be consumed by the reconstruction pipeline. Proposed repository-side
evidence must independently have been available by the current primary
cutoff `tFG`; retain `tC` and both availability judgments where known.

------------------------------------------------------------------------

## 3. Leakage-controlled data partitions

### `safe/`

`safe/reconstruction/<case_id>/` contains only information admissible at
the reconstruction point, such as the target developer prompt,
admissible preceding conversation, developer-supplied information,
frozen repository snapshot/reference, and necessary task metadata.

### `sealed/`

`sealed/evaluation/<case_id>/` contains future or outcome-revealing
information withheld during reconstruction. Depending on the
reconstruction point, this may include the target historical response,
later turns/artifacts, post-cutoff repository information, later
commits/tests/reviews/CI, final PR diff, final implementation, and
integration outcomes.

The safe/sealed boundary is a scientific-validity safeguard, not merely
an organizational convention.

``` text
cases/raw/
    |
    v
Temporal Partitioning
   / \
  v   v
SAFE  SEALED
```

------------------------------------------------------------------------

## 4. Research pipeline

### `pipeline/screening/`

Screens source cases for linkage/integrity, pilot manageability, and
completeness before selection and raw extraction. It records unresolved
integrity failures and does not use reconstruction-point metadata for
eligibility or pilot selection.

### `pipeline/extraction/`

Extracts conversations, turns, generated artifacts, PR
metadata, commits, discussion/reviews, linked issues, conditionally
included CI/check information, full PR diff, and temporal identifiers.
Extraction preserves history; it does not decide which repository
evidence is relevant.

### `pipeline/partitioning/`

A newer explicit stage that derives reconstruction-safe and sealed
packages from raw cases according to the reconstruction point and
temporal protocol.

### `pipeline/family_construction/`

Constructs snippet families, preserves generated-artifact versions and
ordering, associates versions with prompts, and identifies
family-relative reconstruction points. Retrospective family information
must not leak later versions into reconstruction.

### `pipeline/snapshot/`

Creates/resolves/validates frozen repository snapshots and metadata.
Never guess an unsupported state or SHA. Appropriate status values
include:

``` text
exact
derivable
unresolved
unavailable
```

Distinguish historical availability from extractor/API retrieval
success.

### `pipeline/localization/`

Identifies the task-local repository region from admissible task
anchors. It must operate on the temporally valid repository state and
cannot use sealed final information.

### `pipeline/retrieval/`

Retrieves candidate evidence while preserving provenance and retrieval
paths.

### `pipeline/selection/`

Selects task-relevant evidence and records contribution, source/span,
temporal admissibility, uncertainty, C/S/V relationship where
appropriate, and provenance. Retrieval success and selection success are
distinct.

### `pipeline/evidence_engineering/`

Reduces and organizes selected evidence into compact payloads while
preserving relevant information, uncertainty, and provenance. It must
not invent missing requirements.

### `pipeline/reconstruction/`

Constructs evidence-grounded intent using only admissible inputs. Every
substantive addition should be traceable to evidence; unresolved
ambiguity should remain unresolved.

### `pipeline/evaluation/`

Computes evaluation measures after reconstruction/generation outputs
have been frozen and relevant sealed information may be revealed.
Post-hoc explanation remains separate from primary reconstruction.

------------------------------------------------------------------------

## 5. Human validation

### `annotations/`

-   `annotations/independent/developer_1/` --- first independent
    annotation set.
-   `annotations/independent/developer_2/` --- second independent
    annotation set.
-   `annotations/adjudicated/` --- adjudicated/consensus labels.
-   `annotations/diagnostic_search/` --- explicitly separate diagnostic
    searches.

Independent judgments remain separate until agreement/adjudication.
Diagnostic search must not be retroactively represented as automated
retrieval.

`annotations/` holds later formal validation and adjudication. It does
not replace the exploratory researcher interpretations in
`pilot_analysis/`.

------------------------------------------------------------------------

## 6. Experiments

### `experiments/`

-   `experiments/retrieval/` --- retrieval comparisons/baselines.
-   `experiments/selection/` --- evidence-selection experiments.
-   `experiments/evidence_engineering/` ---
    evidence-reduction/engineering experiments.
-   `experiments/reconstruction/` --- intent/reconstruction experiments.
-   `experiments/controlled_generation/` --- controlled code-generation
    experiments.
-   `experiments/ablations/` --- ablation configurations.

Planned conditions may include:

``` text
A0 = original developer information only
A1 = + candidate evidence
A2 = + selected evidence
A3 = + engineered evidence
A4 = reconstructed prompt
```

Keep experiment definitions separate from reusable pipeline
implementation. Pilot cases support method development/validation;
held-out evaluation cases must remain outside method development,
tuning, and revision.

------------------------------------------------------------------------

## 7. Results

### `results/`

-   `results/pilot/` --- pilot/development results.
-   `results/convergence/` --- agreement, adjudication, and convergence
    results.
-   `results/evaluation/` --- downstream evaluation results.
-   `results/figures/` --- publication figures and visualizations.

Results must be traceable to run manifests, dataset versions,
configuration, and code versions. Failed and insufficient-evidence cases
should be retained rather than silently excluded.

------------------------------------------------------------------------

## 8. Provenance and reproducibility

### `provenance/`

-   `provenance/manifests/` --- dataset/case/input manifests.
-   `provenance/lineage/` --- links between inputs and derived outputs.
-   `provenance/checksums/` --- hashes for important frozen artifacts.
-   `provenance/runs/` --- code version, configuration, model/settings,
    inputs, outputs, and run metadata.

Expected lineage:

``` text
Paper Result
→ Experiment Run
→ Configuration
→ Generated Artifact
→ Reconstructed Intent
→ Engineered Evidence
→ Selected Evidence
→ Candidate Evidence
→ Localization
→ Task Anchors
→ Reconstruction-Safe Case
→ Frozen Repository Snapshot
→ Raw Case / Source Data
```

Do not silently overwrite frozen datasets or experimental outputs.

------------------------------------------------------------------------

## 9. Automation and implementation

### `scripts/`

Thin command-line/operational entry points, such as dataset screening,
raw extraction, family construction, snapshot creation, safe/sealed
partitioning, boundary validation, provenance validation, and pilot
execution. Reusable logic belongs in `src/`.

### `src/developer_intent/`

Reusable Python package for extraction, partitioning, family
construction, snapshotting, localization, retrieval, selection, evidence
engineering, reconstruction, and evaluation.

Prefer small, typed, testable, deterministic components with explicit
inputs and outputs.

### `tests/`

-   `tests/unit/`
-   `tests/integration/`
-   `tests/leakage/`

Leakage tests are especially important because leakage prevention is a
scientific-validity requirement. They should eventually verify that
reconstruction-time stages cannot access target responses, later
turns/artifacts, post-cutoff material, final implementation, or other
sealed information.

------------------------------------------------------------------------

## 10. Documentation

### `docs/`

Current documents:

-   `architecture.md` --- overall architecture and research data flow.
-   `repository_structure.md` --- directory responsibilities and
    expected contents.
-   `research_questions.md` --- central research question, RQ1--RQ3, and
    related constraints.

Recommended later documents:

-   `data_dictionary.md` --- stable field definitions/data contracts.
-   `experiment_matrix.md` --- experiments, baselines, factors, and
    outputs.
-   `reproducibility.md` --- reproduction of datasets, runs, and
    results.

Do not present unstable/not-yet-defined schemas as finalized.

------------------------------------------------------------------------

## 11. `AGENTS.md`

`AGENTS.md` lives at the repository root and gives coding agents
repository-level instructions, especially temporal admissibility,
safe/sealed separation, stable identifiers, artifact preservation,
provenance, leakage prevention, and escalation of methodology-changing
ambiguities.

It is version-controlled development infrastructure, not a replacement
for the research protocol or architecture.

------------------------------------------------------------------------

## 12. Updated case lineage

``` text
Original source
→ Case integrity validation and screening
→ Eligible case pool
     ├── Pilot/development cases → Raw case extraction → cases/raw/<case_id>/
     │       → First-generation conversation extraction/validation/freeze
     │       → Repository-state resolution → Exploratory pilot analysis → Cross-case synthesis
     │       → Retrieval Algorithm v1 → Formal method development/validation
     │       → Method freeze/version
     └── Held-out evaluation cases ────────────────────────┘
→ Raw case extraction if needed → cases/raw/<case_id>/
→ Snippet-family construction → Reconstruction point → Temporal partitioning
     ├── SAFE → Frozen snapshot/reference → Task anchors → Localization
     │        → Candidate evidence → Selected evidence → Engineered evidence
     │        → Intent reconstruction → Controlled generation
     └── SEALED ------------------------------------------------→ Evaluation
```

Raw extraction may technically occur before final cohort assignment when
operationally useful. Pilot cases are extracted and used for method
development and validation before method freeze. Additional cases may
be extracted earlier only as a mechanical operation; held-out
evaluation cases must not be used to develop, tune, or revise the method.
See the pilot protocol for the detailed sequence.

------------------------------------------------------------------------

## 13. Key structural principles

1.  **Stable case identity:** study role belongs in manifests/metadata,
    not case IDs or lifecycle directories.
2.  **Pilot as development:** the initial \~30 cases establish and
    validate the method; they are not the entire study.
3.  **Method freeze/versioning:** later evaluation cases should not
    silently become method-development cases.
4.  **Raw is not safe:** raw historical cases must be temporally
    partitioned before reconstruction-time use.
5.  **SAFE/SEALED are first-class boundaries:** enforce and test them.
6.  **Generated artifacts are first-class objects:** preserve all
    versions and their prompt/response relationships.
7.  **Repository state is never guessed:** explicitly record
    uncertainty.
8.  **Availability differs from retrieval:** historical existence and
    successful extraction are separate facts.
9.  **Failure types remain separate:** localization, retrieval,
    selection, engineering, reconstruction, and evaluation failures
    should not be conflated.
10. **End-to-end provenance:** results remain traceable to source data,
    snapshots, configurations, code versions, and runs.
11. **Schemas evolve deliberately:** empty placeholders are not
    finalized contracts.
12. **Failed cases are research data:** do not silently remove cases
    because the method performs poorly.
