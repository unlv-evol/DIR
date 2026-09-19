# AGENTS.md

# Developer Intent Reconstruction

## Purpose

This repository implements the **Developer Intent Reconstruction** research study.

The project investigates whether task-relevant information omitted from a
developer's prompt can be recovered from software-project evidence that was
available when the prompt was issued, transformed into a compact and traceable
reconstruction of developer intent, and used to improve downstream code
generation.

This is a research repository. Correctness therefore includes both:

1. software correctness; and
2. methodological validity.

An implementation that runs successfully but violates the study design,
temporal boundary, provenance requirements, or safe/sealed separation is
incorrect.

---

# 1. Read Before Making Changes

Before implementing or modifying research-pipeline code, inspect the relevant
project documentation.

At minimum, read:

- `README.md`
- `docs/architecture.md`
- `docs/repository_structure.md`
- `docs/research_questions.md`
- `docs/data_dictionary.md`
- relevant files under `protocols/`
- relevant schemas under `schemas/`
- `decisions/decision_log.md`

For work involving pilot-case extraction, also read the current
**30-case Pilot Case Selection and Extraction Requirements**.

For work involving a specific pipeline stage, inspect that stage's
documentation, schemas, tests, configuration, and upstream/downstream data
contracts before modifying it.

Do not infer research rules from code alone when the documented study protocol
provides an explicit rule.

If documentation, schemas, and implementation disagree, identify the
inconsistency before silently choosing one interpretation.

---

# 2. High-Level Research Workflow

The overall study follows this conceptual workflow:

```text
Candidate index / Raw Source Data
            |
            v
      Case Screening
      and Integrity
            |
            v
      Eligible Case Pool
            |
      +-----+------+
      |            |
      v            v
Pilot /        Scale-up /
Development    Evaluation
Cases          Cases
      |
      v
Raw Case Extraction
      |
      v
cases/raw/<case_id>/
      |
      v
Exploratory Pilot Analysis
      |
      v
Cross-Case Synthesis
      |
      v
Retrieval Algorithm v1
      |
      v
Method Development
and Validation
      |
      v
Method Freeze
      |
      +------------+-------> Held-out evaluation application
                   |         (mechanical raw extraction may be earlier)
                   v
       Snippet-Family Construction
                   |
                   v
          Reconstruction Case
                   |
                   v
         Temporal Partitioning
              /          \
             v            v
           SAFE         SEALED
             |            |
             v            |
       Task Anchors        |
             |            |
             v            |
       Localization        |
             |            |
             v            |
    Candidate Retrieval    |
             |            |
             v            |
     Evidence Selection    |
             |            |
             v            |
    Evidence Engineering   |
             |            |
             v            |
    Intent Reconstruction  |
             |            |
             v            |
    Controlled Generation  |
             +------+-----+
                    |
                    v
              Evaluation
```

The pilot raw cases feed method development and validation before
method freeze. The downstream stages shown after the freeze are also
developed and validated on pilot cases beforehand. Additional cases may
be extracted mechanically earlier, but held-out evaluation cases must
not be used to develop, tune, or revise the method. The pilot protocol
governs source mapping, screening, and temporal precision.

The approximately 30 pilot cases first support exploratory method
discovery. Store per-case analyses in `pilot_analysis/cases/`, separate
from raw, safe, and sealed packages. Never consume `pilot_analysis/` as
reconstruction input. Researchers may inspect downstream history there
to discover what mattered and possible retrieval mechanisms, but any
repository evidence proposed for reconstruction must independently have
been available by the fixed conversation-start cutoff `tC`. For target
prompt `i`, conversational cues use only the target prompt and permitted
earlier turns. Complete individual pilot analyses before synthesizing
Retrieval Algorithm v1. Avoid detailed taxonomies, confidence schemes,
and annotation frameworks unless pilot findings motivate them; see the
pilot protocol.
