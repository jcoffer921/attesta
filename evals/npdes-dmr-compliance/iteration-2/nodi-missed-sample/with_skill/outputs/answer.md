# Missed TSS sample at Outfall 002 (PA eDMR)

## Short answer

- Report the one TSS result you do have (value, or `<QL` if non-detect). Do not leave the row blank and do not enter 0 or "No Discharge".
- The missing second sample is a missed sample / failed analysis. In PA eDMR that is NODI code `E`, and per PA DEP guidance **E is itself a violation**, not an excuse. It needs a comment and a Non-Compliance Reporting Form 3800-FM-BCW0440.
- Yes, treat it as a violation (a sampling-frequency / monitoring violation), even though no limit was exceeded.

## What to enter

1. **Reported value.** One sample was collected, so report it as the TSS value for the period.
   - Monthly average: with a single result the average is that result. If it is a non-detect, report `<QL`, not `0` or "ND".
   - Daily maximum: that same value.
   - Do not invent or estimate a second sample.
2. **The missing sample.** Because a numeric value and a NODI code cannot both be on the same row, how E is applied depends on how your eDMR structures the row (the average/max rows carry the one real value). Check how the eDMR handles "samples taken vs required" and the sample-count field for outfall 002. Use `E` only where no value can be reported for a required row.
   - Do not use `FF`, which is for no data not covered by E or GG, with extenuating circumstances. An autosampler failure is an equipment failure and DEP guidance puts missed samples and analytical failures under E.
   - Do not use `GG`; that is for conditional sampling where the condition was not met.
   - Do not use "No Discharge"; there was a discharge, you just did not sample it twice.
3. **Comment field.** State the facts plainly: the autosampler failure, the dates (first half of September), that one sample was collected on [date], what was done to restore sampling, and corrective action.
4. **Form 3800-FM-BCW0440.** File the Non-Compliance Reporting Form with the DMR.

## Is it a violation?

- **Yes, as a monitoring/reporting violation.** Under PA guidance E is a violation. In general NPDES terms, taking fewer samples than the permit requires is a sample-frequency violation regardless of whether the one result met the limit.
- **It is not an effluent exceedance.** A single result under the limit is still a pass against the limit. The problem is the missed monitoring, not the discharge quality. Keep these separate in your explanation to DEP.
- **Notification.** A missed sample is not one of the 24-hour/5-day oral/written notice triggers (those are for endangerment, bypass, upset, or max daily limit violations), but all noncompliance must be reported with the DMR, which is what the comment and 0440 form do.
- **SNC.** Significant noncompliance is assigned by DEP/EPA, not by you. Reporting violations can count toward SNC, so a one-off is low risk but a pattern is not.

## Caveats and things to confirm

- The permit is the authority. Check Part C of the permit for the TSS sample frequency, sample type, and any provision on equipment failure or alternate sampling (for example, a grab sample substitute for a failed composite).
- PA DEP guidance cited is dated in places and one older mining FAQ says otherwise on E; follow the current eDMR page and your permit.
- I have not verified the exact PA eDMR mechanics for entering E alongside a reported value, nor PA's precise late/reporting-violation thresholds. Confirm with your DEP regional office or the eDMR help if the form will not accept the entry.
- Attesta does not currently model sample-frequency violations, so its `pass` on this row would not capture this issue. Do not rely on a "pass" status here.
- A human with signatory authority should approve and certify the final entry.
