# System Architecture — Protocol v5.2

The operational protocol is [`protocols/experiment_protocol.md`](../protocols/experiment_protocol.md). Protocol v5.2 applies to the PA/PN candidate corpus.

## Research data flow

```text
                 +---------------------------------------+
                 | PatchPrompt PA/PN Candidate Corpus   |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Stages A-C: Screen, Package, and     |
                 | Extract Conversation Evidence        |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Post-C v3: B1 Direct Evidence ->     |
                 | B2 Git Derivation; B5 Support Only  |
                 | Establish Minimum R_i(tFG)           |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Stage D: Validate Stage C Extraction |
                 | on ~30% of Eligible PA/PN Corpus     |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Stage E: Freeze Authoritative        |
                 | Conversation-Side Records            |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Stage F1: Discovery / Held-Out       |
                 | Assignment                           |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Stage F2: Construct H_i(tFG) using   |
                 | authoritative R_i(tFG)               |
                 +-------------------+-------------------+
                                     |
                           +---------+---------+
                           | discovery         | held-out
                           v                   |
          +---------------------------+        |
          | Stage G: Evidence-Pattern |        |
          | Discovery                 |        |
          +-------------+-------------+        |
                        |                      |
                        v                      |
          +---------------------------+        |
          | Stage H: Freeze Retrieval |        |
          | Algorithm v1              |        |
          +-------------+-------------+        |
                        +----------+-----------+
                                   |
                                   v
                 +---------------------------------------+
                 | Stage I: Apply Frozen Algorithm      |
                 | Retrieved Index -> Selection ->      |
                 | Semantic Reduction -> Deferred       |
                 | Materialization -> Payload Reduction |
                 | -> E_i^eng                           |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Stage J1: Structured Intent Record   |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Stage J2: Evidence-Grounded Prompt   |
                 | Reconstruction                       |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Stage K: Controlled Same-Model      |
                 | Generation; BOTH Outputs Fixed       |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Stage L1: Intent-Record Fidelity     |
                 | Evaluation; L1 Judgment Fixed        |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Reveal Integrated Implementation     |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Stage L2: Generation-Effectiveness  |
                 | Evaluation                          |
                 +---------------------------------------+
```

## Conversation-side isolation

Stage A contains automated/administrative screening and a separate restricted manual correspondence activity for all candidate/processable cases. Source linkage and semantic task correspondence remain distinct. Completed semantic reviews reference checksum-bound restricted correspondence-evidence packets that preserve archive support versus reviewer attestation and cannot enter later model or reconstruction inputs. Correspondence `yes` can satisfy that Stage A criterion, `no` excludes, and `unresolved` remains pending and blocks Stage B. Operational readiness is separate from scientific disposition: a pending case may be packaged only when its sole unresolved reasons are the preliminary first-generation boundary and `tFG`-dependent historical-state judgments. Stage D validates only Stage C conversation extraction on the approximately 30% PA/PN-stratified sample.

Stage B preserves three layers: retrieved source archive (source bytes and safe retrieval provenance), lossless normalized conversation (all source conversation records, tool traces, first-generation response, later turns, and source locations), and derived Stage C model view (neutral case ID, conversation-addressed turns, temporal and candidate provenance). `conversation-only-v2` adds deterministic `generated-technical-content-v2` candidates with uniform `GTC_*` IDs, including declarative resources and explicit incomplete fragments; a candidate is not yet a scientific generated artifact. Candidates own exact spans within one assistant response and never span responses. Exact V1 mappings are retained only through nullable `legacy_artifact_id`; historical V1 packages remain immutable. Source acquisition distinguishes fresh retrieval, current-cache reuse, explicit offline legacy raw-source import, and explicit offline archived HTTP response import. Archived HTTP import uses only identity-matched raw `HTMLContent` in the PatchTrack replication ZIP, selects the earliest qualifying snapshot deterministically, and never substitutes the derived `Conversations` list or screening evidence. Unknown or timezone-naive historical retrieval times remain distinct from import time. Corpus orchestration preserves valid packages and reports operational Stage C readiness without changing scientific eligibility. A restricted case-linkage record retains PR/source identities through the same neutral ID; it is never model input. Isolation is provenance-based: the model view must equal the deterministic derivative of the normalized source conversation and cannot carry independently injected administrative fields. Repository or PR strings already present in source conversation text remain unchanged. Stage C uses two independent, tool-free OpenAI Responses API passes. Pass 1 remains `dir-stage-c-first-generation-v4` and receives the complete model view to select a response-local first family from supplied candidates; it cannot invent candidate spans, and incompleteness alone does not prevent selection. Deterministic code validates response-local ownership fail closed, derives `tFG`, and constructs the strictly pre-boundary conversation. Extraction v6 Pass 2 uses `dir-stage-c-csv-extraction-v3` and `stage-c-pass2-v2`; it receives only that reduced conversation and extracts textual C/S/V. Its source-turn and source-role arrays are positionally paired with equal length, evidence remains textually attributable to cited admissible turns, and the final record preserves the independent Pass 2 outcome. All pre-boundary user and assistant turns are admissible, with their roles preserved; the first-generation response and every later turn are excluded. Neither pass receives screening data, PA/PN, independently injected repository/PR metadata, outcomes, or external tools. Temporal methodology remains `dir-tfg-v2`.

