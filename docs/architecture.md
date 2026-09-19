# System Architecture

## Research Data Flow Architecture

The architecture supports both the initial 30-case pilot/development corpus and the later larger-scale study. After screening, integrity validation, selection, and raw extraction, all selected pilot cases receive lightweight exploratory forensic analysis. Cross-case synthesis then informs Retrieval Algorithm v1 and subsequent formal method development and validation. Once the methodology is sufficiently stable, it is frozen and versioned before application to held-out evaluation cases.

The architecture also separates raw historical case extraction from temporally admissible reconstruction data and sealed evaluation information. This separation prevents future or outcome-revealing information from influencing evidence retrieval or intent reconstruction.

```text
                 +--------------------------------------+
                 | PatchPrompt CSV / original sources   |
                 +------------------+-------------------+
                                    |
                                    v
                 +--------------------------------------+
                 | Case Screening                       |
                 | Candidate indexing                   |
                 +------------------+-------------------+
                                    |
                                    v
                 +--------------------------------------+
                 | Case Integrity Validation            |
                 | Source linkage and duplicates        |
                 +------------------+-------------------+
                                    |
                                    v
                 +--------------------------------------+
                 | Manageability and Completeness       |
                 | Pilot limits and required data       |
                 +------------------+-------------------+
                                    |
                                    v
                 +--------------------------------------+
                 | Eligible Case Pool                   |
                 +------------------+-------------------+
                                    |
                       +------------+------------+
                       |                         |
                       v                         v
          +-------------------------+  +-------------------------+
          | Pilot Case Selection    |  | Held-out Evaluation     |
          | Initial ~30 cases       |  | Additional cases        |
          +------------+------------+  +------------+------------+
                       |                         |
                       v                         | No method development,
          +-------------------------+             | tuning, or revision
          | Pilot Raw Extraction    |             |
          +------------+------------+             |
                       |                         |
                       v                         |
          +-------------------------+             |
          | cases/raw/<case_id>/    |             |
          +------------+------------+             |
                       |                         |
                       v                         |
          +-------------------------+             |
          | Exploratory 30-Case     |             |
          | Forensic Analysis       |             |
          | Lightweight discovery   |             |
          +------------+------------+             |
                       |                         |
                       v                         |
          +-------------------------+             |
          | pilot_analysis/cases/   |             |
          | <case_id>.md            |             |
          +------------+------------+             |
                       |                         |
                       v                         |
          +-------------------------+             |
          | Cross-Case Synthesis    |             |
          | After all pilot cases   |             |
          | pilot_analysis/         |             |
          | synthesis/              |             |
          +------------+------------+             |
                       |                         |
                       v                         |
          +-------------------------+             |
          | Recurring needs,        |             |
          | locations, cues, paths  |             |
          +------------+------------+             |
                       |                         |
                       v                         |
          +-------------------------+             |
          | Retrieval Algorithm v1  |             |
          +------------+------------+             |
                       |                         |
                       v                         |
          +-------------------------+             |
          | Formal Method           |             |
          | Development/Validation  |             |
          +------------+------------+             |
                       |                         |
                       v                         |
          +-------------------------+             |
          | Method Freeze / Version |             |
          +------------+------------+             |
                       |                         |
                       +------------+------------+
                                    |
                                    v
                 +--------------------------------------+
                 | Raw Extraction if Needed             |
                 | Mechanical extraction may be earlier |
                 +------------------+-------------------+
                                    |
                                    v
                 +--------------------------------------+
                 | cases/raw/<case_id>/                 |
                 +------------------+-------------------+
                                    |
                                    v
                 +--------------------------------------+
                 | Snippet-Family Construction          |
                 | Reconstruction Points                |
                 +------------------+-------------------+
                                    |
                                    v
                 +--------------------------------------+
                 | Reconstruction Case                  |
                 +------------------+-------------------+
                                    |
                                    v
                 +--------------------------------------+
                 | Temporal Partitioning                |
                 +------------------+-------------------+
                                    |
                       +------------+------------+
                       |                         |
                       v                         v
          +-------------------------+  +-------------------------+
          | Reconstruction-Safe     |  | Sealed Evaluation       |
          | safe/reconstruction/    |  | sealed/evaluation/      |
          | <case_id>/              |  | <case_id>/              |
          +------------+------------+  +------------+------------+
                       |                         |
                       v                         |
          +-------------------------+             |
          | Task Anchor Extraction  |             |
          +------------+------------+             |
                       |                         |
                       v                         |
          +-------------------------+             |
          | Task Localization       |             |
          +------------+------------+             |
                       |                         |
                       v                         |
          +-------------------------+             |
          | Candidate Retrieval     |             |
          +------------+------------+             |
                       |                         |
                       v                         |
          +-------------------------+             |
          | Evidence Selection      |             |
          +------------+------------+             |
                       |                         |
                       v                         |
          +-------------------------+             |
          | Evidence Engineering    |             |
          +------------+------------+             |
                       |                         |
                       v                         |
          +-------------------------+             |
          | Intent Reconstruction   |             |
          +------------+------------+             |
                       |                         |
                       v                         |
          +-------------------------+             |
          | Controlled Generation   |             |
          +------------+------------+             |
                       |                         |
                       +------------+------------+
                                    |
                                    v
                 +--------------------------------------+
                 | Final Evaluation                     |
                 +--------------------------------------+
```



