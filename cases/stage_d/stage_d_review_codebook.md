# Stage D review codebook

## Purpose and evidence boundary

Stage D assesses the reliability of the authoritative Stage C conversation
extraction. It does not assess historical Git reconstruction or downstream
implementation outcomes.

The **first generation** is the earliest assistant response containing the
first generated artifact in the selected response-local artifact family. The
**target prompt** is the developer turn that prompted that response. The
**boundary**, with timestamp `tFG`, is immediately before the first-generation
response.

**Context** describes task-relevant conditions already present. **Specificity**
states requested behavior or constraints. **Verification** states supplied
checks, tests, expected results, or acceptance conditions.

The `pre_boundary_conversation` is the only admissible evidence for judging
Context, Specificity, and Verification. The resolved artifacts under
`first_generation.family.artifacts` reproduce exactly what Stage C selected,
while `first_generation_response` supplies the complete containing assistant
response. Both are visible only to assess the first generation, target prompt,
and boundary. Never use either as evidence for C/S/V. No later conversation
turns are provided.

## Review CSV

Each row represents one case. `case_id` is the stable case identifier and
`case_details` is the repository-relative path to its reviewer-safe JSON and is
the **primary Stage D evidence package**. Reviewers should normally make their
judgments using that package.

`conversation_url` provides supplementary access to the original conversation.
It may be used for source inspection, but the Stage D evidence boundary still
applies. Only pre-boundary conversation information is admissible for C/S/V.
The first-generation response may be inspected only for first-generation,
target-prompt, boundary, and `tFG` validation. Turns after it must not influence
Stage D C/S/V judgments.

`pr_url` is supplied only for case traceability and provenance. During
independent Stage D validation, PR content is not admissible C/S/V evidence.
Do not use PR implementation, changed files, commits, comments, reviews, CI
results, merge status, final outcome, or later development information. A
future reconciliation or adjudication step may use the PR only if its separately
approved methodology explicitly permits that use.

Leave a judgment blank until you have reviewed the case.

- `first_generation_correct`, `target_prompt_correct`, and
  `boundary_tFG_correct`: `yes`, `no`, or `uncertain`.
- `context_extraction`, `specificity_extraction`, and
  `verification_extraction`: `correct`, `partially_correct`, `incorrect`, or
  `uncertain`.
- `missing_information`: `none`, `context`, `specificity`, `verification`,
  `multiple`, or `uncertain`.
- `post_boundary_leakage`: `no`, `yes`, or `uncertain`.
- `overall_extraction`: `correct`, `needs_correction`, or `uncertain`.
- `correction_notes`: free text describing required corrections. When
  `missing_information` is not `none`, identify the omitted information and
  its supporting turn or evidence here.
- `reviewer_notes`: optional free text about review uncertainty or rationale.

For each C/S/V category, `correct` means the extraction is supported and
sufficiently complete. `partially_correct` means it is substantially correct
but has an omission, unsupported addition, category problem, or provenance
problem requiring correction. `incorrect` means it is materially wrong.
`uncertain` means the available evidence does not permit a confident judgment.

Reviewers work independently. Do not consult or copy the other reviewer's
answers. Reconciliation and adjudication occur only in a later authorized step.

## Version-controlled review instruments

Both `stage_d_review.csv` and `stage_d_review.xlsx` are intentionally committed.
The CSV is the canonical machine-readable annotation representation used for
validation and later analysis. The XLSX is the frozen reviewer-facing instrument
generated from that CSV, with dropdowns, clickable source URLs, formatting, and
instructions. The XLSX does not replace the CSV as scientific authority.

The committed blank files are the original pre-review instruments. Later human
annotations must be preserved as subsequent versioned review outputs rather
than overwriting repository history or presenting a populated workbook as the
original blank instrument.
