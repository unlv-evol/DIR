# Post-Stage-C v4 corpus execution

Execution date: 2026-10-05. Contract `post-stage-c-reconstruction-v4`; procedure `post-stage-c-git-lineage-v4`.

## Population and outcomes

- Authoritative Stage-C-processable population: 111 unique cases.
- Reconstructed focal state: 75 (67.57%).
- Reconstructed base state: 36 (32.43%).
- Unresolved: 0.
- PA: 68 cases; 46 focal (67.65%), 22 base (32.35%), 0 unresolved.
- PN: 43 cases; 29 focal (67.44%), 14 base (32.56%), 0 unresolved.
- Previous read-only audit pattern: 75 focal / 36 base. Final v4 result is identical.

The authoritative per-case table is `cases/manifests/post_stage_c_v4_corpus_authority.csv`, containing every one of the 111 cases exactly once.

## Temporal, routing, and validation results

- Selected temporal basis: 111 `committer_time`; 0 `author_time_fallback`; 0 `unavailable`.
- Fourteen cases contain at least one focal/base lineage commit whose author and committer timestamps cross `tFG`: `CASE_0CE9E03556F1`, `CASE_1C3B62857D19`, `CASE_3E10D31BBE69`, `CASE_5D45BE40E95A`, `CASE_7351FB1ECD56`, `CASE_74FE6518B1D8`, `CASE_8A756AAC10B8`, `CASE_978B83E2DF72`, `CASE_97AFC2022473`, `CASE_AD8C4F13A90B`, `CASE_B98070F8A24D`, `CASE_C95F69523646`, `CASE_EE7F13CD9FB7`, and `CASE_F7BED13B8119`. Committer time remained authoritative.
- Temporal/topological ambiguities: 0.
- Base routing among 36 base cases: 30 `pr_base_ref`; 6 `other_explicitly_justified_route`; 0 `current_default_branch_substitution`.
- Commit validation and exact recursive-tree materialization: 111/111.
- Historical observability: 111 `not_confirmed`; 0 `confirmed`.
- Final acquisition, validation, and repository-access failures: 0.
- Six expected 404 responses occurred for deleted/unresolvable recorded base refs and were resolved by the validated focal-root external-parent topology route. One accepted focal pilot record retained an irrelevant failed base probe; its focal result was unaffected.

## Existing accepted records

- Fourteen accepted records were revalidated under the final implementation and remained scientifically identical: the same eight pilot records and six weak-routing records.
- A provenance-only runner discrepancy was detected before reuse: focal cases initially omitted `base_lineage_ref`. The runner was corrected to preserve the PR base ref for all paths. No accepted record was overwritten, and no selected state changed.

## Scientific eligibility readiness

- `first_generation_boundary_identifiable = yes`: 111/111.
- Current eligibility ledger `historical_state_reconstructible = unresolved`: 111/111 because the ledger was intentionally not mutated by this run.
- V4 reconstruction evidence supports `historical_state_reconstructible = yes`: 111/111.
- Existing ledger `remaining_criteria_status`: solely `historical_state_reconstructible_unresolved` for all 111.
- Stage C authority validation is `validated` and `adjudication_required = false` for all 111.
- Therefore 111 cases appear ready for final Post-C eligibility resolution under the existing rules, subject to applying the reconstruction results through the separately reviewed eligibility transition. No transition was applied here.

## Safeguards

PA/PN was used only for reporting. No later PR discussion/review content, post-`tFG` implementation content, current PR base SHA as automatic authority, silent current-default substitution, or inferred uncommitted state entered selection. Scientific eligibility was not changed and Stage D was not started. V1/v2/v3 outputs were not altered. Nothing was committed or pushed.
