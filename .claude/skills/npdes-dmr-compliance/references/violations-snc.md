# Violations, notification, and SNC

Evidence tags: **[V]** verified against a primary or EPA/state source (see `sources.md`); **[G]** general domain knowledge, confirm against the actual permit before using it in user-facing text; **[?]** open question, do not guess.

- Report all noncompliance with the DMR (122.41(l)(7)); anything that may
  endanger health/environment, an unanticipated bypass over a limit, an
  upset over a limit, or a violation of a listed maximum daily limit needs
  oral notice within 24 hours and a written report within 5 days. [V]
- Records (samples, calibration, reports) kept >= 3 years (5 for sludge
  records); the Director can extend this. [V]
- **Significant noncompliance (SNC)** is assigned by EPA (ICIS-NPDES)/the
  state, not by the permittee. Effluent criteria for monthly-average
  limits (40 CFR 123.45 App. A, "Category I") [V]:
  - Chronic: limit exceeded (by any amount) in >= 4 months of a 6-month
    period.
  - Technical Review Criteria: monthly average >= 1.4x limit (Group I:
    oxygen demand, solids, nutrients, oil & grease, minerals, some metals)
    or >= 1.2x (Group II: most metals, cyanide, TRC, organics), in >= 2
    months of a 6-month period.
  - Reporting violations (e.g. DMRs 30+ days late) also count toward SNC;
    nationally they account for over half of facilities in SNC [V]. The
    30-day threshold itself is [G].
## Group I and Group II pollutants (40 CFR 123.45 App. A)

Category-level lists. Source: a secondary reproduction of Appendix A (see
`sources.md`); the eCFR was not reachable, so confirm an individual
pollutant against the official text before relying on it. [V, secondary]

**Group I (TRC 1.4)**
- Oxygen demand: BOD, COD, total oxygen demand, TOC
- Solids: TSS, TDS
- Nutrients: inorganic phosphorus and nitrogen compounds
- Detergents and oils: MBAS, NTA, oil and grease
- Minerals: calcium, chloride, sulfate, hardness (and similar)
- Four metals only: aluminum, cobalt, iron, vanadium

**Group II (TRC 1.2)**
- Every other metal (copper, zinc, lead, nickel, chromium, cadmium,
  mercury, silver, arsenic, ...)
- Cyanide
- Total residual chlorine
- All organics, except those specifically listed under Group I

Working rule: **a metal is Group II unless it is aluminum, cobalt, iron or
vanadium.** The group matters: a 25% exceedance meets Group II's 1.2x TRC
but not Group I's 1.4x.

- Attesta may *preview* these as informational flags ("would meet TRC"),
  but must label them indicative, not an official SNC determination.
