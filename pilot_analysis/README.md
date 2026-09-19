# Pilot Analysis

`cases/` holds lightweight, researcher-generated forensic analyses of
selected pilot cases. Complete the individual analyses before producing
cross-case synthesis in `synthesis/`. These files are interpretations
for exploratory method discovery, not raw historical source data. Keep
them separate from `cases/raw/`.

`pilot_analysis/` is not reconstruction-safe evidence and must never be
consumed as input by the reconstruction pipeline. Researchers may inspect
downstream history here to understand retrospectively what mattered.
Any repository evidence later proposed for reconstruction must
independently have been available by the fixed conversation-start cutoff
`tC`. See `protocols/pilot_case_selection_and_extraction.md` for the
exploratory procedure and temporal rule.
