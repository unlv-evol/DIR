# Experiment Matrix

Track each experiment with:

| Experiment | Input condition | Evidence condition | Model/config | Unit | Primary outcome | Status |
|---|---|---|---|---|---|---|
| Post-C v2 pilot | Authoritative Stage C boundary and `tFG` | B1–B5 evidence used only to establish `R_i(tFG)` | Deterministic sequential acquisition; no model | Same eight v1 pilot cases | `historical_state_reconstructible` | Prepared, unexecuted |
| Stage J reconstruction | Original target prompt, admissible prior conversation, frozen supplied C/S/V | Frozen Stage I `E_i^eng` only | Frozen reconstruction procedure | Eligible held-out case | Structured intent fidelity and reconstructed prompt | Planned |
| Stage K/L controlled comparison | Original versus reconstructed prompt with identical prior conversation | Integrated implementation sealed until outputs and L1 freeze | Same current model and configuration | Eligible held-out case | L1 intent fidelity; L2 generation effectiveness | Planned |

Keep the matrix synchronized with `experiments/` and the corresponding run manifests.
