# Record contracts

Protocol v5 currently uses methodology `dir-tfg-v2`. A schema version identifies a **record contract**, not a change to that methodology. CSV values remain strings until explicitly parsed. Current Stage A contracts are:

| Artifact / record | Contract file | Record version | Methodology | Producer | Validation entry point |
| --- | --- | --- | --- | --- | --- |
| Screened and eligible CSV logical rows (64 ordered columns) | `dir_screening_v9.schema.json` | `dir-screening-v9` | `dir-tfg-v2` | `src/developer_intent/screening.py` | `stage_a_contracts.validate_csv(path, "screening")` |
| Researcher-only case mapping CSV logical rows (7 ordered columns) | `dir_case_mapping_v1.schema.json` | `dir-case-mapping-v1` | Stage A under `dir-tfg-v2` | `src/developer_intent/case_mapping.py` | `stage_a_contracts.validate_csv(path, "mapping")` |
| Restricted correspondence review JSON | `correspondence_review_v1.schema.json` | `dir-correspondence-review-v1` (schema `x-schema-version`); implemented `version` is the review-record revision | Stage A under `dir-tfg-v2` | manual case-validity screening for candidate/processable cases | `stage_a_contracts.validate_correspondence_review(review, source_row)` |

`stage_a_correspondence_review.csv` is a `dir-correspondence-review-csv-v1` interchange interface, not a replacement scientific contract. Its importer validates identity and manual provenance, then emits the canonical v1 JSON above. No screening, mapping, methodology, or canonical review schema version changes are introduced by this interface.

`stage_a_contracts.validate_stage_a_outputs(screened, eligible, mapping)` also checks that the eligible file is the confirmed-eligible subset and mapping identities agree with screened rows. The read-only CLI is `pipeline/screening/validate_contracts.py`. A header-only eligible CSV is valid when no case is confirmed eligible.

## CSV normalization

The validator checks exact headers and column order. Every column is required; a field is **nullable** only where its logical schema type includes `null`. An empty nullable cell becomes Python `None`; explicit `unresolved` stays the string `unresolved`. Only lowercase `true` and `false` become booleans. Nonnegative base-10 integer strings become integers. Timezone-aware ISO timestamps become `datetime`; `conversation_start` becomes `date` or timezone-aware `datetime` according to `temporal_precision`. A missing date is never given a time. Identifiers, canonical GitHub PR URLs, conversation share IDs, and tested SHA/object IDs are checked explicitly. Original source URLs remain strings even when malformed so excluded cases retain the source evidence of an invalid link.

The JSON Schema files describe the JSON-compatible form of each typed logical record. The standard-library validator converts parsed dates/times back to ISO strings for field validation and enforces cross-field invariants separately. It supports the schema keywords used here (`type`, `required`, `additionalProperties`, `const`, `enum`, `minLength`, `minimum`, `pattern`, and timezone-aware `date-time`). The review schema's positive-source restriction is also enforced by the existing correspondence implementation. These validators do not infer a scientific judgment from a blank cell.

`frozen_conversation_v1.schema.json` and `repository_evidence_v1.schema.json` are **legacy `dir-tfg-v1` contracts**. They do not validate current Protocol v5 Stage C–E or later outputs. No current Stage C/E/F/G/I/J/K/L schema is asserted here.
