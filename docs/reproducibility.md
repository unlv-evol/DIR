# Reproducibility

The revised authoritative Word Protocol v5 (`Developer_Intent_Reconstruction_Experiment_Protocol_v5 (2).docx`) governs the method. Protocol v5 uses methodology `dir-tfg-v2` and current screening schema `dir-screening-v9`. Record source CSV checksum, stable case/source IDs, retrieval and parsing status, processability source, methodology/schema versions, validation and freeze versions, split seed/stratum/assignment once defined, code commit, configuration version, source artifact IDs, both temporal anchors and their precision/status/source, historical boundary SHA and references, and checksums for frozen outputs. Record model/version and generation settings at generation time.

Stage A intermediate outputs use `data/intermediate/screening/`; methodology and schema versions are recorded in the outputs. Preserve acquired source material and retrieval provenance. Do not silently overwrite existing research outputs or frozen records. Reproduce SAFE inputs without exposing SEALED future or outcome information. See [the protocol](../protocols/experiment_protocol.md).

Within Stage A, record source-linkage provenance separately from manual semantic correspondence. Preserve one versioned `dir-correspondence-review-v1` record for every candidate/processable case reaching manual screening; verify identity binding before finalizing eligibility. Stage D remains the approximately 30% extraction-validation sample.

The deterministic `stage_a_correspondence_review.csv` is a restricted interchange artifact. Preserve its `dir-correspondence-review-csv-v1` version, evidence policy/reference, and manual provenance during import. Canonical per-case JSON remains authoritative; identical re-import is idempotent and conflicting records fail closed.

Validate Stage A CSVs by checking exact headers, explicitly parsing blank/boolean/integer/temporal cells into logical records, then applying the versioned contracts and cross-field checks in `schemas/` and `src/developer_intent/stage_a_contracts.py`. `pipeline/screening/validate_contracts.py` validates existing outputs without retrieval. A blank eligible field for `pending_resolution` remains null, not false; an explicit `unresolved` judgment remains unresolved.

Retain restricted PR/conversation review records with reviewer, method, time, version, rationale, and evidence reference. Retain Git history access mechanism, tested repository/commit, result, and failure reason separately from PR API retrieval and later historical-state reconstruction.
