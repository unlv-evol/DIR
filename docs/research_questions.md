# Research Questions

## Status

This document records the research goal and research questions.

## Research Goal

A developer prompt to an LLM is not necessarily a complete specification
of the intended software change. Information omitted from the prompt may
already exist in the repository, tests, issues, documentation,
configuration, prior commits, or earlier conversation turns.

The study investigates whether this information can be recovered without
looking into the future, transformed into a compact and traceable
reconstruction of developer intent, and used to improve downstream code
generation.

## Central Research Question

> Can task-relevant information omitted from a developer's prompt be
> reconstructed from software evidence that was available by the
> first-generation boundary, and does providing that reconstructed intent
> enable an LLM to generate code closer to what developers ultimately
> integrate?

## RQ1 -- Expressed Prompt Information

> To what extent do developer prompts explicitly express task-relevant
> Context, Specificity, and Verification information?

RQ1 characterizes what the developer explicitly communicated using the
Context--Specificity--Verification (C/S/V) framework. C/S/V is not a
completeness oracle: a prompt may score highly on these dimensions and
still omit project-specific information needed for the task.

## RQ2 -- Repository-Grounded Evidence and Intent Reconstruction

> What additional task-relevant information is available in the software
> project by the first-generation boundary, and to what extent can that
> information be retrieved, identified, engineered, and used to
> reconstruct the prompt?

RQ2 concerns temporally admissible project evidence and the stages
required to recover it: task anchoring/localization, candidate
retrieval, evidence identification/selection, Evidence Engineering, and
intent reconstruction.

The study must distinguish: - evidence historically available at the
cutoff from evidence successfully retrieved by the pipeline; -
localization failure from retrieval failure; - retrieval failure from
evidence-selection failure; and - automated retrieval from later
diagnostic search.

## RQ3 -- Downstream Effectiveness and Reconstruction Limits

> Does evidence-grounded intent reconstruction improve LLM-generated
> code, and what explains the remaining differences from developers'
> eventual integrated implementations?

RQ3 evaluates the downstream effect of reconstructed intent and the
limits of reconstruction. Sealed historical/final information is used
only after reconstruction and generation outputs have been frozen.

## Cross-Cutting Temporal Constraint

For each conversation `C`, retain both temporal anchors:

``` text
tC = timestamp/date of the first developer prompt in conversation C
tFG = boundary immediately before the assistant response containing
      the first generated artifact in the first snippet family
```

For the current first-generation experiment,
`primary_repository_cutoff = tFG`. Reconstruction repository evidence
must have been available by `tFG` and otherwise admissible. Preserve
availability by `tC` separately for conservative sensitivity analysis.
An unresolved `tFG` never silently becomes `tC`; the former primary-`tC`
procedure remains distinguishable by methodology version.

For target prompt `i`, conversational evidence may include only earlier
observed turns:

``` text
Conv_pre,i = {I1, ..., I(i-1)}
```

The conversation-side record of what was supplied before initial
generation is validated and frozen before repository inspection.
Conversation cues include the target prompt and only permitted prior
turns; repository evidence is evaluated against `tFG`.

The first artifact-bearing response, later conversation turns, post-`tFG` repository
artifacts, later commits/tests/reviews/CI outcomes, final PR diff, merge
outcome, and eventual integrated implementation are sealed from
reconstruction.

## Role of C/S/V

C/S/V is used to characterize information explicitly supplied by the
developer and, where appropriate, to organize information contributed by
project evidence.

Historical numerical C/S/V scores may be used for descriptive analysis;
they are not reconstruction inputs or
retrieval rules. Supplied C/S/V and additional repository C/S/V are
provenanced information categories, not 0–2 scores. Repository items
must be both task-relevant and evaluated for whether they add beyond
the frozen conversation-side record.

## Relationship to Protocol v5

All PA/PN candidates undergo integrity, availability, and processability
screening. An approximately 30% PA/PN-stratified sample of eligible cases
supports independent human validation of conversation-side extraction.
After conversation records are versioned and frozen, a PA/PN-stratified
discovery/held-out split precedes project-evidence analysis. Retrieval
Algorithm v1 is developed from discovery cases and frozen before held-out
application. Existing approximately-30-case pilot outputs are
legacy/provisional, not this validation sample or discovery set. See the
[operational protocol](../protocols/experiment_protocol.md).
