# Protocol v5 screening

Stage A starts with all PatchPrompt rows whose `Outcome_Class` is PA or PN. The source CSV is a candidate index, not a complete case source. Screening records integrity, availability, and processability. Size, prompt count, word count, and commit count are descriptive only. `PR_Size` is inherited metadata and unused. See [the protocol](../../protocols/experiment_protocol.md).

V5 outputs are `cases/manifests/screened_PA_PN_cases.csv`, `eligible_PA_PN_cases.csv`, and `stage_a_summary.md`, marked `dir-screening-v4` / `dir-tfg-v2`. Former `screened_cases.csv`, `selection_summary.md`, `pilot_cases.csv`, and smoke files are `dir-screening-v3` historical material recoverable from Git history. Preserve the ignored old retrieval cache as external source material; do not use historical eligibility judgments in a v5 run.

## Safe local checks

Python 3.9.6 or newer is required. `.env` is ignored by Git. `GITHUB_TOKEN` remains optional for public GitHub API access; the configuration check never prints its value.

```bash
python3 pipeline/screening/run.py --check-config
make test
```

For an authorized future v5 run, `--live` retrieves sources into `data/intermediate/screening_v5/cache/`; `--limit N` uses separate `screening_v5/smoke_N*` paths. The CLI guards named legacy outputs and the old cache against live writes. Overrides include `--source`, `--output`, `--eligible-output`, `--summary`, `--cache-dir`, `--evidence-dir`, `--timeout`, `--retries`, `--archive`, `--no-archive-fallback`, and `--refresh`. Environment defaults use `DIR_V5_SCREENING_CACHE_DIR` and `DIR_V5_SCREENING_OUTPUT`.
An existing v5 manifest or summary also blocks a new run before retrieval; archive it explicitly before a rerun. The HTTP cache can still support acquisition without replacing a research output.

Stable DIR IDs derive from source `Case ID` without encoding outcome or role. Verified GitHub redirects preserve source and canonical PR URLs. Retrieval and parsing failures stay explicit. Archive fallback requires matching PR and conversation identities; summary-only archive records do not establish completeness. Date-only values stay date-only. Source bodies and parsed evidence are intermediate audit material, not supplied-C/S/V input.

Positive processability judgments require `processability.source` in case evidence JSON. Unreviewed first-generation boundary, PR/conversation match, project-history access, or historical-state reconstructibility stays pending. Full evidence discovery occurs after conversation freeze and the discovery/held-out split.

The former pilot-selection utility and manifest are retained only in Git history; they are not part of the Protocol v5 workflow.
