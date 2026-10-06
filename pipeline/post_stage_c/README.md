# Post-Stage-C reconstruction

The only active implementation is the accepted v4 method. It reconstructs `S_i(tFG)` from authoritative Stage C output; Stage F later constructs `H_i(tFG)`.

```bash
python3 pipeline/post_stage_c/run.py --check-config
python3 pipeline/post_stage_c/run.py --case-id CASE_97AFC2022473 --dry-run
python3 pipeline/post_stage_c/run.py --all --dry-run
python3 pipeline/post_stage_c/run.py --validate
python3 pipeline/post_stage_c/run.py --validate-eligibility
```

Live execution uses `--case-id CASE_ID` or `--all`. Existing authoritative records are validated and reused. Corpus execution is checkpointed and resumable. Final eligibility is represented by `post-stage-c-eligibility-v2`; `--resolve-eligibility` atomically derives the ledger from authoritative Stage C and Post-C records after complete in-memory validation.

Scientific records declare `post-stage-c-reconstruction-v4` and `post-stage-c-git-lineage-v4`.
