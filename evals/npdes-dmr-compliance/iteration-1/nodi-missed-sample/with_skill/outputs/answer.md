**Short answer:** Report the one TSS sample you actually have as a real value, and use NODI code `E` only for the sample you could not collect. Yes, treat the missed sample as a violation. PA DEP guidance treats `E` as a violation, not an excuse.

**What to enter on the eDMR**

1. **Do not leave the field blank**, and do not use "No Discharge". "No Discharge" is only for a period with no discharge at all. You did discharge and simply didn't sample.
2. **Enter the result you have.** The one valid TSS sample goes in as a numeric value. A row takes a value or a NODI code, never both. If it is non-detect, report it as `<QL`, not `0` or "ND".
3. **Use `E` (missed sample / analytical failure) for the missing sample.** This applies to the sample you didn't collect because the autosampler failed.
   - Add a comment explaining the autosampler failure and the dates.
   - File the Non-Compliance Reporting Form 3800-FM-BCW0440.
4. **Watch how the statistic is handled.** If the permit's TSS limit is a monthly average, the average is computed from the samples you actually have. Never drop or invent samples to change an average. Check how the eDMR wants the average, max and sample count shown when only one sample exists. The permit's Part C and DEP's current eDMR page control.
5. `FF` (no data, extenuating circumstances) is a possible alternative if the permit and DEP allow it. Do not pick it just to avoid `E`, because the guidance puts "missed sample / analytical failure" under `E`. If you think a different code applies, confirm with your DEP regional office before submitting.

**Does it count as a violation?**

Yes, in the sense that matters here. Under PA DEP guidance, `E` is a violation. Taking one sample when the permit requires two is a sampling-frequency (monitoring/reporting) violation, not an effluent-limit exceedance. Nothing here suggests TSS exceeded its limit, so there is no exceedance from this event alone.

Points worth knowing:
- **Being a violation is not the same as SNC.** Significant noncompliance is assigned by EPA/DEP, not by you. Reporting violations can count toward SNC, but a single missed sample is not the typical trigger.
- **Reporting it honestly is the right path.** Report all noncompliance with the DMR. The `E` code, the comment and the 3800-FM-BCW0440 form are how you do that. Reporting it does not erase the violation, but concealing it is worse.
- **A broken autosampler is generally not a 24-hour/5-day notification event** on its own, unless it also involved something that endangers health or the environment. Check your permit's Part A/B conditions to confirm.
- **Keep records:** the equipment failure log, repair records and calibration, retained at least 3 years.

**Caveats**
- The PA guidance I'm relying on is partly dated (DMR instructions 12/2016), and I haven't verified the exact late-DMR or reporting-violation thresholds in 25 Pa. Code Ch. 92a. Your permit and DEP's current eDMR guidance win.
- I don't have your permit, so I can't confirm whether outfall 002 TSS is a monthly average, whether the 2 samples/month frequency has any permit-specific relief, or the exact limit. A grab-vs-composite requirement may matter too, since your autosampler was presumably taking composites.
- Going forward, ask DEP whether any alternate or backup sampling method (for example manual composite or grab sampling) is acceptable if the autosampler fails again, so you avoid another missed sample.
