# Post-Stage-C historical reconstruction

This workflow consumes only rows marked `eligible_for_post_c_scientific_resolution = true` in `cases/manifests/stage_c_post_resolution_authority.csv`. It resolves the authoritative Stage C boundary criterion offline and initializes the remaining historical-state criterion without making a scientific eligibility decision.

`H_i(tFG)` is the project-information space demonstrably available at or before authoritative `tFG`; it includes separately statused repository, PR, issue/work-item, CI, and discussion/review components. The core reconstruction target is the historically evidenced focal-PR base repository state applicable at `tFG`. A Stage A base SHA is only a candidate until historical identity and temporal applicability are established.

Target identity follows the frozen five-level hierarchy in the experiment protocol. Direct historical PR-state evidence outranks derivable immutable relationships, which outrank adequately corroborated contemporaneous provider evidence. Present-day PR metadata and Git evidence remain supporting only. Claims are retained independently; comparable historical conflicts remain ambiguous. Human adjudication may apply the hierarchy and verify derivations, but cannot use fetchability, outcomes, final implementation, or invented values.

Initialize or reproduce the two manifests without network, Git, provider, or model calls:

```bash
python3 -B pipeline/post_stage_c/initialize.py
python3 -B pipeline/post_stage_c/initialize.py --validate-only
```

The command writes `post_stage_c_eligibility.csv` and the proposed eight-case pilot manifest. It does not create acquisition results, execute the pilot, update Stage A, make a final eligibility decision, or begin Stage D.
