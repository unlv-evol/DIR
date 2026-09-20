# Pilot screening CLI

Requires Python 3.9.6 or newer. No third-party dependencies are needed.
The source CSV is an index, not a complete raw-case dataset. Screening
uses only PA/PN as the generated-code candidate population. PA versus
PN status, `PR_Size`, adoption depth, and merge outcome never determine
eligibility.
Numeric thresholds are development-pilot workload limits. The manifest
reports `scientific_data_eligible` and `pilot_manageability_eligible`
separately; a failed workload limit receives
`pilot_manageability_exclusion`. Screening preserves conversation start
(`tC`) but does not infer first-generation `tFG` before raw artifact
preservation. See the pilot protocol, §§2 and 9.

## Local setup

```bash
cp .env.example .env
# Edit .env locally; leave GITHUB_TOKEN empty for unauthenticated public access.
python3 pipeline/screening/run.py --check-config
python3 -m unittest discover -s tests/unit -v
```

`.env` is ignored by Git. `GITHUB_TOKEN` is optional for public PRs but
recommended for the full run because unauthenticated GitHub API limits
are lower. It may be required for private PRs. Public ChatGPT share
retrieval does not use ChatGPT credentials.

## Live smoke tests and full run

```bash
python3 pipeline/screening/run.py --live --limit 1
python3 pipeline/screening/run.py --live --limit 5
python3 pipeline/screening/run.py --live
```

Limited runs write to `data/intermediate/screening/smoke_N.csv` and a
matching summary. The full run writes
`cases/manifests/screened_cases.csv` and
`cases/manifests/selection_summary.md`. Review the 1-case cache/output
before the 5-case run, and inspect both before the full run. The
summary also reports the reviewed pilot selection when the pilot manifest
exists. Limited smoke runs remain screening-only.

## Reviewed pilot selection

`cases/manifests/pilot_cases.csv` records 30 selected pilot/development
cases, their screening measures, the same persisted secondary fields,
and a source-observable reason for each
choice. The choices were reviewed for C/S/V and conversation/task
variation; no automatic ranking score or PA/PN outcome balance is used.
Generated-artifact counts and revision relationships are established
after raw extraction, not assumed from the screening cache.

The `dir-screening-v3` CSV also persists secondary characteristics for
every candidate. `conversation_turn_pattern` is based on complete
visible developer turns. The `prompt_*_signal` fields are conservative
lexical cues for identifiers, paths, code fragments, errors/logs,
tests/assertions, and URLs in those turns. `detected` has a literal
matched cue and developer-turn index in
`secondary_characteristics_evidence`; `not_detected_by_rule` means only
that the rule found no cue, not that the characteristic is absent.
Unparsed conversations use `unavailable`. `help_seeking_context_cues`
are lexical leads, not assigned task categories. Mostly behavioral
language, actual help-seeking context, link-sharer role, and the number
or revision pattern of generated artifacts remain `not_assessed` until
their respective source evidence is reviewed or raw artifacts are
preserved. These fields do not change screening eligibility or pilot
membership.

After editing the pilot manifest or rerunning screening, validate it and
refresh the selected-pilot section of `selection_summary.md` with:

```bash
make pilot-summary
```

The command rejects duplicate, ineligible, or stale case records. A full
screening rerun also validates the existing pilot manifest and includes
the selected-pilot section in the summary; limited smoke runs leave the
selection unchanged. The manifest records study role without changing
case identity. Raw extraction and first-generation analysis follow this
selection stage.

HTTP source bodies and parsed conversations are cached under
`data/intermediate/screening/cache/`. Successfully retrieved resources
are reused on the next run; use `--refresh` to fetch them again. A
partially failed run keeps successful cache entries. The cache is
intermediate research material, never SAFE reconstruction input. Do
not commit cached source material without a separate data-management
decision.

Supported overrides: `--source`, `--output`, `--summary`,
`--cache-dir`, `--evidence-dir`, `--timeout`, `--retries`, `--limit`,
`--refresh`, `--archive`, `--no-archive-fallback`, and `--check-config`.
Equivalent non-secret defaults can
be set in `.env`: `DIR_HTTP_TIMEOUT`, `DIR_HTTP_RETRIES`,
`DIR_SCREENING_CACHE_DIR`, and `DIR_SCREENING_OUTPUT`. CLI overrides
take precedence over environment values, which take precedence over
`.env` values and built-in defaults. Configuration checking makes no
network requests and never prints the token value.

DIR case IDs are deterministic SHA-256 prefixes of inherited PatchPrompt
`Case ID` values; they do not encode PA/PN status or study role. The
summary records the source CSV checksum. Integrity statuses are `ok`,
`unresolved`, `duplicate`, and `conflict`. Duplicate and conflicting
records stay in the manifest for review.
The manifest keeps the source `pr_url` and the API's `canonical_pr_url`.
A changed repository URL is accepted only when GitHub's API redirect,
repository ID, canonical repository name, and PR number agree;
`pr_redirect_verified` records that check. Other URL mismatches remain
integrity conflicts.

Each source has a retrieval status. A failed ChatGPT request or an
unsupported share-page format leaves the conversation and its counts
unresolved; it is never converted into an empty conversation. The
parser accepts only a verifiable ordered structured conversation.
It supports structured JSON, `__NEXT_DATA__`, and the flattened React Router
payload observed in cached public share pages.
Tool-directed assistant calls and tool replies are excluded from visible
conversation-turn and word counts; developer turns and assistant replies
addressed to the conversation remain in order.
Parsed evidence retains the full source conversation structure, ordered raw
records, and a tool trace with source positions; mixed assistant content
keeps visible text while recording tool parts separately.
Date-only values remain date-only; no time is fabricated. GitHub 403,
404, rate-limit, and network failures likewise remain explicit and do
not imply that the historical PR did not exist. Blank manifest measures
mean not established, not zero. All known exclusion reasons are
retained. Commit count above 10 is recorded as a preference failure,
not an eligibility exclusion.

The HTTP cache contains retrieved source bodies. The parsed evidence
cache is under `cache/evidence/<PatchPrompt Case ID>.json`. If you have
separately verified source evidence, supply `--evidence-dir` with JSON
files keyed by source Case ID. Each can contain `pr`, a complete `files`
list, and `conversation` with original URL, date/timestamp precision,
`complete`, and ordered `turns` with `role` and `text`. Preserve
provenance for any manually supplied evidence. The CLI does not infer
conversation completeness or a conversation date from the URL alone.

If a public share fails to parse, the CLI also checks the local PatchTrack
`data/raw/allPullRequestSharings.zip` archive. It requires both the source
PR identity and share ID to match. Saved share-page HTML is parsed with
the same conversation parser; conflicting historical snapshots are not
selected automatically. Summary-only archive records remain unresolved
because they do not establish completeness or first-prompt time. The
manifest records `conversation_source` and `conversation_archive_status`;
the evidence JSON retains archive member and SHA-256 provenance. Run the
CLI without `--live` to apply this fallback to prior failed evidence
without making network requests. Use `--archive` for a different archive
path or `--no-archive-fallback` to skip it.
