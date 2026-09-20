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

For `dir-screening-v3`, secondary-characteristic fields in
`cases/manifests/screened_cases.csv` are descriptive selection metadata,
not eligibility rules or reconstruction inputs. `conversation_turn_pattern`
counts visible developer turns in a complete parsed conversation.
`prompt_identifier_signal`, `prompt_file_path_signal`,
`prompt_code_fragment_signal`, `prompt_error_log_signal`,
`prompt_test_assertion_signal`, and `prompt_url_signal` search only those
developer turns. `detected` means the documented lexical rule found a
cue; `not_detected_by_rule` does not establish absence; `unavailable`
means complete parseable conversation evidence is missing.
`secondary_characteristics_evidence` stores each detected literal cue
and its developer-turn index; `secondary_characteristics_basis` records
the source scope and rule version. `help_seeking_context_cues` are
lexical leads, not assigned task categories. The actual context,
mostly-behavioral judgment, link-sharer role, and generated-artifact
pattern are `not_assessed` until supported source review or raw-artifact
preservation. The screening CLI README specifies the current rules.

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