Immediately after Stage C, Post-C Historical Processability / Eligibility establishes the minimum historically justified development baseline `R_i(tFG)`, resolves deferred criteria, and determines final scientific eligibility. It does not build complete `H_i(tFG)` or perform evidence discovery. Historical v1 retains its focal-PR-base definition and v2 retains its B1–B5 same-eight pilot. Current `post-stage-c-reconstruction-v3` asks whether admissible pre-`tFG` information directly establishes a revision (B1), and, only from that revision, whether immutable Git relationships deterministically derive the baseline when needed (B2). Present-day B5 information supports routing, materialization, validation, and cross-checking only. B3 and B4 are disabled and reserved for a separately justified future version. PatchPrompt corpus archives remain conversation/case provenance and are not v3 repository-state evidence. Infrastructure failure remains separate from scientific `no`. Stage D samples approximately 30% of the scientifically eligible corpus solely to validate Stage C extraction.

## Historical information and temporal boundary

Preserve `tC` and `tFG` with independent value, precision, status, and source. `primary_repository_cutoff = tFG`; never substitute unresolved `tFG` with `tC`. Post-C v3 establishes `R_i(tFG)` through B1 and conditional B2. This is the historically justified repository revision representing the project baseline relevant to the focal task. Stage F2 then constructs complete `H_i(tFG)` from that fixed anchor without rediscovering or replacing it; repository, PR, issue/work-item, CI, discussion/review, and history components retain independent statuses. PR state is included only when the PR existed by `tFG`. Exact timestamps use inclusive `<= tFG`; date-only same-day ordering is unresolved without independent ordering. Historical availability, retrieval, relevance, and evidence status remain distinct.

## Discovery, held-out, and evidence flow

A reproducible PA/PN-stratified split follows validation of the extraction procedure and freeze of downstream-processable conversation records. Frozen does not imply individually human validated: sampled and unsampled case statuses remain distinct. Unresolved boundaries and extraction failures remain outside the split until resolved. Discovery cases alone produce traces and Algorithm v1. Held-out project information remains inaccessible to algorithm design and tuning. Each trace connects a prompt/C/S/V cue to a justified search operation, historical artifact, relevant fragment, next operation, and additional evidence or a documented no-evidence stopping result. Candidate additional evidence must concern the target task, add beyond the frozen conversation, and contribute C/S/V; temporal availability by `tFG` remains mandatory. Uncertainty reduction can be recorded analytically but is not an additional retention gate. Matching the PR or repository alone is insufficient.

Frozen retrieval yields a compact Retrieved Evidence Index. Evidence Engineering first selects and semantically reduces candidates, then materializes large payloads only where needed and reduces their content into `E_i^eng`, preserving gaps and provenance. Reconstruction receives only the original prompt, permitted prior conversation, frozen supplied C/S/V, and engineered evidence. The controlled original and reconstructed conditions use the same current model/configuration. The integrated implementation stays sealed until both outputs are fixed.

## RAW / SAFE / SEALED boundaries

- `cases/raw/`: historical audit material; may contain downstream outcomes and is not reconstruction-safe.
- `cases/conversations/`: isolated conversation-only packages used before project inspection.
- `data/derived/historical_information/`: compact historical indexes and references at `tFG`.
- `safe/reconstruction/`: only evidence admissible under frozen methodology.
- `sealed/evaluation/`: post-cutoff/outcome material, including the integrated implementation until final evaluation.

A separately versioned `tC` sensitivity partition can be derived later. Retrospective researcher inspection, when explicitly allowed, never changes automated reconstruction admissibility.
