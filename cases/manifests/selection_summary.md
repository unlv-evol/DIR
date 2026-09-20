# Screening summary

Screening only; no pilot cases selected.
Screening schema: `dir-screening-v2`; first-generation `tFG` is not derived here.

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
