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

Inspect the same-eight-case v2 pilot without network or Git operations, then use the
no-argument command for the explicitly authorized live run:

```bash
python3 -B pipeline/post_stage_c/run_pilot_v2.py --check-config
python3 -B pipeline/post_stage_c/run_pilot_v2.py --dry-run
python3 -B pipeline/post_stage_c/run_pilot_v2.py
```

The plan is stored in `cases/manifests/post_stage_c_reconstruction_pilot_v2.csv`. Live execution is sequential and resumable: a completed result is atomically persisted before its row becomes `executed=true`, and completed rows are skipped on resume. Execution status does not imply scientific resolution. V2 records use `cases/reconstruction/<case_id>/historical_state_acquisition_v2.json` and `data/derived/historical_information/<case_id>/historical_information_boundary_v2.json`; v1 files are never overwritten. The runner retains competing claims, applies B1–B5, and materializes only after authoritative identity is established. Transport retries are limited to the initial attempt plus two infrastructure retries; semantic ambiguity is never automatically retried.

## Post-C v3 B1–B2 checkpoint

`post-stage-c-reconstruction-v3` asks whether `R_i(tFG)` can be reconstructed from information actually supplied or explicitly referenced before first generation, together with immutable Git relationships, while present-day systems serve only retrieval and validation. The target remains the historically justified repository revision representing the project baseline relevant to the focal task at `tFG`.

| Route | Question | Primary source | v3 status |
|---|---|---|---|
| B1 | Was the revision directly identified before generation? | Authoritative Stage C admissible prior turns | Active; establishes the starting revision |
| B2 | Can Git derive the baseline from the B1 revision? | Immutable Git relationships | Active only after B1 and only when semantics require derivation |
| B3 | Did a historical project system record it? | Historical CI/branch/PR/task metadata | Not used; future versioned extension |
| B4 | Is there an independent historical clue requiring validation? | Independent historical project records | Not used; future versioned extension |
| B5 | What can today's systems check without rewriting history? | Current provider/Git/repository systems | Supporting only |

B2 cannot select its own input and does not automatically select a parent. B5 cannot establish `R_i(tFG)` or start B2. PatchPrompt/PR-sharing data remains conversation acquisition, case identity, correspondence, and corpus provenance; its eventual PR commit lists and archive timestamps are not v3 repository-state evidence. V3 creates no `archive_derivation_leads_v3.json`. No B route is scored.

The same-eight v3 plan is independent and starts with zero executed rows. These commands inspect it offline; the final command is the separately authorized live pathway:

```bash
python3 -B pipeline/post_stage_c/run_pilot_v3.py --check-config
python3 -B pipeline/post_stage_c/run_pilot_v3.py --dry-run
python3 -B pipeline/post_stage_c/run_pilot_v3.py
```

Check and dry-run perform no provider requests, Git remote operations, or model calls. Live execution writes v3 files only and updates a row only after both outputs are atomically persisted. Stage F2 must consume the fixed `R_i(tFG)` and may not rediscover or replace it.
