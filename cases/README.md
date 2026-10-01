# Cases

`cases/manifests/` holds screening, eligibility, validation-sample, and later discovery/held-out roles as metadata. Stable case identity does not change with role. Protocol v5 manifests use versioned names and fields.

`cases/conversations/<case_id>/` is the proposed location for isolated conversation-only packages and versioned validated records. Conversation-side supplied-C/S/V extraction receives no PR/repository identity, PA/PN outcome, project history, or eventual implementation.
The source archive preserves retrieved bytes and safe retrieval provenance. The lossless normalized conversation preserves original ordered records, tool traces, first-generation responses, and later turns. The Stage C model view is derived from it and receives only conversation-addressed turns and temporal/artifact provenance. PR identity stays in a separate restricted case-linkage record tied by the same neutral Case ID. Frozen records retain separate procedure and case human-validation statuses; unsampled does not mean individually validated.
The one-case Stage B command writes linkage under `cases/manifests/linkage/`, source archive under `cases/raw/<case_id>/`, and normalized/model-view/status files under `cases/conversations/<case_id>/`. Inspect `package_status.json` before using a model view; only `complete` marks a validated package. See [`pipeline/extraction/README.md`](../pipeline/extraction/README.md).

`cases/raw/<case_id>/` remains historical audit material and may expose future or outcome information. It is not reconstruction-safe. Historical project indexes retain reproducible boundary references and defer large payload materialization. `safe/reconstruction/<case_id>/` holds admitted inputs; `sealed/evaluation/<case_id>/` holds outcome material and the integrated implementation until evaluation.

`cases/reconstruction/<case_id>/` is reserved for versioned researcher-side Post-Stage-C acquisition records. These records document attempts to reconstruct the historically evidenced focal-PR base state and are not Stage C inputs or automatically SAFE evidence. The historical project-information index remains separate under `data/derived/historical_information/<case_id>/`.

See [the architecture](../docs/architecture.md) and [protocol](../protocols/experiment_protocol.md).

`cases/manifests/case_mapping.csv` is a generated, researcher-only Case ID / PR / PA-PN mapping. It is separate from richer `linkage/*.json` records and never enters the Stage C model view.
