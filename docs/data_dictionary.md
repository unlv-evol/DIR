# Data Dictionary

This document is the human-readable companion to `schemas/`.

Each field should document:

- field name
- definition
- data type
- required/optional status
- source
- temporal admissibility
- whether it is reconstruction-safe or sealed
- example
- notes/known limitations

The JSON schemas are the machine-readable contracts; this document explains them for researchers.

For current first-generation derived records (`dir-tfg-v1`):

- `C_score`, `S_score`, `V_score`: inherited numerical PatchPrompt
  metadata for pilot diversity and description only.
- `context_supplied[]`, `specificity_supplied[]`,
  `verification_supplied[]`: information actually present in the target
  prompt or permitted earlier conversation, with stable-turn
  provenance; not numerical scores.
- `evidence_dimension`: Context, Specificity, or Verification category
  for an additional historical repository item. `task_relevance` and
  `adds_beyond_frozen_conversation` are separate judgments.
- `conversation_start_time` (`tC`) and `first_generation_cutoff`
  (`tFG`): independent value, precision, status, and source records.
  The current `primary_repository_cutoff` is `tFG`; never fill missing
  `tFG` from `tC`.
- `available_by_tC` and `available_by_tFG`: separate historical
  availability judgments (`YES`, `NO`, `UNCERTAIN`, `UNAVAILABLE`).
  Source date-only values do not imply an exact time of day.
- `methodology_version`: `dir-tfg-v1` for current derived records;
  earlier primary-`tC` outputs are not semantically equivalent.

See the pilot protocol for operational definitions and the two current
schemas for machine-readable derived contracts. Screening retains
`conversation_start` as its historical `tC` equivalent; `tFG` is not
inferred during screening.
