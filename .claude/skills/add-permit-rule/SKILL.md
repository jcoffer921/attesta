---
name: add-permit-rule
description: Add or change a permit limit, outfall, sample frequency, or pipeline step in Attesta's Racket DSLs (dsl/permit/permits, dsl/pipeline/pipelines). Use whenever the user wants a new permit, a new or changed limit (monthly average, daily max, pH range, report-only), a unit conversion, non-detect handling, or any edit to a .rkt rule or pipeline file.
---

# Add or change a permit rule

The Racket engine is the single source of compliance decisions, so every
change here must be small, pure and tested.

1. Read `dsl/README.md` and a sibling file in `dsl/permit/permits/` or
   `dsl/pipeline/pipelines/` for the exact syntax.
2. **Real values only.** Limits come from an actual permit. The shipped
   `pa0000000` permit is fictional; never invent limits, permit numbers or
   units to fill a gap - ask for the permit text.
3. Slug (file name) must match `^[a-z0-9][a-z0-9_-]*$`.
4. Non-integer thresholds need the `#e` prefix (`#e0.5`); bare decimals are
   rejected at expansion time so floating point never enters a threshold.
5. Keep it pure: no I/O, clock, randomness. Exact rationals only.
6. Non-detect steps need an explicit `treat-as`:
   `(non-detect (marker "<") (treat-as report-limit))` is the PA convention;
   `zero` additionally requires `(basis "...")`; `half-mdl` no longer exists.
7. Add a worked example to the matching `dsl/tests/*-test.rkt` first, then
   run `raco test dsl/` and `uv run pytest`.
8. If the engine's output shape or status set changes, bump
   `schema_version` (currently 3) in `dsl/main.rkt` and
   `apps/validation/services.py`, and update the views badge map, docs and
   tests together.
9. Compliance decisions belong in the DSL, never in Python.
