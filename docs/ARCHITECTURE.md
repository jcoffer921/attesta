# Architecture reference

This is the detailed reference for how the Django side of Attesta talks to
the Racket rule engine, what gets persisted, and how the evidence pages are
wired up. For the engine's own contract and DSL design, see
[`dsl/README.md`](../dsl/README.md); this document starts where that one
ends.

## Models (`apps/validation/models.py`)

```
ValidationRun
├── permit_slug, pipeline_slug          which definition files were used
├── permit_file_sha256, pipeline_file_sha256   hash of those files AT RUN TIME
├── period                              "YYYY-MM"; may be None
├── status                              "success" | "failed"
├── schema_version                      what the engine actually returned
├── error_code, error_message           set only when status == "failed"
├── started_at, finished_at
├── results            (LimitResult, one per substantive permit clause)
├── provenance_entries (ProvenanceEntry, one per applied pipeline step per record)
└── rejection_entries  (RejectionEntry, one per record a pipeline step could not apply to)
```

The SHA-256 hashes exist to answer "which exact rule definition produced
this result" later, even after `permit_slug`'s underlying file has since
changed. `LimitResult`, `ProvenanceEntry`, and `RejectionEntry` fields are
copied **verbatim** from the engine's JSON — the Django side never
recomputes or restyles a `status`, `computed_value`, or `reason`.

`LimitResult.gemini_explanation` is the one field not owned by the engine:
it's written only by `apps.ai_assist.services.explain_result`, after the
run has already committed, and only that one field.

All four models live in `apps/validation` (not split across apps) because
one CLI invocation does both pipeline normalization and permit evaluation
in one shot — `ValidationRun` is the natural parent of both provenance and
results. Split them only if pipelines are ever run independently of permit
evaluation; nothing in the current design does that.

## Service layer (`apps/validation/services.py`)

```python
run_validation(*, permit_slug, pipeline_slug, records, period=None) -> ValidationRun
describe_permit(*, permit_slug) -> dict
```

Both resolve `*_slug` to a file under `DSL_ROOT` with two independent
checks — this is deliberate defense in depth, not redundancy:

1. **Python-side**: slug must match `^[a-z0-9][a-z0-9_-]*$`; the resolved,
   `.resolve()`d path must be `is_relative_to()` the permits/pipelines
   directory (so a symlink can't escape it); the file must exist. A
   violation raises `InvalidSlugError` (a subclass of `EngineError`)
   **before any subprocess is started.**
2. **Racket-side**: `dsl/main.rkt` re-validates the same restriction
   independently (see `dsl/README.md`).

`subprocess.run` is always called with an argument list (never
`shell=True`), `capture_output=True`, and `timeout=RACKET_TIMEOUT_SECONDS`.
Every failure mode is classified into an `EngineError(code, message)`:

| `code` | Cause |
|---|---|
| `invalid-slug` | Slug fails the pattern, resolves outside the allowed directory |
| `file-error` | Slug is well-formed but no matching `.rkt` file exists |
| `timeout` | `subprocess.TimeoutExpired` |
| `invalid-json` | Engine exited 0 but stdout wasn't valid JSON |
| `unexpected-schema-version` | Engine's `schema_version` wasn't 1 |
| `engine-crash` | Nonzero exit and stdout wasn't the documented `{"error": {...}}` shape |
| *(anything else)* | Passed through verbatim from the engine's own `{"error": {"code", "message"}}` |

`run_validation` persists the outcome **atomically**: on success, one
`ValidationRun(status="success")` plus all of its `LimitResult` /
`ProvenanceEntry` / `RejectionEntry` rows commit together
(`transaction.atomic()`); on any failure, one
`ValidationRun(status="failed")` with the classified `error_code` /
`error_message` and **zero** child rows. A bad slug (caught before any
subprocess call) doesn't even get a row — nothing was attempted. This is
what "a failed or garbled engine run leaves the database in a consistent
state" means concretely; see `tests/test_validation_service.py`.

## Explanation layer (`apps/ai_assist/services.py`)

```python
explain_result(limit_result_id: int) -> str
```

Reads one `LimitResult`'s trace fields (read-only), builds a prompt,
calls Gemini, and writes the response to `gemini_explanation` via a
**targeted `.update()`** — not a full model `.save()` — so a concurrent
change to other fields can't be clobbered. Any failure (API error, network,
quota) raises `ExplanationError` **without writing anything**, so a failed
explanation attempt can never blank out or alter a previously stored
result. Gemini is called after `run_validation` has already committed;
there is no path by which an explanation failure affects a stored status.

## Evidence views (`apps/validation/views.py`, `apps/validation/urls.py`)

| URL | View | Purpose |
|---|---|---|
| `/validation/permits/<slug>/` | `permit_rules` | Renders a permit's limits from `describe_permit`'s JSON only |
| `/validation/runs/<id>/` | `validation_results` | One row per `LimitResult`, status badge, expandable trace shown by default |
| `/validation/runs/<id>/provenance/` | `provenance_timeline` | Ordered steps + rejections per record |

`permit_rules` treats two failure kinds differently, on purpose:

- **`InvalidSlugError` → `Http404`.** A bad or unknown slug is a client
  error; `describe_permit` already validated it in Python before any
  subprocess call, so this never touches Racket.
- **`EngineError` → renders an error template with HTTP 502.** A broken
  permit file, timeout, or malformed engine output is a server-side
  failure. The page shows `error.code` and a fixed generic message —
  **never** the raw engine message, which can contain filesystem paths.

`validation_results` and `provenance_timeline` look up an already-persisted
`ValidationRun` by primary key (no live engine call), so an unknown `id` is
a plain `Http404`, and a run whose `status == "failed"` renders normally
(HTTP 200) with an error banner built from the stored `error_code` /
`error_message` — that's historical data already in the database, not a
failure of the page itself.

Status badges (`STATUS_BADGE_CLASSES` in `views.py`) are a fixed dict keyed
by the engine's literal status string — `pass`, `exceedance`,
`missing-data`, `unit-error`, `report-only` — and nothing else computes or
restyles them; in particular, AI-generated text is never used to pick a
badge.

The optional Chart.js monthly-average line (built in
`_monthly_avg_chart_series`) converts stored fraction/decimal strings
(e.g. `"55/2"`) to floats via `fractions.Fraction` **for display only**; it
never touches the stored `computed_value` or any status.

### Cross-links and current entry point

The three pages link to each other (results ↔ provenance ↔ permit rules)
via the run's stored `permit_slug` and primary key. There is no dedicated
"run list" page yet, so `ValidationRun` is registered in Django admin
(`apps/validation/admin.py`, read-only: add/change permissions disabled)
with an `evidence_links` column linking straight to Results / Provenance /
Permit rules for each run — that's the working front door until a small
dedicated run-list page (with a single sidebar link) replaces it.

## What's deliberately out of scope so far

- No UI for authoring or editing permit/pipeline DSL definitions, and no
  "submit to agency" feature — these pages are read-only evidence viewers.
- No persisted model for raw (pre-pipeline) lab records; `records` is
  passed into `run_validation` by whatever ingestion code calls it.
- No human-approval workflow (`approved_by`/`approved_at`) yet. This was
  deliberately deferred rather than reserving a placeholder column: approval
  needs to record *who* approved, decide what a re-run does to an approved
  run (a re-run should create a new run and never inherit approval), and
  ideally block approving a run with unacknowledged exceedances — none of
  which is a placeholder-shaped, one-line addition.
- No dedicated run-list page (see above) — `ValidationRun` in Django admin
  is the interim entry point.
