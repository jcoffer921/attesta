# TSS non-detect review: pa0000000, 2026-10, pipeline lab-csv-import

Command: `racket dsl/main.rkt run --permit dsl/permit/permits/pa0000000.rkt --pipeline dsl/pipeline/pipelines/lab-csv-import.rkt --period 2026-10`

## Answer: we did not pass, and we cannot claim a pass either.
The engine returned no `pass` for any clause. The TSS limits are `review-required`, and pH and Flow are `missing-data`.

## Inputs
- n1: TSS `<80` mg/L on 2026-10-05 (non-detect, reporting limit 80). Parsed as non_detect=true, value 80.
- n2: TSS 10 mg/L on 2026-10-19.
- No rejections. Both records passed all pipeline steps.

## Results
| Parameter | Clause | Computed | Threshold | Status |
|---|---|---|---|---|
| TSS | monthly-avg | <45 | 30 mg/L | review-required |
| TSS | daily-max | <80 | 60 mg/L | review-required |
| pH | range | n/a | 6..9 | missing-data (0 of 5 required samples) |
| Flow | monthly-avg | n/a | 0.5 MGD | missing-data (0 samples) |

## Interpretation
- Using the reporting limit (80), the TSS average is (80+10)/2 = 45 > 30, and the max 80 > 60. That would look like an exceedance.
- The 80 is only a ceiling. The true n1 value is somewhere between 0 and 80. With n1 at zero, the average is 5 and the max is 10, both compliant.
- The data can neither show compliance nor prove a violation, so the engine correctly flags human review rather than an exceedance or a pass.
- Note the problem is the detection limit. A reporting limit of 80 mg/L is above the permit daily max (60), so the method (SM2540D at QL 80) is not sensitive enough to demonstrate compliance. Re-analyze with a lower-QL method or confirm the QL, and document it.

## Other findings
- Sample frequency: TSS requires 2 per month. 2 samples were provided, so the frequency is met.
- pH: requires 1 per week (engine computed 5 samples for October). None were supplied, so missing-data. This is a reporting gap, not a violation, but it must be resolved (supply data or NODI code).
- Flow: no samples supplied, so missing-data (report-only clause is not in the results).
- The permit is a fictional placeholder (PA0000000), so this is a syntax and engine exercise, not a real compliance determination.
- convert-units ug/L -> mg/L was a no-op (values already mg/L).

## Recommended actions
1. Have the lab confirm the n1 QL and whether a lower reporting limit is achievable or the sample can be re-run.
2. Have a human reviewer decide on the TSS clauses; do not report an exceedance on the non-detect alone.
3. Supply the missing pH and Flow data before submitting the DMR.
