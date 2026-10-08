# Stage D human validation design

Stage D validates the authoritative Stage C conversation extraction after final
scientific eligibility resolution. It does not validate Post-Stage-C historical
repository reconstruction.

The executed sampling frame contains 111 eligible cases: 68 PA and 43 PN. A
proportional stratified random sample without replacement contains 33 cases:
20 PA and 13 PN, or 29.73% of the eligible corpus. PA/PN is used only for
stratification. Repository, focal/base reconstruction route, historical
observability, conversation length, C/S/V density, PR outcome, and downstream
implementation do not influence selection.

The preserved implementation uses fixed integer seed `20261005`. It sorts case
IDs lexicographically within each stratum, derives domain-separated random
streams from the seed, samples each stratum without replacement, combines the
draws, and applies a deterministic seeded shuffle for a blinded review order.

Two independent reviewers receive the same 33 cases in the same order and the
same Stage C evidence, with separate blank annotation CSVs. Reviewer-facing
files omit PA/PN, eligibility, Post-C reconstruction information, historical
observability, downstream outcomes, and later conversation turns. Each CSV has
one row per case and links to a reviewer-safe JSON containing the target prompt,
ordered pre-boundary conversation, selected first-generation response, and the
authoritative Context, Specificity, and Verification items with provenance.
Each JSON is accompanied by a deterministic standalone HTML rendering for
human review. The HTML contains no additional evidence: it preserves the JSON
content, ordering, evidence restrictions, and provenance while making source
URLs, turns, artifacts, and Stage C items easier to inspect. Reviewer workbook
`case_details` cells retain the displayed JSON path and open the sibling HTML
page through a repository-relative link. JSON remains the structured evidence
authority, CSV remains the canonical annotation representation, and XLSX is
the frozen reviewer-facing instrument.

The first-generation response is displayed only to validate first-generation,
target-prompt, boundary, and `tFG` identification. It is explicitly separated
from the pre-boundary conversation and cannot supply C/S/V evidence.

Independent judgments are preserved before any future reconciliation or
adjudication. Human annotation has not yet been performed, and no agreement or
validation result is claimed by package preparation.
