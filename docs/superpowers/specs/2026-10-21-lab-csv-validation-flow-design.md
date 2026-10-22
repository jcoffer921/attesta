# Lab CSV → validation run flow — design

Sub-project B of the MVP gap list. Depends on sub-project A (done:
`ValidationRun.organization`, `_visible_runs`, `LimitResult.explanation`).

## Goal

An org user uploads a lab CSV, picks a permit and period, and lands on the
results page of a persisted `ValidationRun`. The Racket engine remains the
only judge; Python only moves bytes into the shape the engine expects and
stores the raw input.

## Non-goals

- Report generation, approval (sub-projects C, D).
- Permit authoring or real PA permit (E).
- Auto-running Claude explanations at upload.
- Any change to the engine JSON contract (no `schema_version` bump).

## Components

### `LabRecord` model (`apps/validation/models.py`)

| Field | Notes |
|---|---|
| `organization` | FK `facilities.Organization`, CASCADE |
| `run` | FK `ValidationRun`, related_name `lab_records`, CASCADE |
| `row_number` | int, 1-based data row in the source CSV |
| `record_id` | CharField(64), the CSV `id` column |
| `data` | JSONField, exactly the dict sent to the engine |

Unique together `(run, record_id)`. Created in the same transaction as the
run (see Flow), for successful **and** failed runs, so the raw input is
always retained. Migration `0004`.

No source-file FK in this iteration: the upload is not stored as `Evidence`
(YAGNI; the `data` rows are the durable input).

### Parser (`apps/validation/csv_import.py`)

`parse_lab_csv(file_bytes) -> list[dict]`; raises `LabCsvError(message)`.

- Decode UTF-8 (accept BOM via `utf-8-sig`); otherwise error.
- Max 1 MB and 5,000 data rows.
- Required headers: `id, outfall, Analyte, value, unit, sample_date,
  method`. Extra columns ignored. Missing headers listed in the error.
- Each record: all required columns as stripped strings, except `outfall`
  → `int`. Blank `id`, `outfall`, `Analyte`, `value` rejected with the
  row number; `unit`, `sample_date`, `method` may be blank (the pipeline's
  `require-field` rejects them and that rejection is persisted by the
  engine, not pre-empted here).
- Duplicate `id` rejected with both row numbers.
- No unit, date, or non-detect interpretation. `"<0.5"` passes through
  verbatim.

### Service change (`apps/validation/services.py`)

`run_validation` gains one optional keyword, `row_numbers: list[int] | None
= None` (same length as `records`). When given, the service creates one
`LabRecord(row_number, record_id=record["id"], data=record)` per record for
the run — inside the success transaction, and for failed runs in the same
transaction as the failed `ValidationRun` (`_fail`). `records` stays the
single source for both the engine payload and the stored rows, so stored
and sent data cannot diverge. Persisting in the service, not a post-hoc
insert in the view, keeps run + records atomic. A length mismatch raises
`ValueError` before any subprocess call.

### Views and URLs (`apps/validation/views.py`, `urls.py`)

Mounted under the existing `validation/` prefix (keeps the module cohesive;
`/app/...` routes in `config/urls.py` stay for the legacy pages):

- `GET validation/runs/` — `validation_run_list`: org-scoped via
  `_visible_runs`, newest first, columns: id, permit, period, status,
  started, link to results.
- `GET/POST validation/runs/new/` — `validation_new`:
  - Org-role users only. Admins (no organization) get a page-level message
    and HTTP 403 on POST.
  - Form: CSV file, permit (choices from `describe`-able files in
    `dsl/permit/permits`, listed by slug, no subprocess), period
    (`YYYY-MM`, required).
  - POST: parse → on `LabCsvError` re-render with the message (HTTP 400);
    else `run_validation(organization=..., permit_slug=...,
    pipeline_slug="lab-csv-import", records=..., period=...)`;
    redirect to `validation_results`. On `EngineError` the failed run
    already exists; redirect to its results page (shows the error banner).
    On `InvalidSlugError` re-render form with a generic message.
- `POST validation/results/<id>/explain/` — `explain_limit_result`:
  look up the `LimitResult` through `_visible_runs` (404 cross-org),
  call `explain_result`, redirect back to the run's results page with a
  flash message; `ExplanationError` shows a generic message (no raw Claude
  or path text). Writes only via `explain_result`'s existing targeted
  update.

Pipeline slug is fixed to `lab-csv-import` (only one exists; no UI for it).

### Templates

- `pages/validation_run_list.html`, `pages/validation_new.html`.
- `validation_results.html`: "Explain" button per row without an
  explanation.
- Nav link "Validation" in the app sidebar; README drops the "use Django
  admin" note.

## Data flow

```
CSV bytes -> parse_lab_csv -> records[] (+ row numbers)
          -> run_validation(organization, ..., records)
               -> racket run (stdin JSON, argument list, timeout)
               -> atomic: ValidationRun + LimitResult/Provenance/Rejection
                          + LabRecord (same transaction)
          -> redirect validation_results
```

## Error handling

| Failure | Result |
|---|---|
| Bad CSV | Form re-rendered, 400, row-level message, nothing persisted |
| Engine failure/timeout | Failed `ValidationRun` + `LabRecord`s persisted; redirect to results with banner |
| Bad permit slug | Form error, nothing persisted |
| Explanation failure | Flash message, stored data unchanged |
| Admin user | Message / 403, no run |

## Testing

- `tests/test_csv_import.py`: each rejection, BOM, extra columns, `<0.5`
  passthrough, row/size limits.
- `tests/test_validation_new_view.py` (engine mocked): success → redirect
  and `LabRecord` rows with correct `data`; parse error; engine failure
  persists failed run + records; admin blocked; unauthenticated redirect.
- Run list: org scoping, admin sees all.
- Explain endpoint: 404 cross-org, success writes only explanation fields
  (snapshot of engine fields unchanged), `ExplanationError` path, POST-only.
- Model: `LabRecord` unique `(run, record_id)`.
- Full gate: `pytest`, `raco test dsl/`, `makemigrations --check`.

## Open assumptions (confirmed in review)

- Column set above matches the user's lab export.
- Explanations are on-demand, not automatic.
