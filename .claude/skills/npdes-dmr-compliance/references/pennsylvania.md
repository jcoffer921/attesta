# Pennsylvania (PA DEP) specifics

Evidence tags: **[V]** verified against a primary or EPA/state source (see `sources.md`); **[G]** general domain knowledge, confirm against the actual permit before using it in user-facing text; **[?]** open question, do not guess.

Tag [PA] = from PA DEP guidance. Several sources are dated (DMR instructions 12/2016, overview 5/2012); the permit's Part C and DEP's current eDMR page win.

**Non-detects [PA]**
- A lab result of "ND" or `<x` means below the quantitation limit (QL, a.k.a.
  reporting limit). Report it as `<QL`, never as `0` or "ND".
- For statistics (monthly average etc.) ignore the `<` symbol and use
  detected results plus the reporting limit for each non-detect.
- Put `<` on the **statistical result** if the data set has at least one
  non-detect. Example: `<1.0, 2.0, <1.0, 1.0` -> average `<1.3`.
- If every result in the period is non-detect, report `<QL`.
- Zero may replace the reporting limit **only** when the permit has a limit
  below the most sensitive detection limit and the parameter is in
  25 Pa. Code Ch. 16 App. A Tables 2A/2B.
- Bacteria: geometric mean ignoring qualifier symbols, keep the symbol on
  the result; `>` takes precedence over `<` in a mixed set; note volume
  filtered in comments.

Engine behavior (implemented, schema_version 3): `treat-as report-limit`
is the PA convention; `zero` requires `(basis "...")`; `half-mdl` is gone.
A monthly average with any non-detect is reported qualified (`<5/4`). If a
limit is exceeded only because non-detects were taken at their reporting
limits (it would pass with them at zero), status is `review-required`, not
`exceedance`. Detected values alone over the limit remain `exceedance`.

**NODI codes in PA [PA]** - PA eDMR uses its own codes, not the EPA letter
table above. Do not leave a parameter blank when there is no data.
- `E` - missed sample / analytical failure: **a violation**, needs a
  comment and Non-Compliance Reporting Form 3800-FM-BCW0440. (An older
  mining FAQ says otherwise; current guidance controls.)
- `GG` - conditional sampling, condition not met (also used instead of "No
  Discharge" for non-representative outfalls when the permit allows
  representative sampling).
- `FF` - no data not covered by E or GG; extenuating circumstances, with
  explanation.
- "No Discharge" is only for a period with no discharge at all - not for
  unsampled/unanalyzed periods.
- Every active permittee must submit a DMR even with no discharge.
- An Attesta `under-sampled` row (e.g. 4 of 5 required weekly pH samples)
  is the missed-sample situation: the shortfall is reported with code `E`
  (a violation), a comment, and Form 3800-FM-BCW0440, while the samples
  that were taken are still reported and evaluated.
- Mapping: Attesta `missing-data` must be resolved to one of: reported
  value, `E` (violation), `GG` (not required), `FF` (explained) or
  no-discharge. Do not auto-select; ask the human.

**Still unverified for PA [?]**
- Text of 25 Pa. Code Ch. 92a reporting provisions (not retrieved).
- Whether `0` vs `<QL` handling differs for specific parameters in a
  given permit's Part C.
- PA's exact late-DMR / reporting-violation thresholds.
- Full list of PA eDMR NODI codes beyond E, GG, FF.

## Other open items

- Whether weekly averages, mass loads, and sampling-frequency checks are
  in scope for the submission.
- Full Group I/II pollutant lists (only examples verified).
