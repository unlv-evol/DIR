# Post-Stage-C Historical Target Evidence and Anchor Audit

## Status and scope

This is a descriptive audit artifact, not a scientific authority record. It was produced entirely from retained repository files. It did not rerun the eight-case pilot, acquire repository data, change eligibility, or begin Stage D.

The preserved pilot remains: 8 attempted, 0 `yes`, 0 `no`, and 8 `unresolved`. The Post-C population remains 111 processable cases, all pending scientific eligibility.

## Retained offline source inventory

| Source | Producer and representation | Time represented | Relevant fields | Strongest legitimate use and limitation |
|---|---|---|---|---|
| `data/raw/final_analysis_dataset_from_patchprompt_study.csv` | PatchPrompt analysis dataset; raw inherited candidate index | Dataset snapshot time is not recorded in the file | Source case ID, PA/PN, PR URL, conversation URL, scores and inherited descriptive fields | Candidate identity and indexing only. It has no base/head SHA, refs, parents, or PR event history. |
| `data/raw/allPullRequestSharings.zip` and extracted `data/raw/allPullRequestSharings/*.json` | PatchTrack/PatchPrompt PullRequestSharing snapshots; raw source records | Collection-like timestamps appear in filenames from 2023-07-27 through 2023-10-12, plus a manual 2024-02-18 file; the JSON files contain no independent collection-time field | Repository, PR number/URL, PR created/updated/closed/merged times, PR commit SHA lists in some records, conversation sharing data | Later PR snapshots and possible Level 2 derivation leads. They contain no base SHA, parent SHA, base/head ref, or event history. A later commit list does not itself identify the applicable base at `tFG`. |
| `data/intermediate/screening/cache/http/*.body` plus `*.json` | Stage A raw GitHub pull/file responses and cache status | Present-day Stage A retrieval; exact retrieval timestamp is not retained in the cache metadata | Current pull response includes base/head SHA and refs, creation and lifecycle timestamps; file endpoint includes changed-file metadata | Level 4 present-day PR metadata only. Cache metadata records HTTP status/final URL, but no retrieval timestamp. |
| `data/intermediate/screening/cache/evidence/<source_case_id>.json` | Stage A transformed facts | Same current-provider state as the cached response | Canonical PR identity, `created_at`, current `base_sha`, `head_sha`, branches, counts, plus Git access result | Level 4 candidate identity. `history_access` is a separate present-day Level 5 materializability probe. |
| `cases/manifests/screened_PA_PN_cases.csv` and retained Stage A run copies | Stage A transformed manifests | Current-provider state at Stage A execution | `project_history_access_object`, repository, PR identity, access mechanism/status | Repeats the Stage A candidate and access result; it is not an independent historical claim. |
| `cases/manifests/case_mapping.csv`, `linkage/*.json`, correspondence reviews/evidence | Stage A administrative mapping and restricted human-review provenance | Review/import time, not historical repository state | Stable case/source/PR/conversation identity and correspondence provenance | Identity linkage only. These records do not establish historical base state. |
| `cases/raw/*/conversation_source_archive.json` and `cases/conversations/*` | Stage B conversation source, normalization, and model-view packages | Conversation event times and package/import provenance | Conversation turns, timestamps, generated-content candidates | Conversation evidence only. They contain no independently established repository snapshot. |
| `cases/reconstruction/<case_id>/` and `data/derived/historical_information/<case_id>/` for the eight pilot cases | Preserved Post-C pilot records | Current-provider observation with explicit unresolved temporal relation | Sanitized current PR metadata and Level 4 target claims | Immutable pilot execution history. All eight remain supporting-only Level 4 observations. |
| Legacy schemas and repository-evidence documentation | Contract definitions, not populated observations | Not applicable | Expected historical target/provenance fields | Cannot supply evidence merely because a field exists in a schema. |

No retained source contains a qualifying direct historical focal-PR base snapshot (Level 1). No retained source contains a parent relationship already sufficient to derive the base applicable at `tFG` (completed Level 2), and none contains a contemporaneous base-SHA claim suitable for Level 3.

