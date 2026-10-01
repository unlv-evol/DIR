# Protocol v5 Stage C

Stage C performs two independent OpenAI Responses API calls for one explicitly selected Stage B package. Pass 1 receives the complete `stage_c_model_view.json` and identifies the first snippet family, artifact-bearing assistant response, immediately triggering developer prompt, and boundary. Conceptual family relationships may span responses, but the authoritative first-generation family is response-local and contains only coherent artifacts generated in the earliest selected response. Later turns may clarify relationships but cannot contribute selected artifact IDs. Deterministic code validates ownership fail closed, derives `tFG` from the selected response without substituting `tC`, and constructs the strictly pre-boundary conversation. Pass 2 receives only that reduced conversation and extracts textual Context, Specificity, and Verification information.

C/S/V are information categories, not scores. All conversation turns before the first-generation boundary are admissible conversation-side evidence, including assistant turns; provenance preserves the originating role. The response containing the first generated snippet and all later turns are excluded from Pass 2.

During Stage C, model-accessible tools are disabled. Stage C operates exclusively on conversation evidence supplied by the DIR pipeline. Repository evidence is acquired separately after Stage C under the `tFG` temporal-evidence policy.

Configuration check, with no API call:

```bash
python3 pipeline/stage_c/run.py --check-config
```

Future authorized one-case live extraction:

```bash
python3 pipeline/stage_c/run.py --case-id CASE_XXXXXXXXXXXX --live
```

An explicitly authorized development retry can use `--development-run-id retry_01` to write a separate suffixed artifact without changing the selected extraction contract. The same normal two-pass pipeline and no-overwrite guard apply.

`DIR_STAGE_C_MAX_RETRIES` configures the OpenAI SDK's bounded transport/provider retry allowance; the current execution configuration is `2`, and valid values are integers from `0` through `5`. Stage C passes this value explicitly to the SDK and records it as `sdk_max_retries` in future output provenance. Stage C has no application-level retry loop: a completed invocation that fails semantic, deterministic, provenance, or human validation remains a failed attempt. A separately authorized run with a distinct development-run ID is a new controlled execution, not an SDK retry. The SDK retry allowance does not establish the number of HTTP attempts, which is not claimed unless independently observable.

Input and output:

```text
cases/conversations/<case_id>/stage_c_model_view_v2.json
cases/conversations/<case_id>/stage_c_extraction_v6.json
```

The current `--input-version v3` execution contract reads `conversation-only-v2` and writes `conversation-draft-v4` under extraction procedure `conversation-extraction-v6` and unchanged temporal methodology `dir-tfg-v2`. Pass 1 remains `dir-stage-c-first-generation-v4` with `stage-c-pass1-v2`. Historical `v1` and `v2` execution contracts remain available and immutable.

Pass 2 prompt v3 preserves the v2 modality rules and makes provenance serialization explicit. `source_turns` and `source_roles` are equal-length parallel arrays; each role corresponds positionally to its turn and repeated roles must be repeated in the array. Evidence remains an exact textual attribution to at least one cited admissible turn. The response schema is `stage-c-pass2-v2`. `conversation-draft-v4` also preserves `pass_2_outcome.status` and the reason for every non-complete Pass 2 outcome.

If an invoked Pass 2 result is rejected, the failed draft preserves available invocation and request provenance but emits no accepted C/S/V items from that result. Parsing and deterministic validation statuses remain separate.

Pass 1 failures follow the same fail-closed rule. Parsed rejected Pass 1 or Pass 2 model output is written, when available, to a separate `stage_c_extraction_v4*.diagnostic.json` sidecar marked non-authoritative. Rejected values never populate the accepted family, boundary, `tFG`, or C/S/V fields. The sidecar retains only response and non-secret request provenance needed to reproduce and diagnose the failure.

Existing output is never overwritten. Pre-correction v2 development records can be rebuilt without a model call using `migrate_family_id.py`; the v2 record remains unchanged and the migrated v3 record records its source hash and original model family value. Existing Stage C development records remain immutable; prompt-v3 runs use versioned v4 output paths beside preserved prior attempts. Stage C does not update scientific eligibility. Its result is consumed by the Post-Stage-C processability/eligibility workflow before Stage D.

`conversation-only-v2` uses `generated_technical_content_candidates` with `GTC_*` IDs. Pass 1 prompt v4 treats these as candidate representations rather than scientific artifacts, permits selection of incomplete candidates when their family is determinate, and preserves response-local selection. Deterministic validation checks exact spans, hashes, ownership, ordering, and selected-ID existence before deriving a family ID or `tFG`.

Historical V2 execution remains available as `--input-version v2` and writes only `stage_c_extraction_v5*.json`. Future v6 execution requires explicit `--input-version v3`; it reads the same immutable V2 model view and writes a no-overwrite `stage_c_extraction_v6*.json`. Selecting either contract never overwrites the other.
