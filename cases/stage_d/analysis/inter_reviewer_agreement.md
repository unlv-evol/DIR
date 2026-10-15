# Stage D inter-reviewer agreement

## Design and inputs

Stage D sampled 33 of 111 scientifically eligible cases by proportional PA/PN-stratified random sampling without replacement: 20 of 68 PA and 13 of 43 PN, using seed `20261005`. Both PhD reviewers independently assessed the same cases in the same frozen order with PA/PN and downstream outcomes concealed. The analysis reads the original completed workbooks directly and does not use adjudicated judgments.

Nine categorical fields yield 297 paired judgments. `uncertain` is retained as an observed category. Free-text notes are preserved in the disagreement inventory and excluded from agreement calculations.

## Field-level results

| Field | Exact agreement | Disagreements | Cohen's kappa |
|---|---:|---:|---:|
| First-generation identification | 33/33 (100.00%) | 0 | NA |
| Target prompt | 33/33 (100.00%) | 0 | NA |
| tFG boundary | 30/33 (90.91%) | 3 | 0.000000 |
| Context | 33/33 (100.00%) | 0 | NA |
| Specificity | 33/33 (100.00%) | 0 | NA |
| Verification | 33/33 (100.00%) | 0 | NA |
| Missing information | 32/33 (96.97%) | 1 | 0.000000 |
| Post-boundary leakage | 33/33 (100.00%) | 0 | NA |
| Overall extraction | 29/33 (87.88%) | 4 | -0.047619 |

Cohen's kappa is unweighted because the judgments are treated as nominal categories. `NA` means kappa is mathematically undefined because both reviewers assigned the same single category to all 33 cases; it is not replaced by 1.0. Kappa values of zero or slightly below zero in highly imbalanced fields do not contradict high exact agreement: expected agreement from the marginal distributions is already very high.

## Pooled descriptive result

There were 289 agreements among 297 paired categorical judgments (97.31%), with 8 field-level disagreements across 4 cases: CASE_188C69620856, CASE_522F0F296F37, CASE_AD8C4F13A90B, CASE_EE7F13CD9FB7. This pooled percentage describes judgments, not the percentage of cases with complete agreement, and it does not replace field-specific reliability estimates.

## Interpretation and limits

Independent agreement was complete for first-generation identification, target prompt, Context, Specificity, Verification, and post-boundary leakage. Disagreements concerned three `tFG` boundary judgments, one missing-information judgment, and four overall-extraction judgments. Subsequent joint findings and decisions are documented separately and never enter these calculations.

Stage D directly measures judgments on extraction correctness, missing information, leakage, and boundary selection. It does not contain a dedicated categorical field isolating provenance correctness. The supplementary provenance audit therefore cannot be interpreted as 480 manually validated items: independent Stage D review covered 33 sampled cases.

## Reproduction

```text
python3 -B pipeline/stage_d/run_agreement.py
```