## What Stage A `base_sha` represents

`src/developer_intent/screening_github.py::retrieve_pr` requests the GitHub pull endpoint and assigns `raw["base"]["sha"]` to `pr.base_sha`. Stage A stores the transformed result in `data/intermediate/screening/cache/evidence/<source_case_id>.json` and copies it to `project_history_access_object` in the screened manifest. The raw response is retained in the HTTP body cache.

The exact retrieval timestamp is absent from the cache metadata. The value therefore represents the base SHA reported by the pull endpoint at the Stage A retrieval-time state. It is not labeled or proven as the PR-creation base. A PR base can change during its lifetime, for example through base-branch changes or retargeting. `screening_checks.py::history_access` then fetches that known SHA into a temporary bare repository and verifies its object type. This proves present access to a commit object only; it does not establish that the SHA was the focal PR base at `tFG`.

## PR existence at `tFG`

The classification compares the retained provider `pr.created_at` event timestamp with authoritative Stage C `tFG`. All 111 rows have timestamp precision sufficient for the comparison.

| Stratum | Existed at `tFG` | Not yet created at `tFG` | Unresolved | Total |
|---|---:|---:|---:|---:|
| PA | 47 | 21 | 0 | 68 |
| PN | 35 | 8 | 0 | 43 |
| **Overall** | **82** | **29** | **0** | **111** |

There were 82 strictly pre-`tFG` PR creation times, 82 at-or-before `tFG`, and 29 after `tFG`; no exact equalities occurred.

## Temporal distribution

`delta = PR created_at - tFG`. Percentiles use linear interpolation at `(n - 1)p` (the common Type 7 definition).

| Population | n | Minimum | 25th percentile | Median | 75th percentile | Maximum |
|---|---:|---:|---:|---:|---:|---:|
| All | 111 | -176d 04:31:00.356 | -3d 23:29:00.051 | -00d 05:39:40.869 | +00d 00:03:20.833 | +100d 03:12:56.029 |
| PR created after `tFG` | 29 | +00d 00:03:14.426 | +00d 00:19:00.898 | +00d 01:27:50.662 | +00d 22:57:50.607 | +100d 03:12:56.029 |

PA has 47 before and 21 after; PN has 35 before and 8 after. The per-case seconds and exact timestamps are in the audit CSV.

## Eight-case pilot audit

| Case | Stratum | Repository / PR | `tC` | `tFG` | PR `created_at` | Delta | Retained archive evidence | Coverage |
|---|---|---|---|---|---|---:|---|---|
| `CASE_97AFC2022473` | PA | equinix/metal-cli #405 | 2023-12-13T16:35:21.465610+00:00 | 2023-12-13T16:35:54.603014+00:00 | 2023-12-11T20:48:11Z | -1d 19:47:43.603 | One later manual snapshot; no commit SHAs | Level 4 only |
| `CASE_F93FFAA22B9B` | PA | dotCMS/core #25432 | 2023-07-07T21:09:50.169989+00:00 | 2023-07-07T21:10:15.086839+00:00 | 2023-07-06T15:28:20Z | -1d 05:41:55.087 | Nine later snapshots; 38 unique PR commit SHAs | Potential Level 2 lead |
| `CASE_85AD863F8290` | PA | alshedivat/al-folio #2059 | 2024-01-09T07:35:13.463705+00:00 | 2024-01-09T07:36:25.716598+00:00 | 2024-01-10T05:23:50Z | +0d 21:47:24.283 | No matching PullRequestSharing record | Level 4 only; PR absent at `tFG` |
| `CASE_BFB2599E145D` | PA | hufscheer/client #119, canonical hufscheer/web-v1 | 2023-11-30T08:40:08.698626+00:00 | 2023-11-30T08:40:22.179209+00:00 | 2023-11-30T09:19:13Z | +0d 00:38:50.821 | One later manual snapshot; no commit SHAs | Level 4 only; PR absent at `tFG` |
| `CASE_CE4BF3CB944D` | PN | pokt-network/poktroll #338 | 2024-01-19T20:27:43.622841+00:00 | 2024-01-19T20:28:03.030660+00:00 | 2024-01-19T16:29:19Z | -0d 03:58:44.031 | One later manual snapshot; no commit SHAs | Level 4 only |
| `CASE_F13F98792012` | PN | polywrap/evo.ninja #206, canonical agentcoinorg/evo.ninja | 2023-09-25T11:59:01.557490+00:00 | 2023-09-25T11:59:29.032600+00:00 | 2023-09-25T11:08:34Z | -0d 00:50:55.033 | One later snapshot; one PR commit SHA | Potential Level 2 lead |
| `CASE_F7BED13B8119` | PN | VOICEVOX/voicevox_engine #716 | 2023-07-15T21:52:50.143974+00:00 | 2023-07-15T21:55:31.086959+00:00 | 2023-07-09T10:27:11Z | -6d 11:28:20.087 | Nine later snapshots; five unique PR commit SHAs | Potential Level 2 lead |
| `CASE_EE7F13CD9FB7` | PN | darklang/dark #5058 | 2023-09-05T01:42:57.168012+00:00 | 2023-09-05T01:44:25.726944+00:00 | 2023-09-04T13:56:14Z | -0d 11:48:11.727 | Three later snapshots; eleven unique PR commit SHAs | Potential Level 2 lead |

