# DMR evaluation: pa0000000, 2026-10, pipeline lab-csv-import

Note: `pa0000000` is a FICTIONAL placeholder permit. Nothing here is a real compliance determination.

## 0. Frame
- Permit: `dsl/permit/permits/pa0000000.rkt`; pipeline: `dsl/pipeline/pipelines/lab-csv-import.rkt`; period 2026-10.
- Source: `evals/.../nd-mixed-conversion/inputs/records.json` (4 TSS records, outfall 1).
- Question: does October 2026 TSS (with one non-detect and one ug/L result) comply?

## 1. Input validation
All 4 records have unique id, outfall, Analyte, value, unit, ISO sample_date and method. No `parameter` column, no NODI codes. All 4 fall inside 2026-10. Observations:
- m1 `<10 mg/L` is a non-detect (reporting limit 10).
- m4 `12000 ug/L` is in the wrong unit for the permit (mg/L); the pipeline has a `convert-units ug/L -> mg/L` step.
- Outfall is given as `1`; permit outfall is `001`. The engine matched them.
- Samples are weekly (Oct 4, 11, 18, 25), 4 in total, only TSS.

## 2. Engine run
```
racket dsl/main.rkt run --permit dsl/permit/permits/pa0000000.rkt \
  --pipeline dsl/pipeline/pipelines/lab-csv-import.rkt --period 2026-10 < records.json
```
Engine ran (no error envelope). Racket at `C:\Program Files\Racket\racket.exe`.

## 3. Reconciliation
records in 4 = used in results 4 (m1-m4, both TSS results) + rejected 0 + out-of-period 0. All four appear in provenance. No mismatch.

## 4. Verdict
4 limit results: 0 pass, 1 exceedance, 1 review-required, 2 missing-data. **Not compliant / cannot be called compliant.**

| Outfall | Parameter | Clause | Computed | Limit | Status | Samples | Engine reason |
|---|---|---|---|---|---|---|---|
| 1 | TSS | monthly-avg (mean <= limit) | <127/4 (=31.75, qualified) | 30 mg/L | review-required | m1-m4 | exceeds limit only because non-detect m1 is used at its reporting limit; with it at zero the value is 117/4 (29.25). Compliance cannot be demonstrated or refuted - human review required. |
| 1 | TSS | daily-max (max <= limit) | 65 | 60 mg/L | exceedance | m1-m4 | daily-max exceeds the permit limit (computed 65). Non-detect m1 used at reporting limit. |
| 1 | pH | range 6.0-9.0 | n/a | 6..9 | missing-data | none | Only 0 samples found for pH in 2026-10; 5 required. |
| 1 | Flow | monthly-avg | n/a | 0.5 MGD | missing-data | none | Only 0 samples found for Flow in 2026-10. |

## 5. What passed / didn't
- Passed: the data handling. All records accepted, no rejections, and the ug/L record was converted correctly (m4: 12000 ug/L -> 12 mg/L, provenance note "converted 12000 ug/L to 12 mg/L"). Other records were left unchanged (mg/L did not match ug/L). Non-detect m1 was treated as report-limit -> 10 and flagged `non_detect`. No limit has status `pass`.
- Hand check of the trace (I am verifying, not replacing, the engine): values 10, 40, 65, 12 -> sum 127, mean 127/4 = 31.75 > 30; with m1 = 0 mean 29.25 <= 30, which is exactly why it is review-required not exceedance. Daily max 65 > 60 and it comes from m3 (a detected value, 65 mg/L, 2026-10-18), so the daily-max exceedance does not depend on the non-detect.
- Mean effect of conversion: had m4 NOT been converted, 12000 would have been compared as mg/L and wrecked the average; it was converted, so the average is correct.

## 6. Not evaluated
Weekly averages, mass loads (lbs/day), percent removal, WET, sample-frequency beyond count (pH requirement of 5 is `count x ceil(31/7)`, an approximation), late submission, NODI validity. Flow's `report-only` clause produced no separate result row; only its monthly-avg row (missing-data) appears - worth confirming in engine behavior.

## 7. Required human decisions / next steps
1. **TSS monthly average (review-required)**: a human must decide. The reporting limit of the non-detect (10 mg/L) is below the permit limit, but the average only fails because the ND is counted at its RL. Under PA guidance, report the statistic as `<31.75` (qualified, `<127/4`). Zero substitution is only allowed if the permit limit is below the most sensitive detection limit and the parameter is in 25 Pa. Code Ch. 16 App. A tables 2A/2B - not the case here per this data, so do not change `treat-as` to zero to make it pass. Possible follow-up: ask the lab whether a lower RL was achievable; the mean passes only if the ND is counted at <= 3 mg/L (117 + x <= 120), so the 10 mg/L RL is too high to demonstrate compliance.
2. **TSS daily-max exceedance (65 vs 60 mg/L, m3, 2026-10-18)**: real breach by a detected value. Confirm the result and QA with the lab; if confirmed, it is a limit exceedance to report on the DMR with a comment. Check whether TSS is a pollutant that triggers 24-hour / 5-day notification under the actual permit (not modeled; permit is fictional). Do not call it an SNC determination.
3. **pH and Flow missing-data**: supply the results, or record a PA NODI code, to be chosen by a human: `E` (missed sample - a violation, needs Form 3800-FM-BCW0440), `GG` (conditional sampling condition not met), `FF` (explained), or no-discharge if applicable. Do not auto-select.
4. Also confirm m4 really came back in ug/L (and not a mislabelled mg/L; 12000 mg/L TSS would be implausible) - the engine's conversion is correct for the stated unit.
5. TSS had 4 samples against a requirement of 2 per month; all 4 must stay in the average (dropping samples is not allowed).

## 8. Reproduce
```
cd C:\Users\jcoff\attesta
"C:\Program Files\Racket\racket.exe" dsl/main.rkt run --permit dsl/permit/permits/pa0000000.rkt --pipeline dsl/pipeline/pipelines/lab-csv-import.rkt --period 2026-10 < evals/evaluate-dmr-data/iteration-2/nd-mixed-conversion/inputs/records.json
```
- pa0000000.rkt SHA-256: 6c4823e131ff56c01449b028775c185eda33398966d0c9871886bdf1d91c109c
- lab-csv-import.rkt SHA-256: fa5a89330e51675fb302c360b90ac153c723f2c871eb9959878841885fcc7ccf
- Period 2026-10, schema_version 2. Run was not persisted to Django (direct CLI run).
