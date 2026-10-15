---
name: npdes-dmr-compliance
description: NPDES/DMR domain knowledge for Attesta - what a Discharge Monitoring Report contains, how limits are judged (pass, exceedance, review-required, missing-data), non-detect (<QL) handling, NODI codes, 24-hour/5-day notification and SNC criteria, and Pennsylvania DEP rules. Use whenever work touches compliance rules, DMR or report output, status badges, non-detects, lab results below detection limit, NODI/eDMR codes, violations, or AI explanations of a compliance result - even if the user never says "NPDES" or "DMR".
---

# NPDES / DMR compliance

Read this before changing anything that decides, displays, or explains
compliance. Evidence tags: **[V]** verified against a primary or EPA/state
source (see `references/sources.md`); **[G]** general domain knowledge -
confirm against the actual permit before using it in user-facing text;
**[?]** open question, do not guess.

**The permit is the authority.** Limits, statistical bases, units, sampling
frequency, non-detect handling and due dates all come from the specific
permit; state programs differ. Never hard-code a federal default where the
permit could say otherwise. [V]

## Which reference to read

| Situation | Read |
|---|---|
| Working on or explaining a Pennsylvania permit, `<QL`, PA NODI codes (E, GG, FF) | `references/pennsylvania.md` |
| Choosing or explaining a NODI code | `references/nodi-codes.md` |
| Notification deadlines, record retention, SNC / TRC criteria | `references/violations-snc.md` |
| Citing a source | `references/sources.md` |

Sections below are the core that applies to every task.

## What a DMR is

- EPA's uniform national form (40 CFR 122.2); results are reported at the
  intervals the permit sets, electronically (NetDMR or a state eDMR system)
  unless waived. [V]
- One DMR per outfall (monitoring point) per monitoring period; each
  parameter has one or more limit rows (e.g. monthly average, daily
  maximum), each with a reported value or a NODI code. [G]
- Typical row content: parameter, outfall, statistical base, reported value
  + units, permit limit, number of exceedances, sample frequency, sample
  type (grab/composite). [G]
- The signatory certifies the report. In Attesta, a human approves before
  anything leaves the system.

## Evaluating a limit

| Limit type | Definition | Pass when |
|---|---|---|
| Average monthly | highest allowable average of "daily discharges" over a calendar month [V] | arithmetic mean of the month's daily values <= limit [V: mean unless permit says otherwise] |
| Average weekly | same, over a calendar week [V] | mean of the week <= limit |
| Maximum daily | highest allowable "daily discharge" [V] | every daily value <= limit |
| Range (pH) | min and max [G] | every value within [min, max] |
| Minimum (e.g. DO) | [G] | value >= limit |
| Report-only | monitor and report [G] | never an exceedance; just must be reported |

- A "daily discharge" is measured over a calendar day or a 24-hour period
  reasonably representing it. [V]
- **All** monitoring done with approved methods must be included in the
  averages and reported, even if more frequent than the permit requires -
  never drop samples to improve an average. [V]
- Compare with exact arithmetic. Exactly equal to the limit is not an
  exceedance. [G]
- Units must match the permit's; a unit mismatch is a data error, not a
  pass or fail (Attesta: `unit-error`).

## Mapping to Attesta's status set

`pass`, `exceedance`, `review-required`, `under-sampled`, `missing-data`,
`unit-error`, `report-only` (`dsl/permit/eval.rkt`).

- `exceedance` = a value or computed statistic is over the limit.
- `review-required` = exceedance that depends on non-detect reporting
  limits; compliance can be neither shown nor refuted. A human decides.
- `under-sampled` = fewer samples than the permit's frequency, reported on a
  separate `sample-frequency` row (computed = samples taken, threshold =
  required). The limit's own statistic is still computed from the samples
  that exist, so a short count can never hide an exceedance. This is a
  monitoring-frequency finding, not an effluent one.
- `missing-data` = no samples/value at all for the limit. In a real DMR this is a
  *reporting* violation unless a valid NODI code explains it, and some
  codes (E, P) themselves count as non-receipt violations. [V]
- Do not map `missing-data` to `pass`. Do not map `unit-error` to either.
- Not modeled yet [?]: mass-loading limits (lbs/day), weekly averages,
  percent-removal limits, WET/toxicity limits, and late-DMR violations.
  Don't claim a report "complies" without saying which are unchecked.

## Non-detects (below detection limit)

- Handling is **set by the permit/permitting authority**: whether to report
  `<DL`, the detection value, or zero, and how to average non-detects. [V]
- Never report a non-detect as NODI C (No Discharge) or `=0` unless the
  permitting authority directs it. NetDMR allows `<` with the detection
  limit value where the permit requires a value. [V]
- NODI B ("Below Detection Limit/No Detection") applies only where the
  authority allows it; some states report the MDL in the comment field and
  use Q (Not Quantifiable) between QL and DL. [V]
- **Do not substitute zero (or half the limit) for a non-detect in an
  average** unless the permit says so. In PA the reporting limit goes into
  the average and the result is qualified `<`; zero is allowed only in the
  narrow Ch. 16 case (`references/pennsylvania.md`). Treating non-detects
  as zero understates averages and can hide an exceedance.
- Therefore the pipeline's `non-detect` step must keep requiring an
  explicit `treat-as` - never add a silent default. If the DL exceeds the
  permit limit, flag it for human review rather than concluding pass.

## NODI codes in one paragraph

A DMR row takes a numeric value **or** a NODI code, never both. [V] Code
sets vary by state, and which codes excuse versus create a violation is
state- and permit-specific [?]. E and P generate non-receipt violations
in EPA's system. [V] The system must not assert that a NODI code excuses a
missing value; surface it and let the human decide. Full table:
`references/nodi-codes.md`.

## Rules for Attesta code and copy

1. The engine decides; AI only explains. Explanations restate engine
   fields (value, limit, statistic, status, trace) and never introduce new
   numbers or a different verdict.
2. Never present "passes" for a report with `missing-data`, `unit-error`,
   or unchecked limit types. Say what was and wasn't evaluated.
3. Never invent permit numbers, limits, or sample values. The shipped
   `pa0000000` permit is fictional.
4. Show the evidence trail for every status: samples used, calculation,
   limit, units.
5. "Exceedance" is a computed limit breach; avoid declaring "violation" or
   enforcement outcomes.
6. When rules change or are uncertain, add a Racket test in `dsl/tests/`
   with a worked example before changing behavior.

## Other open items

- Whether weekly averages and mass loads are in scope for the submission.
- Group I/II lists are category-level and from a secondary reproduction of
  Appendix A; confirm a specific pollutant against the eCFR text
  (`references/violations-snc.md`).
