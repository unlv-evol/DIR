# Post-Stage-C historical processability and eligibility

This workflow consumes only rows marked `eligible_for_post_c_scientific_resolution = true` in `cases/manifests/stage_c_post_resolution_authority.csv`. It resolves the authoritative Stage C boundary criterion offline and initializes the remaining historical-state criterion without making a scientific eligibility decision.

Historical `post-stage-c-reconstruction-v1` defined its target as the focal-PR base applicable at `tFG`; the eight executed v1 records retain that meaning. Current `post-stage-c-reconstruction-v2` establishes only `R_i(tFG)`: the historically justified repository revision representing the development baseline relevant to the focal task. Complete `H_i(tFG)` is constructed later in Stage F.

V2 uses B1 direct historical baseline evidence, B2 immutable derivation, B3 historically versioned project/task/branch/eligible-PR metadata, B4 archived derivation leads, and B5 supporting-only current information. B4 needs explicit validation and B5 cannot establish authority. Historical linkage and temporal applicability precede Git materialization. A PR created after `tFG` is unavailable as a historical component but does not automatically fail repository reconstruction.

Initialize or reproduce the two manifests without network, Git, provider, or model calls:

```bash
python3 -B pipeline/post_stage_c/initialize.py
python3 -B pipeline/post_stage_c/initialize.py --validate-only
```

The command writes `post_stage_c_eligibility.csv` and the proposed eight-case pilot manifest. It does not create acquisition results, execute the pilot, update Stage A, make a final eligibility decision, or begin Stage D.

The live pilot runner is deliberately restricted to the frozen eight-case manifest and refuses an already executed manifest:

```bash
python3 -B pipeline/post_stage_c/run_pilot.py --check-config
python3 -B pipeline/post_stage_c/run_pilot.py --dry-run
python3 -B pipeline/post_stage_c/run_pilot.py
```

It applies current provider metadata only as Level 4 supporting evidence. When qualifying historical target-identity evidence is absent, it persists an unresolved record and does not begin Git materialization. Transport retries are limited to two after the initial request, and credentials are neither printed nor serialized.

Prepare and inspect the same-eight-case v2 pilot without network or Git operations:

```bash
python3 -B pipeline/post_stage_c/run_pilot_v2.py --check-config
python3 -B pipeline/post_stage_c/run_pilot_v2.py --dry-run
```

The plan is stored in `cases/manifests/post_stage_c_reconstruction_pilot_v2.csv`; all rows remain `executed=false`. Live v2 acquisition is deliberately disabled at this checkpoint. Future execution is sequential, retains competing claims, applies B1–B5, and materializes only after authoritative identity is established. Transport retries are limited to the initial attempt plus two infrastructure retries; semantic ambiguity is never automatically retried.
