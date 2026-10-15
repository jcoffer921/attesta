---
name: evaluate-dmr-data
description: Step-by-step workflow for running a set of monitoring/lab records through Attesta's engine against a permit and writing the compliance analysis. Use whenever the user asks to run, check, evaluate, analyze, audit or sanity-test DMR data, a CSV of lab results, a validation run, a month's samples, or an engine scenario - even if they just paste results and ask "are we compliant?". Load npdes-dmr-compliance alongside this for status and non-detect meanings.
---

# Evaluate DMR data

A fixed workflow so every analysis is reproducible, evidence-backed and
honest about what was not checked. Load `npdes-dmr-compliance` first for
status meanings and PA non-detect rules. **The engine decides; you report
what it returned. Never recompute a verdict by hand and present it as the
result.**

## 0. Frame the run

State, before running anything:
- permit slug, pipeline slug, reporting period (`YYYY-MM`), source of records
- what question is being answered (e.g. "does Oct 2026 comply?")

If any is missing, ask; do not guess a permit or period. The shipped
`pa0000000` permit is fictional - say so in the report.

## 1. Validate inputs (before the engine)

For each record check: `id` unique; `outfall`, `Analyte`, `value`, `unit`,
`sample_date` (ISO), `method` present; value is a plain decimal or
`<`-prefixed non-detect. Raw records use the lab column name `Analyte`
(the pipeline maps it to `parameter`); a record that already has
`parameter` instead of `Analyte` is rejected. The engine has no NODI
input - if the source data carries NODI codes, list them separately for
the human rather than feeding them in. List problems; do not silently fix
or drop records. Records outside the
period are noted as out-of-scope, not deleted.

## 2. Run the engine

Prefer the real path so the audit trail is persisted:

```
racket dsl/main.rkt run --permit dsl/permit/permits/<slug>.rkt \
  --pipeline dsl/pipeline/pipelines/<slug>.rkt --period YYYY-MM < input.json
```

(input: `{"schema_version": 3, "records": [...]}`). Racket is often not on
PATH on Windows; check `C:\Program Files\Racket\racket.exe` or set
`RACKET_EXECUTABLE`. From Django use
`apps.validation.services.run_validation`. Never edit engine output.
On an `{"error": ...}` envelope stop and report the code and message.

## 3. Triage the output

Account for **every** input record: it appears in provenance and either
reaches a result (`sample_ids`) or a rejection. Reconcile counts:
`records in = used in results + rejected + out-of-period`. Any mismatch is
a finding - a silently dropped record can hide the one sample that made a
month non-compliant, which is why this check comes before reading any
status.

Group results by status:

| Status | Meaning | Action |
|---|---|---|
| pass | within limit (maybe `<` qualified upper bound) | report |
| exceedance | limit breached by detected data | report, cite values |
| review-required | breach depends on non-detect reporting limits | escalate to human; do not call pass or fail |
| under-sampled | fewer samples than required (separate `sample-frequency` row); the statistic is still computed | report as a monitoring-frequency finding; PA code E, comment, form |
| missing-data | no samples for the limit | list what is missing; NODI needed |
| unit-error | unit mismatch, no conversion | fix input or add convert step |
| report-only | monitor-and-report | note value only |

## 4. Check the analysis, not just the status

For each non-pass result, verify from the trace:
1. threshold and comparison match the permit clause (`describe` output)
2. `sample_ids` are the right outfall/parameter/period samples
3. computed value reproduces from `sample_values` (exact rational; a
   `<` prefix means non-detects at reporting limits)
4. non-detects: treat-as is `report-limit` (or `zero` with a basis); any
   result where the reporting limit exceeds the permit limit is flagged
5. units agree; provenance shows any conversion

If a check fails, that is an engine/pipeline bug - go to step 6, do not
paper over it.

## 5. Report

Output, in this order:
1. **Verdict line**: counts per status, e.g. "12 limits: 9 pass, 2
   exceedance, 1 review-required". Never "compliant" unless every
   substantive limit passed AND the not-evaluated list below is empty or
   explicitly accepted.
2. **Findings table**: outfall, parameter, clause, computed, limit, status,
   sample ids, reason (verbatim from the engine).
3. **Not evaluated**: weekly averages, mass loads, percent removal, WET,
   sample-frequency beyond count, late submission, NODI validity.
4. **Data quality**: rejections and input problems from steps 1 and 3.
5. **Required human decisions**: review-required items, missing-data
   needing NODI (PA: `E` is a violation, `GG`, `FF`), 24-hour / 5-day
   notification candidates for daily-max exceedances of listed pollutants.
6. **Reproduce**: exact command, permit/pipeline file SHA-256, period.

Keep SNC discussion indicative only (see compliance skill).

## 6. When the engine looks wrong

1. Minimize to the smallest record set that reproduces it.
2. Add a failing case to `dsl/tests/permit-eval-test.rkt` or
   `pipeline-run-test.rkt` (worked example, expected status and value).
3. Fix, then use the `run-tests` skill and report real output.
4. Contract changes (new status/field) bump `schema_version` and update
   `apps/validation/services.py`, views badge map and docs together.

## Scenario checklist (use as a test-runner)

Run each as its own small dataset and confirm the expected status. Rows
marked (approx) rest on a documented simplification (per-week frequency is
`count x ceil(days/7)`, not ISO weeks); rows marked (untested) have no
Racket test yet - add one if you rely on them.

| Scenario | Expect |
|---|---|
| value exactly at limit | pass |
| value just over limit (detected) | exceedance |
| non-detect, RL below limit | pass, result `<` qualified |
| non-detect, RL above limit, nothing else | review-required |
| non-detect + detected value over limit | exceedance |
| zero samples in period | missing-data |
| fewer samples than required frequency (approx) | statistic evaluated + under-sampled row |
| short count AND a breaching sample | exceedance + under-sampled row (never masked) |
| wrong unit, no conversion | unit-error |
| `ug/L` sample, limit in `mg/L`, convert step present (untested end to end) | converted, evaluated |
| report-only limit with data | report-only |
| pH below min / above max | exceedance |
| record missing required field | rejection, not silently dropped |
| `0.1 + 0.2` average | exact rational, no float drift |