## Architecture Interpretation

### 1. Source Dataset and Screening

The pipeline begins with available source data. The existing PatchPrompt-study analysis CSV is a candidate-case index and metadata source, not the complete raw-case source; see the pilot protocol for its use and source limitations. Candidate cases are screened for required identifiers, data completeness, and other eligibility conditions.

The protocol defines the PA+PN generated-code candidate population from inherited PatchPrompt outcome classes. PA versus PN adoption status does not rank or balance pilot cases.

For the initial pilot, additional manageability constraints are applied so that cases can be inspected deeply. These constraints are pilot-specific and do not define the general eligibility requirements for the later full study.

Case integrity is checked before manageability and completeness determine the eligible pool. Pilot selection then draws approximately 30 cases from that pool. See the pilot protocol for the screening and selection rules.

### 2. Pilot / Development Corpus

Approximately 30 cases are initially selected as the pilot/development corpus. Selection emphasizes diversity in Context, Specificity, and Verification (C/S/V), with secondary structural diversity considered where possible. The first use of these cases is exploratory method discovery: researchers inspect each raw case using the lightweight template in the pilot protocol. Only after completing the individual pilot analyses do they synthesize recurring evidence needs, repository locations, retrieval cues, and retrieval paths into Retrieval Algorithm v1. These interpretations belong in `pilot_analysis/`, not in raw cases or reconstruction inputs.

The pilot corpus is used to:

* understand recurring evidence-localization patterns;
* understand recurring evidence-retrieval paths;
* develop and refine task localization;
* develop and refine candidate evidence retrieval;
* develop the evidence-selection procedure;
* develop Evidence Engineering;
* refine the intent-reconstruction representation;
* identify failure modes and insufficient-evidence cases;
* validate the human annotation and adjudication procedures; and
* establish the final methodology for the larger study.

C/S/V scores support diversity of the pilot corpus but must not be used as evidence-retrieval rules.

This exploratory work precedes formal development and validation of snippet-family construction, reconstruction points, temporal partitioning, localization, retrieval, selection, Evidence Engineering, and reconstruction. Retrospective inspection may use downstream history to understand what mattered; it does not make that history admissible reconstruction evidence.

### 3. Method Freeze

After pilot extraction, analysis, and convergence activities, the study freezes and versions the methodological decisions that will be evaluated on additional cases. Purely mechanical extraction of additional cases may occur earlier, but held-out evaluation cases must not be used to develop, tune, or revise the methodology.

Depending on the final study design, the frozen components may include:

* task-anchor extraction;
* task-localization rules;
* candidate-retrieval strategies;
* evidence-selection criteria;
* Evidence Engineering transformations;
* intent-reconstruction schema;
* provenance requirements;
* temporal-admissibility rules;
* evaluation metrics; and
* experimental configurations.

Changes made after the method freeze must be explicitly versioned and documented rather than silently incorporated into the primary evaluation.

### 4. Scale-up / Evaluation Corpus

Additional eligible cases from the broader dataset can subsequently be processed using the same architecture.

Held-out evaluation cases must remain outside method development, tuning, and revision so they can evaluate how well the frozen methodology generalizes beyond the initial 30-case pilot.

The architecture therefore does not treat the 30 pilot cases as a special case format. A case has the same identity and raw-package structure regardless of whether it belongs to the pilot, development, validation, or evaluation corpus.

Study membership should be represented through metadata or manifests rather than encoded into the case identifier or directory name.

For example:

```text id="bkw61n"
CASE_000001 -> pilot
CASE_000002 -> pilot
CASE_000031 -> evaluation
CASE_000032 -> evaluation
```

rather than using identifiers such as `PILOT_CASE_001` and `EVAL_CASE_001`.

### 5. Raw Case Extraction

For every processed case, the extraction pipeline creates a raw historical case package under:

```text id="quhv70"
cases/raw/<case_id>/
```

The raw package may contain:

* complete ChatGPT conversation;
* generated software artifacts;
* PR metadata;
* commits;
* reviews and comments;
* explicitly linked issues;
* conditionally included CI/check information;
* complete PR diff; and
* temporal repository identifiers.

Generated artifacts are preserved as independently addressable objects in addition to remaining in their original conversational context.

The raw extraction format is therefore reusable for both pilot and later scale-up cases.

### 6. Snippet-Family Construction and Reconstruction Points

Generated artifacts may subsequently be organized into snippet families representing successive versions of the same logical artifact.

Developer prompts are preserved as potential reconstruction points.

The resulting reconstruction case identifies the task, artifact family, conversation context, and temporal boundary required for later reconstruction.

### 7. Temporal Partitioning

The raw historical package is not reconstruction-safe input.

