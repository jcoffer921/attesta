# October 2026 DMR evaluation: permit PA0000000, outfall 001, pipeline lab-csv-import

Command: `racket dsl/main.rkt run --permit dsl/permit/permits/pa0000000.rkt --pipeline dsl/pipeline/pipelines/lab-csv-import.rkt --period 2026-10` (9 input records).

Note: PA0000000 is a fictional placeholder permit (per its source header), so this is an engine exercise, not a real regulatory determination.

## Verdict: NOT compliant

| Parameter | Clause | Result | Computed vs limit | Status |
|---|---|---|---|---|
| TSS (r1,r2,r3: 20, 35, 62 mg/L) | monthly-avg | mean 39 | limit 30 mg/L | EXCEEDANCE |
| TSS | daily-max | max 62 (r3, 2026-10-16) | limit 60 mg/L | EXCEEDANCE |
| pH (p1-p4: 7.1, 7.2, 6.9, 7.0) | range 6.0-9.0 | n/a | only 4 samples, 5 required | MISSING-DATA |
| Flow (f1: 0.4 MGD) | monthly-avg | 0.4 | 0.5 (report-only) | REPORT-ONLY |

## Findings

1. TSS exceeds both the monthly average (39 vs 30) and the daily max (62 vs 60). Both are genuine violations. The 62 mg/L sample drives both; the 20 and 35 are individually fine but the average still fails.
2. pH: all four accepted values are within 6.0-9.0, so there is no pH excursion. But the engine could not give pass because the weekly frequency requirement (1 per week, 5 weeks in Oct 2026 under the engine's ceil(31/7) simplification) was not met: 4 of 5.
3. Cause of the pH shortfall: p5 (2026-10-29, pH 7.3) was rejected by the pipeline's `require-field sample_date method` step because the `method` field is missing. It was not silently dropped; it appears in `rejections`. If the lab supplies the analytical method for p5 and it is re-run, pH would very likely be 5/5 and pass (7.3 is in range). This is a data-completeness fix, not a result to fabricate.
4. Flow: 0.4 MGD monthly average is below the 0.5 reference value, but the clause is report-only so no pass/fail applies; just report the value.
5. TSS sample frequency (2 per month): 3 samples submitted, satisfied.

## Other observations

- `convert-units ug/L -> mg/L` did not fire on any record (all already mg/L, s.u., MGD); no non-detects present.
- r3 is dated 2026-10-16 and p-samples run through 10-29; today's date is 2026-10-15, so r3 (10-16), p4 (10-22) and p5 (10-29) are future-dated relative to the run date. That is worth checking as a likely data-entry or test-data issue before anyone files.
- Samples sit in outfall 1 (permit outfall 001); all matched.

## Recommended actions

- Treat TSS monthly-avg and daily-max as reportable exceedances; evaluate notification/SNC obligations under the permit and PA DEP rules and investigate cause.
- Obtain method for p5 and re-run to clear the pH missing-data; if not obtainable, the missing sample is a monitoring-frequency violation to report with an explanation.
- Verify the future-dated sample dates.
