# DMR evaluation: PA0000000, outfall 001, 2026-10, pipeline lab-csv-import

Run: `racket dsl/main.rkt run --permit dsl/permit/permits/pa0000000.rkt --pipeline dsl/pipeline/pipelines/lab-csv-import.rkt --period 2026-10` with records.json on stdin.
Note: PA0000000 is a fictional placeholder permit (per its file header), so these results are not a real compliance determination.

## Pipeline (4 records in, 4 through, 0 rejections)

| id | raw | after pipeline | what happened |
|----|-----|----------------|---------------|
| m1 | `<10` mg/L | 10 mg/L, non_detect=true | Non-detect; `treat-as report-limit` substitutes 10 |
| m2 | 40 mg/L | 40 | unchanged |
| m3 | 65 mg/L | 65 | unchanged |
| m4 | 12000 ug/L | 12 mg/L | converted (ug/L -> mg/L, /1000) |

All required fields (sample_date, method) present; `Analyte` was renamed to `parameter` for each record. Nothing was silently dropped.

## Permit results

| Parameter / clause | Computed | Limit | Status |
|---|---|---|---|
| TSS monthly-avg | mean(10, 40, 65, 12) = 127/4 = 31.75 mg/L | <= 30 | **review-required** |
| TSS daily-max | 65 mg/L (m3, 2026-10-18) | <= 60 | **exceedance** |
| pH range 6.0-9.0 | no samples | 5 samples required (1 per week) | **missing-data** |
| Flow monthly-avg | no samples | <= 0.5 MGD | **missing-data** |

TSS sample frequency (2 per month) is met with 4 samples; there is no separate failure for it.

## What passed
Nothing in the substantive limits passed outright. What did work: all 4 TSS records were ingested and normalized cleanly, the ug/L value converted correctly (12000 ug/L = 12 mg/L), and TSS sample count satisfies frequency.

## What did not pass, and why

1. **TSS daily-max: exceedance.** m3 = 65 mg/L > 60. This is a real detected value, not influenced by the non-detect or the conversion. This is a genuine violation for 2026-10-18 and stands regardless of how m1 is treated.
2. **TSS monthly-avg: review-required (not a clean fail).** With m1 at its reporting limit (10) the mean is 31.75, over 30. If m1 is treated as zero the mean is 29.25, under 30. The engine will not decide this for you because the answer depends entirely on the non-detect treatment. Note that m4 only contributes correctly because it was converted; had 12000 been read as mg/L the average would be wildly wrong, so the conversion matters here.
3. **pH and Flow: missing-data.** records.json has no pH or Flow rows at all. pH needs 5 samples for October (1 per week), Flow needs a monthly average. These are data gaps, not exceedances, but they are reportable deficiencies if the data was actually never collected.

## What to do next

1. **Treat the daily-max exceedance as a violation.** Verify m3 (65 mg/L, 2026-10-18) against the lab report to rule out a transcription error. If confirmed, follow your notification/corrective-action procedures and report it on the DMR (check whether any 24-hour/5-day reporting trigger applies under the actual permit; this placeholder permit does not say).
2. **Resolve the monthly-avg question with a human decision.** Confirm the m1 reporting limit (<10 mg/L) from the lab and check what the permit / PA DEP guidance says for averaging non-detects (substitution of zero vs. the QL). A reporting limit of 10 is also fairly high relative to a 30 mg/L limit; if the lab could have achieved a lower QL, ask whether a re-analysis or lower-QL result is available. Record the decision and rationale.
3. **Obtain the missing pH and Flow data** for October (5 pH samples, flow records). If they were measured, add them to the input and re-run; if they were not, document the missed monitoring and use the appropriate no-data indicator / notify DEP.
4. **Fix input hygiene before the next run.** The m4 ug/L record was only handled because the pipeline has a `convert-units ug/L -> mg/L` step; ask the lab to report in mg/L consistently. Also confirm the sample dates: 2026-10-18 and 2026-10-25 are in the future relative to today (2026-10-15), so those results (m3, m4) may be mis-dated or the data is test data; verify before relying on the exceedance.
5. Re-run the engine after corrections and keep the provenance output as the audit trail.
