# Stage C V2 Phase 2 Summary v1

Phase 2 contains two development cases and is not a performance estimate.
Neither case has an accepted V1 Stage C scientific result, so the comparisons
below describe V1 Stage B representation to V2 Stage C selection.

## CASE_5A3A043A5011

- Impact category: `earlier_response_addition`
- Accepted output: `cases/conversations/CASE_5A3A043A5011/stage_c_extraction_v5.json`
- Output SHA-256: `8c5084c136868670d443bb6686cc4587701e00d4c1dfe051f82de3de22dd7d3f`
- Run ID: `canonical_v5_20261001T081233Z`
- Human audit: `accepted`
- Selected response/target: `turn_000003` / `turn_000002`
- Selected GTC count: 3
- Family: `FGF_11f134041d770eecbd370d4b`
- Boundary: `exclusive_before:turn_000003`
- `tC`: `2023-08-13T08:05:19.653407+00:00`
- `tFG`: `2023-08-13T08:05:30.672917+00:00`
- C/S/V counts: 4 / 2 / 1

The three distinct response-local candidates are alternative implementations
of stable function identity for `visibilitychange` listener registration and
removal. The earliest V1 Stage B represented response was turn 5 and concerned
a later Promise-returning handler and TypeScript/ESLint refinement.

## CASE_E8F12807DBDC

- Impact category: `earlier_response_addition`
- Accepted output: `cases/conversations/CASE_E8F12807DBDC/stage_c_extraction_v5.json`
- Output SHA-256: `266f564be4e3400ab082793a8d476f607ac5fec96dc8e439c414095c5d33af9a`
- Run ID: `canonical_v5_20261001T081744Z`
- Human audit: `accepted`
- Selected response/target: `turn_000003` / `turn_000002`
- Selected GTC count: 4
- Family: `FGF_3b0a38932949841dcf581917`
- Boundary: `exclusive_before:turn_000003`
- `tC`: `2023-11-29T15:29:58.598890+00:00`
- `tFG`: `2023-11-29T15:30:05.280608+00:00`
- C/S/V counts: 1 / 1 / 0

The four distinct response-local candidates are type-specific examples of
TypeScript null-or-empty checking. The earliest V1 Stage B represented
response was turn 5 and concerned a later `!array`-specific follow-up.

These cases illustrate that multiple candidates in one response can be
semantically grouped into one response-local first-generation family. They do
not establish that the method handles every multi-candidate response correctly.

## API accounting

- 5A: 2 logical invocations, 14,557 recorded tokens, no application retry or controlled rerun.
- E8: 2 logical invocations, 5,820 recorded tokens, no application retry or controlled rerun.
- Phase 2: 4 logical invocations and 20,377 recorded tokens.
- SDK retry allowance per invocation: 2.
- Transport-level HTTP attempts were not observed and are not inferred.

No remaining recovered-zero case was executed during Phase 2.
