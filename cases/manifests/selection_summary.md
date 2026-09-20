# Screening summary

Screening schema: `dir-screening-v3`; first-generation `tFG` is not derived here.

Source records: 265
PA/PN candidates: 142
Confirmed development-pilot screening eligible: 68
Scientific/data eligible: 122
Pilot workload eligible: 73
Pilot workload exceeded: 61
Pilot workload unresolved: 8
The final eligible-pool size remains unresolved while required source facts are missing.
Detected duplicate candidates: 9
Unresolved source linkage: 11
Candidates with incomplete screening data: 13

## Hard-limit failures observed

- passes_changed_files: 38 failed; 2 unresolved
- passes_changed_lines: 55 failed; 2 unresolved
- passes_prompt_count: 5 failed; 11 unresolved
- passes_conversation_length: 1 failed; 11 unresolved

## PA/PN candidate distribution (descriptive only)

- PA: 89
- PN: 53

## Exclusion reasons

- changed_files_limit: 38
- changed_lines_limit: 55
- conversation_length_limit: 1
- integrity_duplicate: 9
- integrity_unresolved: 11
- missing_changed_files: 2
- missing_changed_lines: 2
- missing_complete_conversation: 11
- missing_conversation_start: 11
- missing_conversation_words: 11
- missing_developer_prompts: 11
- missing_pr_commits: 2
- missing_temporal_precision: 11
- pilot_manageability_exclusion: 61
- prompt_count_limit: 5

## Missing fields

- missing_changed_files: 2
- missing_changed_lines: 2
- missing_complete_conversation: 11
- missing_conversation_start: 11
- missing_conversation_words: 11
- missing_developer_prompts: 11
- missing_pr_commits: 2
- missing_temporal_precision: 11

## Eligible C/S/V distributions

- C_score: {'0': 1, '1': 27, '2': 40}
- S_score: {'1': 41, '2': 27}
- V_score: {'0': 32, '1': 33, '2': 3}

## Eligible PA/PN distribution (descriptive only)

- PA: 39
- PN: 29

Source CSV SHA-256: `5b1cc2d726744f8e0960e3f8ffcaabdd3a56dce74fdfdc7858e620c1a39feafc`
Run scope: all PA/PN candidates.
pr_retrieval_status: {'not_found': 2, 'retrieved_authenticated': 140}
conversation_retrieval_status: {'retrieved_archive': 4, 'retrieved_public': 138}
conversation_parsing_status: {'parsed': 127, 'parsed_archive': 4, 'unsupported_or_malformed': 11}
conversation_archive_status: {'not_attempted': 127, 'not_found': 3, 'pr_mismatch': 3, 'recovered': 4, 'summary_only_unresolved': 5}

## Pilot selection

Selected pilot/development cases: 30 of 68 confirmed screening-eligible cases.
Pilot manifest SHA-256: `313ac1499a1bcecabb23003889a2d3d89cc3c003b7b031cae9c8152a143102da`.
Selection uses reviewed C/S/V diversity and observed conversation/task characteristics; PA/PN outcome and downstream success are not selection signals.
Generated-artifact and revision counts are deferred until raw extraction.

### C/S/V distributions

| Score | Eligible pool | Selected pilot |
| --- | --- | --- |
| C_score | `{'0': 1, '1': 27, '2': 40}` | `{'0': 1, '1': 8, '2': 21}` |
| S_score | `{'1': 41, '2': 27}` | `{'1': 14, '2': 16}` |
| V_score | `{'0': 32, '1': 33, '2': 3}` | `{'0': 12, '1': 15, '2': 3}` |

### Joint C/S/V profiles in selected pilot

- (0, 1, 0): 1
- (1, 1, 0): 3
- (1, 1, 1): 1
- (1, 2, 0): 1
- (1, 2, 1): 2
- (1, 2, 2): 1
- (2, 1, 0): 4
- (2, 1, 1): 5
- (2, 2, 0): 3
- (2, 2, 1): 7
- (2, 2, 2): 2

### Observed complexity

| Measure | Eligible pool | Selected pilot |
| --- | --- | --- |
| changed_files | min 1, median 3, max 10 | min 1, median 3, max 9 |
| changed_lines | min 2, median 56.5, max 300 | min 2, median 50, max 300 |
| developer_prompts | min 1, median 1, max 10 | min 1, median 2, max 10 |
| conversation_words | min 61, median 379, max 2814 | min 62, median 583, max 2814 |
| pr_commits | min 1, median 4, max 35 | min 1, median 3.5, max 35 |

Single-developer-prompt cases: 12; multi-prompt cases: 18.
Case-level selection observations and rationales are recorded in `cases/manifests/pilot_cases.csv`.
