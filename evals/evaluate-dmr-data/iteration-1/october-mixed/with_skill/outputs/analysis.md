# October 2026 DMR evaluation - permit PA0000000 (fictional placeholder)

## 0. Frame
- Permit: `pa0000000` (fictional, invented limits; not a real PA permit)
- Pipeline: `lab-csv-import`; period: `2026-10`
- Source: `evals/evaluate-dmr-data/iteration-1/october-mixed/inputs/records.json` (9 records)
- Question: does October 2026 comply?

## 1. Verdict
**Not compliant - cannot be called compliant.** 4 limit rows evaluated: 2 exceedance, 1 missing-data, 1 report-only, 0 pass.

## 2. Findings
| Outfall | Parameter | Clause | Computed | Limit | Status | Samples | Engine reason |
|---|---|---|---|---|---|---|---|
| 1 | TSS | monthly-avg (mean <= limit) | 39 mg/L | 30 mg/L | exceedance | r1,r2,r3 (20,35,62) | monthly-avg exceeds the permit limit (computed 39). |
| 1 | TSS | daily-max (max <= limit) | 62 mg/L | 60 mg/L | exceedance | r1,r2,r3 | daily-max exceeds the permit limit (computed 62). |
| 1 | pH | range 6.0..9.0 | n/a | 6..9 | missing-data | p1-p4 (7.1,7.2,6.9,7.0) | Only 4 sample(s) found for pH in 2026-10; 5 required. |
| 1 | Flow | monthly-avg | 0.4 MGD (2/5) | 0.5 MGD (1/2) | report-only | f1 | limit is report-only, no pass/fail applies. |

The TSS mean (20+35+62)/3 = 39 reproduces from the sample values. The exceedance is driven by r3 (62 mg/L, 2026-10-16), which also breaches the daily max.

## 3. Record reconciliation
9 in = 8 used in results (r1-r3, p1-p4, f1) + 1 rejected (p5) + 0 out-of-period. Balanced; nothing silently dropped.

## 4. Data quality
- **p5 (pH 7.3, 2026-10-29) rejected**: `missing required field(s): (method)`. This rejection is why pH has 4 samples instead of 5 and shows missing-data. The value is a normal in-range pH, but the engine does not use it until the lab method is supplied. Fix the input (add method, e.g. SM4500H, only if the lab confirms it) and re-run; I did not alter it.
- All other records had all fields present, ISO dates, plain decimal values, no non-detects, units matched the permit (convert-units step was a no-op for all).
- Outfall is `1` in the data and `001` in the permit; the engine matched them.

## 5. Not evaluated
Weekly averages, mass loads, percent removal, WET, sample-frequency beyond the count check (per-week frequency is approximate: count x ceil(days/7)), late submission, NODI validity. Also note TSS sample frequency (2/month) was met with 3 samples.

## 6. Required human decisions
- TSS monthly-avg and daily-max exceedances: report as exceedances and decide on corrective action. For the daily-max breach (62 vs 60), check whether TSS is a pollutant that triggers 24-hour/5-day notification under the permit; confirm against the real permit (this one is fictional). Indicative only; no SNC conclusion drawn.
- pH missing-data: either supply the method for p5 and re-run, or, if the sample is genuinely invalid/absent, a NODI code is needed (PA: `E` is itself a violation; `GG`/`FF` per reference). The engine does not assume any NODI excuses it.
- Flow 0.4 MGD is report-only (also numerically under 0.5), no action.

## 7. Reproduce
```
racket dsl/main.rkt run --permit dsl/permit/permits/pa0000000.rkt --pipeline dsl/pipeline/pipelines/lab-csv-import.rkt --period 2026-10 < evals/evaluate-dmr-data/iteration-1/october-mixed/inputs/records.json
```
(Racket at `C:\Program Files\Racket`, not on PATH.) Exit 0, schema_version 2.
- permit SHA-256: 6c4823e131ff56c01449b028775c185eda33398966d0c9871886bdf1d91c109c
- pipeline SHA-256: fa5a89330e51675fb302c360b90ac153c723f2c871eb9959878841885fcc7ccf
