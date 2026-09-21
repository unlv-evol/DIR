# System Architecture — Protocol v5

The operational protocol is [`protocols/pilot_case_selection_and_extraction.md`](../protocols/pilot_case_selection_and_extraction.md). Protocol v5 applies to the PA/PN candidate corpus. Existing `dir-screening-v3` outputs and the old approximately-30-case manifest are legacy/provisional and do not define this flow. This architecture keeps the original boxed diagram style.

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
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Eligible PA/PN Corpus                |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Stage B: Package Each Eligible       |
                 | Conversation                         |
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
                 | Stage D: Human Validation of         |
                 | Conversation Extraction (~30%)       |
                 +-------------------+-------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Stage E: Freeze the Conversation-    |
                 | Side Record; tC and tFG independent  |
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

Stage B preserves three layers: retrieved source archive (source bytes and safe retrieval provenance), lossless normalized conversation (all source conversation records, tool traces, first-generation response, later turns, and source locations), and derived Stage C model view (neutral case ID, conversation-addressed turns, temporal and artifact provenance). A restricted case-linkage record retains PR/source identities for integrity and later Stage F work through the same neutral ID; it is never model input. The Stage C supplied-C/S/V extractor does **not** receive the screening row, PA/PN status, repository/PR URL, PR body, commits, reviews, issues, CI, changed files, diff, or eventual implementation. The full normalized record preserves the artifact-bearing response and later turns; the supplied-information window excludes them. Human judgments on the validation sample remain independent until reconciliation; frozen records cannot be rewritten by subsequent project findings. `pilot_analysis/conversation/` can hold validated versioned records; its older `cases/` analyses are legacy/provisional.

## Historical information and temporal boundary

Preserve `tC` (first developer prompt) and `tFG` (immediately before the first artifact-bearing assistant response in the first snippet family) with independent value, precision, status, and source. `primary_repository_cutoff = tFG` for `dir-tfg-v2`; never substitute unresolved `tFG` with `tC`. The Historical Project Information Space `H_i(tFG)` comprises searchable project information demonstrably available by the cutoff. A compact per-case index holds repository boundary SHA/tree/history references; eligible PR, issue, CI, and discussion IDs/timestamps; and provenance. It does not eagerly copy large trees, logs, diffs, or discussions. Record `available_by_tC` and `available_by_tFG` separately where determinable. Historical availability, retrieval, relevance, and additional-evidence status are distinct.

## Discovery, held-out, and evidence flow

A reproducible PA/PN-stratified split follows validation of the extraction procedure and freeze of downstream-processable conversation records. Frozen does not imply individually human validated: sampled and unsampled case statuses remain distinct. Unresolved boundaries and extraction failures remain outside the split until resolved. Discovery cases alone produce traces and Algorithm v1. Held-out project information remains inaccessible to algorithm design and tuning. Each trace connects a prompt/C/S/V cue to a justified search operation, historical artifact, relevant fragment, next operation, and additional evidence or a documented no-evidence stopping result. Evidence retention tests temporal validity, task relevance, novelty beyond the frozen conversation, C/S/V contribution, and uncertainty reduction. Matching the PR or repository alone is insufficient.

Frozen retrieval yields a compact Retrieved Evidence Index. Evidence Engineering first selects and semantically reduces candidates, then materializes large payloads only where needed and reduces their content into `E_i^eng`, preserving gaps and provenance. Reconstruction receives only the original prompt, permitted prior conversation, frozen supplied C/S/V, and engineered evidence. The controlled original and reconstructed conditions use the same current model/configuration. The integrated implementation stays sealed until both outputs are fixed.

## RAW / SAFE / SEALED boundaries

- `cases/raw/`: historical audit material; may contain downstream outcomes and is not reconstruction-safe.
- `cases/conversations/`: isolated conversation-only packages used before project inspection.
- `data/derived/historical_information/`: compact historical indexes and references at `tFG`.
- `safe/reconstruction/`: only evidence admissible under frozen methodology.
- `sealed/evaluation/`: post-cutoff/outcome material, including the integrated implementation until final evaluation.

A separately versioned `tC` sensitivity partition can be derived later. Retrospective researcher inspection, when explicitly allowed, never changes automated reconstruction admissibility. The old approximately-30-case pilot selection, eager full PR extraction, and size-threshold exclusions remain historical workflow descriptions only, not Protocol v5 steps.
