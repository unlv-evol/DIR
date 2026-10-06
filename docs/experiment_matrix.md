# Experiment Matrix

Track each experiment with:

| Experiment | Input condition | Evidence condition | Model/config | Unit | Primary outcome | Status |
|---|---|---|---|---|---|---|
| Post-Stage-C reconstruction and eligibility | Authoritative Stage C boundary, repository, and focal PR | Exact focal/base Git lineage state at `tFG`; no outcome input | `post-stage-c-git-lineage-v4`; deterministic | 111 authoritative cases | `S_i(tFG)` and final eligibility | Complete: 111 eligible |
| Stage J reconstruction | Original target prompt, admissible prior conversation, frozen supplied C/S/V | Frozen Stage I `E_i^eng` only | Frozen reconstruction procedure | Eligible held-out case | Structured intent fidelity and reconstructed prompt | Planned |
| Stage K/L controlled comparison | Original versus reconstructed prompt with identical prior conversation | Integrated implementation sealed until outputs and L1 freeze | Same current model and configuration | Eligible held-out case | L1 intent fidelity; L2 generation effectiveness | Planned |

Keep the matrix synchronized with `experiments/` and the corresponding run manifests.
