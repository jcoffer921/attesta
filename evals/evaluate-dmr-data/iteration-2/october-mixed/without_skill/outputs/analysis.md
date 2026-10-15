# October 2026 DMR evaluation - permit PA0000000, outfall 001

Command: `racket dsl/main.rkt run --permit dsl/permit/permits/pa0000000.rkt --pipeline dsl/pipeline/pipelines/lab-csv-import.rkt --period 2026-10` with the 9 records from records.json on stdin.

## Verdict: NOT compliant

Two limits are exceeded (TSS monthly average and TSS daily maximum), and pH cannot be shown compliant because one sample was rejected.

## Engine results

| Parameter | Clause | Limit | Computed | Status |
|---|---|---|---|---|
| TSS | monthly-avg | 30 mg/L | 39 mg/L (20, 35, 62) | EXCEEDANCE |
| TSS | daily-max | 60 mg/L | 62 mg/L (r3) | EXCEEDANCE |
| pH | range | 6.0-9.0 s.u. | n/a | MISSING-DATA (4 of 5 required weekly samples) |
| Flow | monthly-avg | 0.5 MGD (report-only) | 0.4 MGD | REPORT-ONLY |

## Details

- **TSS**: mean of 20, 35, 62 = 39 mg/L > 30; max 62 > 60. Both clauses fail. The 2 per month sample frequency is satisfied (3 samples).
- **pH**: all five pH readings (7.1, 7.2, 6.9, 7.0, 7.3) are inside 6.0-9.0, so there is no pH excursion. However, record p5 (2026-10-29) has no `method` field and was rejected by the pipeline's `require-field sample_date method` step (rejection: "missing required field(s): (method)"). That leaves 4 pH samples vs. 5 required (1 per week, ceil(31/7) = 5), so the engine reports missing-data. Fix: obtain the analytical method from the lab (presumably SM4500H) and re-run; if corrected, pH should pass. Do not just edit the record without lab confirmation.
- **Flow**: 0.4 MGD, report-only, no pass/fail. (Also under 0.5 anyway.)

## Caveats

- r3 (TSS 62 mg/L) is dated 2026-10-16, which is after today's date (2026-10-15). Likely a date typo or a pre-dated entry; verify with the lab. If it were removed, the TSS average would be 27.5 (passes) and daily max 35 (passes), and TSS would still meet the 2/month frequency - so this single record decides the TSS outcome. Do not drop it without confirming; the engine as given treats it as a valid sample.
- The permit file is a fictional placeholder (per its header), so this is an engine exercise, not a real regulatory determination.
- Weekly frequency check is the engine's simplification (count x ceil(days/7)), not real week boundaries.
- Because of the TSS exceedances, real-world follow-up (notification/corrective-action determination) would be required; the engine does not decide that.
- No repository files were modified.
