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
    workflow, data flow, stage boundaries, discovery-to-evaluation
    progression, and SAFE/SEALED architecture.
-   [`docs/repository_structure.md`](docs/repository_structure.md) ---
    directory responsibilities, case organization, pipeline components,
    experiments, provenance, and testing structure.
-   [`protocols/experiment_protocol.md`](protocols/experiment_protocol.md)
    --- current Protocol v5 experiment procedure across Stages A–L.
-   [`decisions/decision_log.md`](decisions/decision_log.md) ---
    methodological and engineering decisions and their rationale.
-   [`AGENTS.md`](AGENTS.md) --- repository-level instructions for Codex
    and other coding agents.

## Current Project Stage

Protocol v5 is the adopted primary experiment design. It screens all
PA/PN candidates for integrity, availability, and processability, then
packages and analyzes conversations in isolation. Conversation-side
records are validated and frozen before a stratified discovery/held-out
split and historical-project evidence analysis. Retrieval Algorithm v1
is developed only on discovery cases and frozen before held-out use.

The PatchPrompt CSV is a candidate index, not complete raw-case data.
See the operational protocol for screening, versioning, and stage rules.

See
[`protocols/experiment_protocol.md`](protocols/experiment_protocol.md)
for the detailed procedure and
[`docs/architecture.md`](docs/architecture.md) for how this stage fits
into the broader study. See
[`docs/repository_structure.md`](docs/repository_structure.md) for the
corresponding output locations.

Current conversation-side infrastructure includes Stage A screening, Stage B lossless packaging, a two-pass Stage C extraction pipeline, and the offline Post-Stage-C reconstruction/eligibility contracts. Stage C uses only the isolated conversation view, derives `tFG` after validated first-generation selection, and extracts textual supplied C/S/V from strictly pre-boundary turns. The Post-C layer binds authoritative Stage C records, resolves the boundary criterion, and initializes historical-state reconstruction without making a final eligibility decision. Live historical acquisition remains a separate reviewed step before Stage D.

## Core Validity Boundary

Raw historical audit cases, when materialized, are stored under:

``` text
cases/raw/<case_id>/
```

Conversation-side analysis first uses isolated packages under
`cases/conversations/<case_id>/`. Reconstruction-time processing later
uses temporally partitioned inputs:

``` text
safe/reconstruction/<case_id>/
```

Future or outcome-revealing information is kept under:

``` text
sealed/evaluation/<case_id>/
```

The detailed temporal and leakage rules are documented in
[`docs/architecture.md`](docs/architecture.md),
[`protocols/experiment_protocol.md`](protocols/experiment_protocol.md),
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
