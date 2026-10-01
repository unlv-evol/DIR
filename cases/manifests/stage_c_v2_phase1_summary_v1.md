# Stage C V2 Phase 1 Summary v1

Phase 1 contains two migration-impact development cases. These results record
representation and extraction behavior for the two cases and do not establish
general scientific performance.

## CASE_C482978A9FE9

- Migration class: `earlier_response_addition`
- Accepted output: `cases/conversations/CASE_C482978A9FE9/stage_c_extraction_v5.json`
- Output SHA-256: `5d77d2dbe28e6945a6bc2de237004afa8287b57aa34339e2776aab64c003da8a`
- Run ID: `canonical_v5_20261001T074347Z`
- Human disposition: `ACCEPT_V2_RESULT`
- V1 selected response/target: `turn_000006` / `turn_000005`
- V2 selected response/target: `turn_000004` / `turn_000003`
- V1 `tFG`: `2023-09-11T00:05:43.858276+00:00`
- V2 `tFG`: `2023-09-11T00:04:52.102398+00:00`
- V2 family: `FGF_315253bfd5414dec26aa573b`

The broader Stage B V2 representation exposed an earlier directly responsive
command family selected by Stage C V2.

## CASE_AADA2C787EEE

- Migration class: `recovered_zero`
- V1 candidates: `0`
- V1 Stage C status: `unresolved`
- V2 candidates: `22`
- Accepted output: `cases/conversations/CASE_AADA2C787EEE/stage_c_extraction_v5_aada_v2_retry_01.json`
- Accepted output SHA-256: `97e79daae2f15322006e385bc57227101fc8b259e33920e56c3f2a35a0048451`
- Run ID: `aada_v2_retry_01`
- Human disposition: `ACCEPT_CONTROLLED_RERUN`
- V2 selected response/target: `turn_000005` / `turn_000004`
- V2 family: `FGF_9fd4c65079a6bcc0948585b4`
- V2 `tFG`: `2023-07-17T12:56:44.032860+00:00`

The first V2 attempt failed because Pass 2 returned structurally incomplete
provenance arrays. Its failed record and non-authoritative diagnostic remain at:

- `cases/conversations/CASE_AADA2C787EEE/stage_c_extraction_v5.json`
  (`36e3ec0045cc52f7608817046abb02c1ed89062909a46a6db36efe9efe24326f`)
- `cases/conversations/CASE_AADA2C787EEE/stage_c_extraction_v5.diagnostic.json`
  (`18dd66c78481f30aab19d5ef10d16518a09c6790d7083554deaff0d361733b3b`)

The accepted controlled rerun used an independent invocation with the same
prompt, schema, validator, Stage B package, and methodology. Rejected C/S/V
content was not repaired or promoted.

## API accounting

- C482: 2 logical model invocations; 9,535 total tokens; no controlled rerun.
- AADA canonical attempt: 2 logical model invocations; 75,674 total tokens.
- AADA retry 01: 2 logical model invocations; 75,755 total tokens; one controlled rerun.
- Phase 1 total: 6 logical model invocations and 1 controlled rerun.
- Application-level retries: 0.
- SDK retry allowance per invocation: 2.
- Transport-level HTTP attempts were not observed and are not inferred.

Phase 2 cases were not executed.
