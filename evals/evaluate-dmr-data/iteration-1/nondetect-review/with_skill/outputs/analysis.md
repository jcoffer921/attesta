# DMR evaluation: pa0000000, 2026-10, pipeline lab-csv-import

## Answer: we did not pass, and we did not fail. TSS is review-required.
The engine cannot show compliance or non-compliance for TSS. The non-detect
(<80 mg/L) has a reporting limit above both TSS limits (30 monthly avg, 60
daily max). A human must decide. Separately, pH and Flow have no data, so the
month cannot be called compliant in any case.

## Frame
- Permit: pa0000000 (PA0000000, **fictional placeholder permit**, not a real permit)
- Pipeline: lab-csv-import (map Analyte->parameter, ug/L->mg/L, non-detect `<` treat-as report-limit, require sample_date/method)
- Period: 2026-10. Source: evals/.../nondetect-review/inputs/records.json
- Question: did the month pass, given one TSS non-detect?

## Input validation
- 2 records (n1, n2), both outfall 1, TSS, mg/L, method SM2540D, dates in 2026-10, ids unique, all required fields present. No NODI codes in the source. No problems.
- n1 = `<80` (non-detect), n2 = `10` (detected).

## Verdict line
4 limits: 0 pass, 0 exceedance, 2 review-required, 2 missing-data.
Not "compliant".

## Findings
| Outfall | Parameter | Clause | Computed | Limit | Status | Samples | Reason (engine) |
|---|---|---|---|---|---|---|---|
| 1 | TSS | monthly-avg (mean <= limit) | <45 | 30 mg/L | review-required | n1, n2 | exceeds limit only because non-detect n1 is used at its reporting limit; with it taken as zero the value is 5. Compliance cannot be demonstrated or refuted - human review required. |
| 1 | TSS | daily-max (max <= limit) | <80 | 60 mg/L | review-required | n1, n2 | same: exceeds only because n1 used at RL; with zero the value is 10. |
| 1 | pH | range 6..9 | n/a | 6..9 s.u. | missing-data | none | Only 0 samples found for pH in 2026-10; 5 required. |
| 1 | Flow | monthly-avg | n/a | 0.5 MGD | missing-data | none | Only 0 samples found for Flow in 2026-10. |

Trace checks: sample_values 80 and 10 -> mean 45 = (80+10)/2, carried as `<45`
(qualified because a non-detect is in the set); max = 80 qualified. Limits and
comparisons match the permit file. Pipeline provenance shows n1 `<80` ->
non_detect true, value 80 "treated as report-limit". Zero-substitution is not
applied (it requires a permit basis); the "would be 5" figure is the engine's
diagnostic only, not a result.

Why not exceedance: the only data above the limit is the non-detect at its RL.
The detected value (10) is well under both limits. Why not pass: the lab's RL
(80) is above the permit limits, so the true value could be anywhere from 0 to
80. The sample was apparently analysed with a method/dilution too insensitive
for these limits.

## Reconciliation
Records in 2 = used in results 2 (n1, n2 both in TSS results) + rejected 0 +
out-of-period 0. No dropped records.

## Not evaluated
- Weekly averages, mass loads (lbs/day), percent removal, WET.
- Sample frequency beyond count (TSS: 2 samples present vs 2 per-month required, count met only; spacing not checked; pH required count is computed as 5 by the engine's per-week approximation).
- Late submission, NODI validity, whether SM2540D at an RL of 80 mg/L is an acceptable method vs the permit's required QL.
- Any other outfalls/parameters the real permit would require.

## Data quality
No rejections. Note pH and Flow have no records at all in the input (the
file contains TSS only), so the missing-data results may reflect an incomplete
input file rather than missing monitoring.

## Required human decisions
1. TSS review-required: obtain the lab's QL/MDL and confirm whether an 80 mg/L
   reporting limit is valid for this permit. Under PA convention report as
   `<QL` (monthly average `<45`, daily max `<80`); zero may replace the RL
   only if the permit limit is below the most sensitive detection limit and the
   parameter is in 25 Pa. Code Ch. 16 App. A Tables 2A/2B (not shown here).
   Consider re-analysis with a lower RL if holding time allows (likely not for
   a past sample) and review with the permit's Part C. Do not report as pass.
2. pH and Flow missing-data: supply data, or resolve to a PA NODI code with
   explanation (E = violation, GG = conditional sampling not triggered, FF =
   extenuating circumstances) or no-discharge. Do not auto-select.
3. No daily-max exceedance by detected data, so no 24-hour/5-day notification
   candidate was identified. SNC not assessed.

## Reproduce
```
export PATH="$PATH:/c/Program Files/Racket"
racket dsl/main.rkt run --permit dsl/permit/permits/pa0000000.rkt \
  --pipeline dsl/pipeline/pipelines/lab-csv-import.rkt --period 2026-10 \
  < evals/evaluate-dmr-data/iteration-1/nondetect-review/inputs/records.json
```
- pa0000000.rkt SHA-256 6c4823e131ff56c01449b028775c185eda33398966d0c9871886bdf1d91c109c
- lab-csv-import.rkt SHA-256 fa5a89330e51675fb302c360b90ac153c723f2c871eb9959878841885fcc7ccf
- schema_version 2, period 2026-10