For every pilot case, Stage A retains a current base SHA, head SHA, base ref, and head ref. The full values, every archived commit SHA, snapshot filenames, access result, and source path are recorded in the audit CSV. No pilot source contains a parent SHA or PR event history. The archive commit lists are later snapshots and may include commits added after `tFG`; they require membership, parent, and temporal validation before any Level 2 claim can be accepted.

## The two pre-PR pilot cases

Both focal PRs were also absent at `tC`:

- `CASE_85AD863F8290`: PR creation followed `tFG` by 78,444.283402 seconds (21h 47m 24.283s). The conversation supplies Ruby/Jekyll code and requested behavior, but no branch, commit SHA, or repository-state identifier. The PatchPrompt index supplies the eventual PR URL only. No matching PullRequestSharing snapshot is retained. The current candidate base cannot be related to a pre-`tFG` baseline with the retained evidence.
- `CASE_BFB2599E145D`: PR creation followed `tFG` by 2,330.820791 seconds (38m 50.821s). The conversation supplies TypeScript/React code and requested behavior, but no branch, commit SHA, or repository-state identifier. The PatchPrompt index supplies the eventual PR URL, and a later manual PullRequestSharing record supplies PR metadata without commit or parent SHAs. The current candidate base cannot be related to a pre-`tFG` baseline with the retained evidence.

The eventual PR link can establish case linkage. It cannot retroactively make the PR exist at `tFG`, and the later final PR state cannot be used to infer an earlier repository state without an admissible immutable relationship.

## Offline hierarchy coverage

The categories are mutually exclusive and prioritize the strongest retained lead. “Potential Level 2” means an archived focal-PR commit list exists, but its parent relationship and applicability at `tFG` have not been validated.

| Coverage category | PA | PN | Total |
|---|---:|---:|---:|
| Qualifying Level 1 | 0 | 0 | 0 |
| Potentially qualifying Level 2 | 23 | 27 | 50 |
| Potentially qualifying Level 3 | 0 | 0 | 0 |
| Level 4 only | 45 | 16 | 61 |
| Level 5 only | 0 | 0 | 0 |
| No target evidence | 0 | 0 | 0 |
| Cannot determine offline | 0 | 0 | 0 |

Matching PullRequestSharing records exist for 82 cases, but 32 of those have no commit SHA list. All 111 have retained Level 4 Stage A candidate metadata. Level 5 access results never replace Level 4 identity metadata and do not independently establish historical applicability.

The audit found no already-qualified stronger historical base evidence. It found derivation leads for 50 cases. Validating those leads would be a new, separately controlled step and could still leave the applicable base at `tFG` unresolved.

