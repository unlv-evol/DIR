# System Architecture — Protocol v5

The operational protocol is [`protocols/experiment_protocol.md`](../protocols/experiment_protocol.md). Protocol v5 applies to the PA/PN candidate corpus.

## Research data flow

```text
                 +---------------------------------------+
                 | PatchPrompt PA/PN Candidate Corpus   |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Stage A: Define and Screen the       |
                 | PA/PN Corpus                         |
                 | Automated / Administrative Screening |
                 |                 +                    |
                 | Intermediate Restricted Review CSV   |
                 |                 +                    |
                 | Manual PR-Conversation               |
                 | Correspondence Screening (100%)      |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Scientific: eligible / excluded /    |
                 | pending_resolution                   |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Stage B: Package Operationally       |
                 | Ready Conversations                  |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Stage C: LLM Conversation Extraction |
                 | First generation + supplied C/S/V    |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Post-Stage-C Processability /        |
                 | Eligibility Resolution               |
                 | Boundary + H_i(tFG) checks            |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Stage D: Human Validation of         |
                 | Conversation Extraction (~30%        |
                 | eligible PA/PN-stratified sample)    |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Stage E: Freeze Validated Records    |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Stage F: Split the Corpus            |
                 | PA/PN-stratified (~70% / ~30%)       |
                 +-------------------+-------------------+
                                     |
                           +---------+---------+
                           |                   |
                           v                   v
          +---------------------------+  +---------------------------+
          | Stage F: Historical       |  | Stage F: Historical       |
          | H_i(tFG) DISCOVERY Index  |  | H_i(tFG) HELD-OUT Index   |
          +-------------+-------------+  +-------------+-------------+
                        |                          |
                        v                          |
          +---------------------------+             |
          | Stage G: Evidence-Pattern |             |
          | Discovery on Discovery    |             |
          | Set                       |             |
          +-------------+-------------+             |
                        |                          |
                        v                          |
          +---------------------------+             |
          | Stage H: Derive and FREEZE |             |
          | Retrieval Algorithm v1    |             |
          +-------------+-------------+             |
                        |                          |
                        +-------------+------------+
                                      |
                                      v
                 +---------------------------------------+
                 | Stage I: Apply Frozen Algorithm v1   |
                 | Held-out H_i(tFG); retrieval begins  |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Stage I: Retrieved Evidence Index    |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Stage I: Evidence Selection          |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Stage I: Semantic Evidence Reduction |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Stage I: Deferred Materialization    |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Stage I: Evidence Payload Reduction  |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Stage I: Engineered Evidence E_i^eng |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Stage J: Reconstruct the Developer   |
                 | Intent                               |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Stage K: Controlled Code Generation  |
                 | Same current model/configuration     |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Stage K: BOTH Outputs Fixed          |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Stage L: Reveal Integrated           |
                 | Implementation                       |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Stage L: Evaluate                    |
                 +---------------------------------------+
```

## Conversation-side isolation

Stage A contains automated/administrative screening and a separate restricted manual correspondence activity for all candidate/processable cases. Source linkage and semantic task correspondence remain distinct. Completed semantic reviews reference checksum-bound restricted correspondence-evidence packets that preserve archive support versus reviewer attestation and cannot enter later model or reconstruction inputs. Correspondence `yes` can satisfy that Stage A criterion, `no` excludes, and `unresolved` remains pending and blocks Stage B. Operational readiness is separate from scientific disposition: a pending case may be packaged only when its sole unresolved reasons are the preliminary first-generation boundary and `tFG`-dependent historical-state judgments. Stage D validates only Stage C conversation extraction on the approximately 30% PA/PN-stratified sample.

