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
> reconstructed from software evidence that was already available when
> the prompt was issued, and does providing that reconstructed intent
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
> project when a developer prompt is issued, and to what extent can that
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

For each conversation `C`, define the repository cutoff:

``` text
tC = timestamp/date of the first developer prompt in conversation C
```

Repository evidence used for any reconstruction in that conversation
must have been available no later than `tC`.

For target prompt `i`, conversational evidence may include only earlier
observed turns:

``` text
Conv_pre,i = {I1, ..., I(i-1)}
```

Repository evidence is therefore frozen at conversation start, while
conversational evidence advances only through turns preceding the target
prompt.

The target response, later conversation turns, post-cutoff repository
artifacts, later commits/tests/reviews/CI outcomes, final PR diff, merge
outcome, and eventual integrated implementation are sealed from
reconstruction.

## Role of C/S/V

C/S/V is used to characterize information explicitly supplied by the
developer and, where appropriate, to organize information contributed by
project evidence.

Numerical C/S/V scores: - may be used as pilot-selection metadata to
obtain variation; - must not be treated as reconstruction inputs; - must
not control evidence retrieval; and - must not be optimized as a proxy
for reconstruction quality.

## Relationship to the Pilot

The initial approximately 20--30/30 cases are a development and
validation pilot. They are used to establish and validate the
extraction, temporal partitioning, snippet-family, localization,
retrieval, evidence-selection, and reconstruction procedures before
broader evaluation.

The pilot is not the complete study population. Once the methodology is
sufficiently stable, the relevant procedures should be frozen/versioned
and applied to additional eligible cases.