## Construct A and Construct B

### Construct A: focal PR base state applicable at `tFG`

- **Scientific interpretation:** anchors `H_i(tFG)` to the focal PR's base state.
- **When the PR exists:** requires a historically evidenced base SHA applicable at the cutoff.
- **When the PR is created later:** the PR object has no base state at `tFG`; the current contract does not define a substitute.
- **Identifiers and evidence:** focal PR identity, historical base SHA, timestamp/provenance, and preferably immutable relationships or corroborated contemporaneous provider evidence.
- **Reproducibility and leakage:** precise when evidence exists and strong against use of current/final state; evidence availability is the limiting factor.
- **Corpus impact:** 29 of 111 focal PRs were not yet created at `tFG`; 82 existed, but none currently has qualified Level 1–3 base evidence in the retained sources.
- **Protocol consistency:** this is the explicitly frozen `post-stage-c-reconstruction-v1` rule.

### Construct B: repository baseline/project state against which the generated change was developed, bounded by `tFG`

- **Scientific interpretation:** anchors reconstruction to the project state actually available to the developer before generation, whether or not a PR object existed.
- **When the PR exists:** the historically evidenced PR base may be a valid operationalization if it represents that development baseline.
- **When the PR is created later:** a branch tip, local parent, or other development baseline could in principle exist before `tFG`.
- **Identifiers and evidence:** repository identity plus a pre-`tFG` immutable commit/tree and evidence linking it to the developer's working baseline.
- **Reproducibility and leakage:** conceptually aligned with available project information, but risks arbitrary “latest before cutoff” substitution unless the linkage rule is explicitly specified and versioned.
- **Corpus impact:** can cover pre-PR cases only when an admissible baseline relationship is evidenced; it must not select a convenient commit to retain cases.
- **Protocol consistency:** it is not the current v1 rule and would require a versioned methodological decision.

The research question concerns reconstructing information available when the first generated change was produced. Construct B is closer to that conceptual timing for pre-PR work, while Construct A is the current precise operational anchor. The 29 pre-PR cases show that the two constructs are not equivalent. This audit does not replace one with the other.

## Interpretation and recommendation

The pilot supports **D: a combination of B and C**:

- **B:** the implemented acquisition path has only supporting Level 4/5 evidence; the offline inventory found no already-qualified Level 1–3 target identity. Four pilot cases have archived commit-list derivation leads, but none currently establishes the base applicable at `tFG`.
- **C:** two of eight pilot PRs, and 29 of 111 processable PRs, were created after `tFG`. For those cases, a focal-PR base “applicable at `tFG`” is undefined unless the protocol specifies how a pre-PR project baseline relates to the later focal PR.

The evidence supports the statement: **the currently implemented evidence path cannot establish the historical target identity**. It does not support the stronger statement that the historical repository states are generally unreconstructible.

### Recommended next path: PATH 3

Version the reconstruction contract because the repository-state anchor requires scientific clarification. Before final Post-C eligibility, define whether the target is strictly the contemporaneous focal-PR base (making pre-PR cases unresolved or inapplicable under that construct) or the evidenced development baseline at/before `tFG`, including a non-arbitrary linkage rule. Then evaluate the 50 potential Level 2 leads under the chosen version without using final implementation or outcome information.

This path allows Post-C eligibility to finish coherently: it first makes the scientific object well-defined for every temporal ordering, then applies an evidence hierarchy tailored to that object. It preserves unresolved cases when evidence is insufficient, retains the existing v1 pilot unchanged, and avoids weakening evidence standards or choosing current commits merely to maximize sample size.

## Validation invariants

- Stage C authority rows: 122.
- Post-C processable rows: 111.
- Eligibility rows: 111, all `pending_resolution`.
- Existing pilot executions: 8; remaining unattempted: 103.
- No new acquisition record was created.
- No Git clone/fetch, provider/API request, or other network acquisition was performed.
- No Stage D action or eligibility change was performed.

