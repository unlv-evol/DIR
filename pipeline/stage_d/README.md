# Stage D

Stage D draws a reproducible PA/PN-stratified sample from the final eligible
population and prepares two blinded, initially blank human-review packages.
It validates Stage C conversation extraction only. It does not validate or
expose Post-C reconstruction results.

Run, in order:

```text
python3 pipeline/stage_d/run.py --check-config
python3 pipeline/stage_d/run.py --generate-sample
python3 pipeline/stage_d/run.py --prepare-review
python3 pipeline/stage_d/run.py --prepare-review-html
python3 pipeline/stage_d/run.py --validate
```

The fixed integer seed is `20261005`. Case IDs are sorted lexicographically in
each stratum. Domain-separated SHA-256 derivations from that one seed initialize
the PA draw, PN draw, and final blinded review-order shuffle. Each draw uses
Python's seeded `random.Random.sample` without replacement.

The internal manifest records the configured Git remote and repository-relative
evidence paths. After review, commit, and push, the checkpoint commit SHA can be
combined with those values; files do not attempt to contain their own commit.

Each reviewer package intentionally versions both `stage_d_review.csv` and
`stage_d_review.xlsx`. The CSV is the canonical machine-readable annotation
representation. The XLSX is the frozen human-review instrument generated from
that CSV, adding dropdown controls, clickable source URLs, formatting, and
review instructions without replacing the CSV's scientific authority.

Each reviewer-safe JSON has a deterministic, standalone HTML companion in the
same `cases/` directory. The JSON remains the structured evidence authority;
the HTML presents the same fields for human reading with embedded styling and
no network dependencies. The XLSX `case_details` cell displays the canonical
JSON path and links to the corresponding relative HTML page. Regenerate these
pages with `--prepare-review-html`; generation reads only the reviewer-safe
JSON files referenced by the canonical reviewer CSV.

Generate the workbooks with the preserved `build_review_workbooks.mjs` script
in an environment providing `@oai/artifact-tool`, then run `--validate` before
committing them. Completed human annotations must later be stored as versioned
review outputs; they must not erase this committed blank checkpoint.