Repository-side reconstruction evidence must have been available by the fixed conversation-start cutoff `tC`, the timestamp/date of the first developer prompt. Changes after `tC` remain inadmissible even if they predate a later target prompt. For target prompt `i`, conversational cues may use the target prompt and only permitted earlier turns; later turns are inadmissible. Exploratory pilot analysis does not change either boundary.

It may contain information that became available only after a reconstruction point, including:

* later conversation turns;
* later generated artifacts;
* later commits;
* later reviews;
* final PR changes;
* merge information; and
* eventual implementation information.

A temporal partitioning stage therefore derives two separate views.

#### Reconstruction-safe package

```text id="zxuz53"
safe/reconstruction/<case_id>/
```

contains only information admissible at the selected reconstruction point.

#### Sealed evaluation package

```text id="70flk1"
sealed/evaluation/<case_id>/
```

contains future or outcome-revealing information that must remain inaccessible during task localization, candidate retrieval, evidence selection, Evidence Engineering, and intent reconstruction.

### 8. Evidence Identification and Intent Reconstruction

Only reconstruction-safe information is used to:

1. derive task anchors;
2. localize the task within the temporally valid repository state;
3. retrieve candidate evidence;
4. select task-relevant evidence;
5. perform Evidence Engineering; and
6. reconstruct developer intent.

Each stage remains separately identifiable so that failures in localization, retrieval, selection, Evidence Engineering, or reconstruction can be distinguished.

### 9. Controlled Generation and Evaluation

Controlled generation compares experimental conditions under a consistent generation environment.

Only after reconstruction and generation are complete may sealed information be used for final evaluation or explicitly designated post-hoc analysis.

This allows the study to compare generated outputs against downstream historical information without allowing that information to influence the reconstruction process.

## Case Cohort Management

Case identity is independent of study role.

The `cases/raw/` directory therefore contains cases using stable case identifiers:

```text id="b2l2kl"
cases/
├── raw/
│   ├── CASE_000001/
│   ├── CASE_000002/
│   ├── CASE_000003/
│   └── ...
│
└── manifests/
    ├── screened_cases.csv
    ├── pilot_cases.csv
    ├── selection_summary.md
    ├── evaluation_cases.csv
    ├── excluded_cases.csv
    └── artifact_manifest.csv
```

The manifests determine how cases are used in the study.

For example, `pilot_cases.csv` identifies cases used for methodology development, while `evaluation_cases.csv` identifies cases reserved for later evaluation.

This allows the dataset to scale without changing the underlying case representation or directory architecture.

## Design Principles

1. **The architecture is corpus-independent.** The same case representation and processing architecture support both the initial 30-case pilot and later larger-scale analysis.

2. **Pilot cases are development cases.** They may be inspected to discover patterns and refine the methodology.

3. **Evaluation cases should not silently become development cases.** Where feasible, cases reserved for evaluation must not be used to tune the method being evaluated.

4. **Method changes are versioned.** Once the methodology is frozen, subsequent changes must be explicitly recorded and evaluated as a new version where appropriate.

5. **Raw extraction and reconstruction are separate stages.** Raw historical case packages preserve available study material but must not be treated as reconstruction-safe input.

6. **Temporal admissibility is enforced before reconstruction.** Information must satisfy the reconstruction-point cutoff before it can enter the safe package.

7. **Safe and sealed information remain separate.** Future and outcome-revealing information must not be accessible to localization, retrieval, evidence selection, Evidence Engineering, or intent reconstruction.

8. **Cases have stable identities.** Cases, conversations, prompts/reconstruction points, responses, generated artifacts, and snippet families should have stable identifiers that allow their relationships to be reproduced.

9. **Study role is metadata, not identity.** Whether a case belongs to the pilot, development, validation, or evaluation corpus should be represented through manifests or metadata rather than changing its case identifier.

10. **Generated artifacts are first-class research objects.** Generated software artifacts are preserved both in their original conversational context and as independently addressable artifacts for later snippet-family construction and evaluation.

11. **Repository state is never guessed.** If the exact repository state at the temporal cutoff cannot be established, the status is recorded as unresolved rather than assigning an unsupported snapshot.

12. **Availability and retrieval are distinguished.** Failure to retrieve an artifact does not imply that the artifact did not historically exist.

13. **Every evidence item has provenance.** Evidence should be traceable to its source artifact, location or span, temporal status, task anchor, and retrieval path.

14. **Localization, retrieval, and selection are evaluated separately.** Failures at one stage should not be silently attributed to another.

15. **C/S/V supports pilot diversity, not evidence retrieval.** Context, Specificity, and Verification scores may guide pilot sampling but must not be used as rules for locating or selecting repository evidence.

16. **Human validation remains independent until adjudication.** Independent judgments are preserved before consensus labels are produced.

17. **Dataset and run versions are recorded.** Derived datasets, experiments, configurations, and outputs must be traceable to their corresponding inputs and code versions.

18. **Failed, ambiguous, and insufficient-evidence cases are retained.** The study must not retain only cases where evidence retrieval or intent reconstruction succeeds.
