# October 2026 DMR evaluation - permit pa0000000 (fictional), pipeline lab-csv-import

**Question:** does October 2026 comply? **Answer: No.** The engine returned 2 exceedances and 1 missing-data result. This is not a clean month, and the missing pH sample is caused by a rejected record that needs a human decision.

Source: evals/evaluate-dmr-data/iteration-2/october-mixed/inputs/records.json (9 records). Period 2026-10. `pa0000000` is a fictional permit shipped with Attesta.

## 1. Verdict
4 limits evaluated: 2 exceedance, 1 missing-data, 1 report-only, 0 pass.

## 2. Findings

| Outfall | Parameter | Clause | Computed | Limit | Status | Samples | Engine reason |
|---|---|---|---|---|---|---|---|
| 1 | TSS | monthly-avg (mean <= limit) | 39 | 30 | exceedance | r1 20, r2 35, r3 62 | monthly-avg exceeds the permit limit (computed 39). |
| 1 | TSS | daily-max (max <= limit) | 62 | 60 | exceedance | r1, r2, r3 | daily-max exceeds the permit limit (computed 62). |
| 1 | pH | range 6..9 | n/a | 6..9 | missing-data | p1 7.1, p2 7.2, p3 6.9, p4 7.0 | Only 4 sample(s) found for pH in 2026-10; 5 required. |
| 1 | Flow | monthly-avg | 2/5 (0.4 MGD) | report-only | report-only | f1 | no pass/fail applies. |

Values are reproducible from sample_values: TSS mean (20+35+62)/3 = 39, max 62. The only daily-max breach is r3 (62 mg/L, 2026-10-16). Exact-rational output is shown as the engine returned it (71/10 = 7.1, 2/5 = 0.4).

## 3. Not evaluated
Weekly averages, mass loads, percent removal, WET, sample frequency beyond count (approximate per-week count), late submission, validity of NODI codes. No NODI codes were supplied. The pH range result is missing-data, so no pH verdict exists either way; the four pH values received were all within 6..9.

## 4. Data quality
- Reconciliation: 9 in = 8 used in results (r1-r3, p1-p4, f1) + 1 rejected (p5) + 0 out-of-period. Counts match; nothing dropped silently.
- Rejection: **p5** (pH 7.3, 2026-10-29) rejected at require-field: "missing required field(s): (method)". The record had no `method`. I did not add one. This rejection is the reason pH shows 4 of 5 samples.
- Outfall values are integers (1), not strings; the engine accepted them.
- Units mg/L, s.u., MGD matched the permit; no conversion was needed (convert-units steps left values unchanged).

## 5. Required human decisions
1. **p5**: obtain the analytical method from the lab and re-submit the record. If it is supplied and in range, pH likely moves to pass, but that must be re-run through the engine; do not assume. If the sample cannot be recovered, a missing-data / NODI decision is needed (PA: `E` is itself a violation; see GG, FF).
2. **TSS exceedances**: monthly average 39 vs 30 and daily max 62 vs 60 are computed exceedances. Review for permit-driven notification/reporting (24-hour/5-day candidates depend on the pollutant lists in the actual permit; TSS applicability not confirmed). SNC discussion is indicative only and not assessed here.
3. Confirm that three TSS samples satisfy the required frequency; the engine did not flag TSS as missing-data.

## 6. Reproduce
```
racket dsl/main.rkt run --permit dsl/permit/permits/pa0000000.rkt \
  --pipeline dsl/pipeline/pipelines/lab-csv-import.rkt --period 2026-10 < records.json
```
(run with C:\Program Files\Racket\racket.exe; input is the records.json file, schema_version 2.) Output schema_version 2; engine output was not edited.

- pa0000000.rkt SHA-256: 6c4823e131ff56c01449b028775c185eda33398966d0c9871886bdf1d91c109c
- lab-csv-import.rkt SHA-256: fa5a89330e51675fb302c360b90ac153c723f2c871eb9959878841885fcc7ccf
