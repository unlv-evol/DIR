# Developer Intent Reconstruction

## Purpose

This repository implements the **Developer Intent Reconstruction**
research study. Software correctness and methodological validity are
both required.

Before making research-pipeline changes, read the authoritative
repository documentation relevant to the task.

## Required Reading

At minimum, inspect:

-   `README.md`
-   `docs/architecture.md`
-   `docs/research_questions.md`
-   `docs/repository_structure.md`
-   relevant files under `protocols/`
-   `decisions/decision_log.md` when present

For pilot screening and extraction, specifically read:

-   `protocols/pilot_case_selection_and_extraction.md`

The `schemas/` directory may be incomplete while data contracts are
still being designed. Do not assume an empty or placeholder schema is
authoritative. When persistent objects become stable, prefer
schema-first changes and keep schemas, producers, consumers,
documentation, and tests synchronized.

If documentation, protocol, code, and schemas disagree, identify the
inconsistency before silently choosing an interpretation.

## Core Research Invariants

1.  Preserve temporal admissibility.
2.  Never use future information during reconstruction.
3.  Keep reconstruction-safe and sealed evaluation information separate.
4.  `cases/raw/` contains complete historical case packages and is **not
    reconstruction-safe input**.
5.  `safe/reconstruction/` contains only information admissible at the
    reconstruction point.
6.  `sealed/evaluation/` contains future/outcome-revealing information.
7.  Preserve all generated software artifacts, including earlier/revised
    versions.
8.  Maintain stable case, conversation, prompt/reconstruction-point,
    response, artifact, and snippet-family identifiers.
9.  Record provenance and retrieval paths.
10. Never guess an unsupported repository snapshot or SHA.
11. Distinguish historical availability from retrieval success.
12. Distinguish localization failure, retrieval failure, and
    evidence-selection failure.
13. Keep diagnostic search separate from automated retrieval output.
14. Do not optimize numerical C/S/V scores as a reconstruction
    objective.
15. Do not modify research methodology merely to make an implementation
    work.
16. Preserve failed and insufficient-evidence cases.

## Temporal Rule

For each conversation `C`, preserve the timestamp/date of the first
developer prompt:

``` text
tC = timestamp/date of the first developer prompt in conversation C
```

Stage C determines `tFG`, the boundary immediately before the assistant
response containing the first generated artifact in the first snippet
family. Under methodology `dir-tfg-v2`, repository evidence used for the
primary reconstruction experiment must have been available no later than
`tFG`. Preserve `tC` independently for provenance, diagnostics, and
separately versioned sensitivity analysis. Never substitute `tC` for an
unresolved `tFG`.

For target prompt `i`, conversational evidence may include only earlier
observed turns.

Do not use the target response, later conversation turns, post-cutoff
repository artifacts, later commits/tests/reviews/CI, final PR diff,
merge outcome, or eventual integrated implementation during
reconstruction.

## Current Priority

The near-term priority is the initial approximately 30-case
pilot/development corpus.

Prioritize: 1. reproducible screening; 2. transparent
eligibility/exclusion reasons; 3. pilot selection support; 4. complete
raw case extraction; 5. preservation of conversation structure; 6.
preservation of generated artifacts as first-class objects; 7. stable
identifiers; 8. temporal repository identifiers; 9. reproducible raw
case packages; and 10. preparation for safe/sealed partitioning.

The pilot is a development/validation corpus, not the full study. Pilot
manageability thresholds are not automatically permanent full-study
eligibility criteria.

## Raw Case Boundary

Raw cases live under:

``` text
cases/raw/<case_id>/
```

Raw extraction should preserve historical information without deciding
which repository evidence is relevant.

Reconstruction-time stages must consume temporally partitioned safe
inputs rather than unpartitioned raw cases.

## Pilot Selection

Use C/S/V primarily to obtain variation in the pilot. C/S/V scores are
selection metadata, not retrieval controls or reconstruction inputs.

Do not select cases based on downstream success, code adoption, merge
outcome, similarity to final implementation, apparent evidence
usefulness, or expected support for the hypothesis.

## Generated Artifacts

Generated artifacts are first-class research objects. Preserve each
artifact independently with source response, order, content,
type/language where supported, and provenance.

Do not discard earlier versions.

Snippet-family construction occurs later and must remain separate from
reconstruction-safe input.

## SAFE / SEALED

Temporal partitioning derives:

``` text
safe/reconstruction/<case_id>/
sealed/evaluation/<case_id>/
```

Task-anchor extraction, localization, retrieval, evidence selection,
Evidence Engineering, and intent reconstruction must not access sealed
information.

Enforce this boundary programmatically and with leakage tests where
practical.

## Evidence Pipeline

Keep these stages separable:

``` text
task anchors
-> localization
-> candidate retrieval
-> evidence selection
-> Evidence Engineering
-> intent reconstruction
-> controlled generation
-> evaluation
```

Persist meaningful intermediate outputs so failures can be attributed to
the correct stage.

Every substantive reconstructed addition must be traceable to admissible
evidence. Preserve unresolved ambiguity rather than inventing a likely
requirement.

## Provenance

Where applicable, preserve source dataset version,
case/conversation/reconstruction-point IDs, repository and
commit/snapshot, file/span, cutoff, retrieval path, pipeline/code
version, configuration, model/version, timestamps, checksums, and run
IDs.

## Implementation Style

Prefer: - small testable functions; - explicit data models; - type
hints; - deterministic behavior; - clear stage boundaries; - structured
logging; - informative errors; - configuration over duplicated
hard-coded research constants; and - reusable library code with thin
orchestration layers.

Avoid: - hard-coded local paths; - silent exception swallowing; -
undocumented manual corrections; - outcome-dependent logic; -
leakage-prone shortcuts; and - broad unrelated refactors.

## Methodological Ambiguity

If an implementation choice could alter the research methodology:

1.  identify the ambiguity;
2.  explain plausible alternatives;
3.  state the methodological consequence of each;
4.  distinguish recommendations from documented protocol; and
5.  wait for a research decision before implementing a
    methodology-changing assumption.

Routine engineering choices that do not affect research validity do not
require escalation.

## Testing

Add appropriate unit, integration, and leakage tests.

For temporal code, test boundary cases.

For safe/sealed processing, test that sealed information cannot enter
reconstruction inputs.

Do not claim successful validation unless the relevant tests were
actually run.

## Research Decisions

Methodologically important changes should be documented in
`decisions/decision_log.md` and, where appropriate, an ADR.

Do not silently encode major methodological decisions only in source
code.

## Guiding Principle

When convenience conflicts with methodological validity, preserve
methodological validity.

> At reconstruction time, use only information defined as admissible at
> that reconstruction point, and keep every substantive addition to
> reconstructed intent traceable to its source.