Stage B preserves three layers: retrieved source archive (source bytes and safe retrieval provenance), lossless normalized conversation (all source conversation records, tool traces, first-generation response, later turns, and source locations), and derived Stage C model view (neutral case ID, conversation-addressed turns, temporal and candidate provenance). `conversation-only-v2` adds deterministic `generated-technical-content-v2` candidates with uniform `GTC_*` IDs, including declarative resources and explicit incomplete fragments; a candidate is not yet a scientific generated artifact. Candidates own exact spans within one assistant response and never span responses. Exact V1 mappings are retained only through nullable `legacy_artifact_id`; historical V1 packages remain immutable. Source acquisition distinguishes fresh retrieval, current-cache reuse, explicit offline legacy raw-source import, and explicit offline archived HTTP response import. Archived HTTP import uses only identity-matched raw `HTMLContent` in the PatchTrack replication ZIP, selects the earliest qualifying snapshot deterministically, and never substitutes the derived `Conversations` list or screening evidence. Unknown or timezone-naive historical retrieval times remain distinct from import time. Corpus orchestration preserves valid packages and reports operational Stage C readiness without changing scientific eligibility. A restricted case-linkage record retains PR/source identities through the same neutral ID; it is never model input. Isolation is provenance-based: the model view must equal the deterministic derivative of the normalized source conversation and cannot carry independently injected administrative fields. Repository or PR strings already present in source conversation text remain unchanged. Stage C uses two independent, tool-free OpenAI Responses API passes. Pass 1 remains `dir-stage-c-first-generation-v4` and receives the complete model view to select a response-local first family from supplied candidates; it cannot invent candidate spans, and incompleteness alone does not prevent selection. Deterministic code validates response-local ownership fail closed, derives `tFG`, and constructs the strictly pre-boundary conversation. Extraction v6 Pass 2 uses `dir-stage-c-csv-extraction-v3` and `stage-c-pass2-v2`; it receives only that reduced conversation and extracts textual C/S/V. Its source-turn and source-role arrays are positionally paired with equal length, evidence remains textually attributable to cited admissible turns, and the final record preserves the independent Pass 2 outcome. All pre-boundary user and assistant turns are admissible, with their roles preserved; the first-generation response and every later turn are excluded. Neither pass receives screening data, PA/PN, independently injected repository/PR metadata, outcomes, or external tools. Temporal methodology remains `dir-tfg-v2`.

Immediately after Stage C, the unlettered Post-Stage-C workflow resolves first-generation boundary identifiability, reconstructs or evaluates `H_i(tFG)` through controlled DIR acquisition, resolves historical-state reconstructibility and remaining deferred criteria, and determines final scientific eligibility. `post-stage-c-reconstruction-v1` treats the core repository target as the historically evidenced focal-PR base state applicable at `tFG`; a Stage A base SHA is only a candidate until identity and temporal applicability are independently verified. Infrastructure failure remains separate from scientific `no`. Stage C does not update eligibility. Stage D then samples approximately 30% of the scientifically eligible PA/PN corpus to validate Stage C extraction. Full evidence-discovery indexes and retrieval work remain governed by the later frozen/split workflow.

## Historical information and temporal boundary

Preserve `tC` (first developer prompt) and `tFG` (immediately before the first artifact-bearing assistant response in the first snippet family) with independent value, precision, status, and source. `primary_repository_cutoff = tFG` for `dir-tfg-v2`; never substitute unresolved `tFG` with `tC`. The Historical Project Information Space `H_i(tFG)` comprises repository, PR, issue/work-item, CI, and discussion/review information demonstrably available by the cutoff, with independently statused components. A compact per-case index holds the verified focal-PR base boundary SHA/tree/history references; eligible PR, issue, CI, and discussion IDs/timestamps; and provenance. It does not eagerly copy large trees, logs, diffs, or discussions. Exact timestamps use an inclusive `<= tFG` test; date-only same-day ordering is unresolved unless other evidence orders it. Record `available_by_tC` and `available_by_tFG` separately where determinable. Historical availability, present retrieval, relevance, and additional-evidence status are distinct.

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
