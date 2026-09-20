# DIR --- Developer Intent Reconstruction

Research repository for the **Developer Intent Reconstruction** study.

The project investigates whether task-relevant information omitted from
developer prompts can be recovered from software-project evidence that
was available when the prompt was issued, reconstructed in a traceable
way, and used in downstream code generation.

## Project Documentation

The research design and implementation conventions are documented
separately to avoid duplicating methodological details in this README.

-   [`docs/research_questions.md`](docs/research_questions.md) --- study
    goal, central research question, RQ1--RQ3, and key research
    constraints.
-   [`docs/architecture.md`](docs/architecture.md) --- research
    workflow, data flow, stage boundaries, pilot-to-evaluation
    progression, and SAFE/SEALED architecture.
-   [`docs/repository_structure.md`](docs/repository_structure.md) ---
    directory responsibilities, case organization, pipeline components,
    experiments, provenance, and testing structure.
-   [`protocols/pilot_case_selection_and_extraction.md`](protocols/pilot_case_selection_and_extraction.md)
    --- current protocol for screening, selecting, extracting, and
    packaging the initial pilot cases.
-   [`decisions/decision_log.md`](decisions/decision_log.md) ---
    methodological and engineering decisions and their rationale.
-   [`AGENTS.md`](AGENTS.md) --- repository-level instructions for Codex
    and other coding agents.

## Current Project Stage

The current implementation priority is the **initial pilot/development
corpus of approximately 30 cases**.

Work currently follows pilot screening and integrity validation,
selection, complete raw-case extraction, validated first-generation
conversation-side extraction and freeze, exploratory 30-case repository
forensic analysis, and cross-case method discovery.

The existing PatchPrompt-study analysis CSV is a candidate index and
metadata source for this pilot; the complete raw cases require their
original sources. Pilot cases are extracted and used to validate the
method before it is frozen for held-out evaluation. See the pilot
protocol for the source mapping and stage rules.

See
[`protocols/pilot_case_selection_and_extraction.md`](protocols/pilot_case_selection_and_extraction.md)
for the detailed procedure and
[`docs/architecture.md`](docs/architecture.md) for how this stage fits
into the broader study. See
[`docs/repository_structure.md`](docs/repository_structure.md) for the
corresponding output locations.

## Core Validity Boundary

Raw historical cases are stored under:

``` text
cases/raw/<case_id>/
```

Reconstruction-time processing must use temporally partitioned inputs:

``` text
safe/reconstruction/<case_id>/
```

Future or outcome-revealing information is kept under:

``` text
sealed/evaluation/<case_id>/
```

The detailed temporal and leakage rules are documented in
[`docs/architecture.md`](docs/architecture.md),
[`protocols/pilot_case_selection_and_extraction.md`](protocols/pilot_case_selection_and_extraction.md),
and [`AGENTS.md`](AGENTS.md).

## Repository Layout

For the complete directory structure and the responsibility of each
component, see:

[`docs/repository_structure.md`](docs/repository_structure.md)

## Reproducibility

Research outputs should remain traceable to their source cases,
repository state, configuration, code version, and provenance records.

Detailed reproducibility and implementation requirements are maintained
in the project documentation and protocols rather than duplicated here.

## For Coding Agents

Coding agents must read [`AGENTS.md`](AGENTS.md) before making changes
and follow the relevant research protocol and documentation referenced
there.
