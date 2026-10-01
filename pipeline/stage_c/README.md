# Protocol v5 Stage C

Stage C performs two independent OpenAI Responses API calls for one explicitly selected Stage B package. Pass 1 receives the complete `stage_c_model_view.json` and identifies the first snippet family, artifact-bearing assistant response, immediately triggering developer prompt, and boundary. Deterministic code validates all references, derives `tFG` from the selected response without substituting `tC`, and constructs the strictly pre-boundary conversation. Pass 2 receives only that reduced conversation and extracts textual Context, Specificity, and Verification information.

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

Input and output:

```text
cases/conversations/<case_id>/stage_c_model_view.json
cases/conversations/<case_id>/stage_c_extraction_v3.json
```

The output is a `conversation-draft-v3` record under methodology `dir-tfg-v2` and extraction procedure `conversation-extraction-v3`. Pass 1 v2 returns a descriptive `family_label`; validated selected artifact IDs are ordered by response event, order within response, and artifact ID. Deterministic code hashes compact, key-sorted UTF-8 JSON containing the case ID and ordered artifact IDs with SHA-256 and uses the first 24 lowercase hexadecimal characters as `FGF_<digest>`. Including the case ID makes the identifier globally usable. The label does not affect identity, boundaries, time, or eligibility.

Existing output is never overwritten. Pre-correction v2 development records can be rebuilt without a model call using `migrate_family_id.py`; the v2 record remains unchanged and the migrated v3 record records its source hash and original model family value. Stage C does not update scientific eligibility. Its result is consumed by the Post-Stage-C processability/eligibility workflow before Stage D.
