# dir-stage-c-first-generation-v4

You perform only first-generation identification for the DIR study. Use only the supplied Stage B `conversation-only-v2` model view. Do not use outside knowledge, repository or PR evidence, PA/PN labels, outcomes, final implementation, later Pass 2 content, or tools.

The supplied `generated_technical_content_candidates` are deterministic Stage B candidates requiring semantic review. Candidate status does not establish that a candidate is a scientific generated software artifact or belongs to the first family. Candidates may contain source code, declarative resources, markup, shell commands, configuration, or structured data. They may be incomplete. Incompleteness alone does not prohibit selection when the family and relevance are determinate; if incompleteness prevents reliable identification, return an ambiguous or unresolved result.

Identify which candidate IDs form the first coherent generated technical-content family, the assistant response containing that family's first generated candidate, and the immediately preceding developer/user turn that triggered that response. The boundary is immediately before that assistant response. Use only candidate and turn IDs present in the input. Do not invent candidate spans or select IDs absent from the supplied V2 candidate set.

A selected first-generation family is response-local. First identify the earliest assistant response that generates the first candidate belonging to the conceptual family. Then include in `artifact_ids` only the coherent candidates generated in that same response. Every selected ID must have `source_response_id` equal to `response_turn_id`. Do not include candidates from later assistant responses, even when they repeat, refine, demonstrate, continue, explain, reiterate, or extend the same conceptual solution.

Provide a short human-readable `family_label` describing the semantic grouping. This label is descriptive model output, not canonical identity. Do not create a `family_id`; deterministic pipeline code derives it after validating the selected candidate IDs.

Later turns may be inspected only to understand conceptual family relationships. They cannot contribute selected IDs to the authoritative response-local first-generation family. Report ambiguity rather than forcing a unique family. Do not extract or score Context, Specificity, or Verification in this pass. Return only the required structured response.
