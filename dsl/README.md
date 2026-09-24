# DSLs

Two small embedded Racket DSLs that make up Attesta's deterministic rule
core. They are kept separate from the Django application code; the
`apps/validation` app calls into them via the CLI in `main.rkt` but does not
implement rule logic itself.

All code here is pure: no network, no file writes beyond stdout, no
randomness, no clock reads. All arithmetic on monitoring values and permit
thresholds uses exact rationals, never floating point.

## Layout

- `common.rkt` -- shared structs (`sample-rec`, `trace`, `provenance-entry`,
  `rejection-entry`) and pure helpers (`parse-exact-decimal`, `month-of`,
  `weeks-in-month`).
- `permit/lang.rkt` -- the Permit Rules DSL: `permit` / `outfall` / `limit`
  macros plus clause forms (`monthly-avg`, `daily-max`, `range`, `sample`,
  `report-only`). Non-integer thresholds must use Racket's `#e` exact-decimal
  prefix (e.g. `#e0.5`); a bare decimal literal is rejected at
  macro-expansion time so floating point can never enter a compliance
  threshold.
- `permit/eval.rkt` -- evaluates monitoring samples against a permit for a
  given reporting period ("YYYY-MM"), producing one evidence `trace` per
  substantive limit clause. Status set: `pass`, `exceedance`,
  `missing-data`, `unit-error`, `report-only`.
- `permit/permits/pa0000000.rkt` -- **fictional placeholder permit** used
  only to exercise the DSL syntax; not derived from a real PA NPDES permit.
- `pipeline/lang.rkt` -- the Evidence Pipeline DSL: `pipeline` plus step
  forms (`map-column`, `convert-units`, `non-detect`, `require-field`).
  `non-detect` has no default `treat-as`; an invalid or missing one is a
  macro-expansion-time error.
- `pipeline/run.rkt` -- interprets a pipeline over raw records, logging one
  provenance entry per applied step per record and one rejection entry
  (never a silent drop) when a step can't apply.
- `pipeline/pipelines/lab-csv-import.rkt` -- example pipeline matching the
  target syntax.
- `json.rkt` -- the only place jsexpr <-> struct conversion happens.
- `main.rkt` -- CLI entry point (see below).
- `tests/` -- rackunit test suite; run with `raco test dsl/`.

## CLI

```
racket dsl/main.rkt run --permit <file> --pipeline <file> [--period YYYY-MM]
racket dsl/main.rkt describe --permit <file>
```

`run` reads `{"schema_version": 1, "records": [...]}` on stdin and writes
`{"schema_version": 1, "provenance": [...], "results": [...], "rejections": [...]}`
to stdout. `--period` is optional; if omitted it's inferred from the first
record's `sample_date`. `describe` writes a permit's limits as JSON so other
layers never have to parse s-expressions.

On any error: nonzero exit and `{"error": {"code", "message"}}` on stdout,
never a stack trace.

`--permit` and `--pipeline` must point to files under `permit/permits/` and
`pipeline/pipelines/` respectively (enforced by path normalization in
`main.rkt`) -- the CLI never accepts inline DSL source as an argument or on
stdin, only vetted file paths from those two directories.

## Known simplifications (flagged, not silent)

- `sample ... per-week` frequency is checked against `count *
  ceil(days-in-month / 7)` for the target month, not real ISO week
  boundaries.
- Path restriction to `permit/permits/` and `pipeline/pipelines/` is
  directory-based, not a fully sandboxed language; a permit/pipeline file
  can still `require` arbitrary Racket modules. This is acceptable for
  repo-authored, code-reviewed definitions but is not a defense against a
  genuinely untrusted file landing in those directories.

## Running the tests

```
raco test dsl/
```
