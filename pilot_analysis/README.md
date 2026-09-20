# Pilot Analysis

`pilot_analysis/cases/` holds lightweight, researcher-generated forensic analyses of
selected pilot cases. Complete the individual analyses before producing
cross-case synthesis in `synthesis/`. These files are interpretations
for exploratory method discovery, not raw historical source data. Keep
them separate from `cases/raw/`.

`pilot_analysis/` is not reconstruction-safe evidence and must never be
consumed as input by the reconstruction pipeline. Researchers may inspect
downstream history here to understand retrospectively what mattered.
Any repository evidence later proposed for reconstruction must
independently have been available by the current first-generation cutoff
`tFG`; preserve `tC` separately. Validated, versioned conversation-side
records belong in `conversation/` and precede repository forensic
analysis. See `protocols/pilot_case_selection_and_extraction.md` for the
exploratory procedure and temporal rule.

`src/developer_intent/first_generation.py` prepares a draft from a
preserved conversation plus explicit, independently preserved artifact
references; it does not discover artifacts from prompt text. Reviewers
validate the boundary and supplied items before `freeze_record` emits a
versioned record. Keep each frozen revision under
`conversation/<case_id>/record_<version>.json`; retain older revisions.
`src/developer_intent/temporal_evidence.py` evaluates bounded repository
items against both anchors and permits a SAFE result only under the
current `tFG` rule. No selected pilot raw packages or frozen records
have been created yet.
