# Lab CSV → Validation Run Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An org user uploads a lab CSV, picks a permit and period, and lands on a persisted, org-scoped `ValidationRun` whose raw input is stored as `LabRecord` rows.

**Architecture:** A strict, non-interpreting CSV parser builds the record dicts the Racket pipeline expects. `run_validation` persists `LabRecord`s in the same transaction as the run (success or failure). New views list runs, create runs, and trigger on-demand explanations through the existing `explain_result`.

**Tech Stack:** Python 3.12, Django 6.0, pytest-django, Racket engine (mocked in view tests via `patch("apps.validation.services.subprocess.run")` or by patching `run_validation`).

**Spec:** `docs/superpowers/specs/2026-10-21-lab-csv-validation-flow-design.md`

## Global Constraints

- Rule engine decides, AI only explains: never set `status`, `computed_value`, `reason` from Python or LLM output.
- Never recompute engine output in Python; the parser does no unit, date, or non-detect interpretation (`"<0.5"` passes through verbatim).
- Subprocess call stays an argument list with timeout, no `shell=True`; pipeline slug is fixed to `lab-csv-import`.
- Required CSV headers: `id, outfall, Analyte, value, unit, sample_date, method`; limits 1 MB and 5,000 data rows; UTF-8 (BOM accepted).
- Period format `YYYY-MM`.
- No engine JSON change, no `schema_version` bump.
- Do not touch `.env`; do not commit unrelated files (`tests/fixtures/`, `tests/test_sample_evidence.py`, other dirty files).
- Run tests with `PYTHONPATH=.venv/Lib/site-packages python -m pytest` on this machine (uv's Python is blocked by Application Control); Racket: `"C:\Program Files\Racket\raco.exe" test dsl/`.
- Views are `@login_required(login_url='login')`; scoping uses `_visible_runs(user)` from `apps/validation/views.py`.

## Review Focus

- CSV with a UTF-8 BOM (Excel export) must parse, not report a missing `id` header.
- CSV with Windows `\r\n` line endings and trailing blank lines must parse; blank trailing rows are ignored, not "blank id" errors.
- Header names with surrounding whitespace or different case (`" id "`, `analyte`) should produce a clear missing-header error naming the expected spelling, not a crash.
- Non-UTF-8 bytes (Latin-1 `µg/L` from Excel) must give a readable "not UTF-8" message, not a 500.
- Engine failure must still leave `LabRecord`s attached to the failed run (raw input is never lost).
- Uploading with no file selected or an empty file must re-render the form with an error, not a 500.

## File Structure

| File | Responsibility |
|---|---|
| `apps/validation/csv_import.py` (new) | `parse_lab_csv`, `LabCsvError` |
| `apps/validation/models.py` | `LabRecord` |
| `apps/validation/migrations/0004_labrecord.py` (new) | schema |
| `apps/validation/services.py` | `row_numbers` param, `LabRecord` persistence, `available_permit_slugs()` |
| `apps/validation/views.py`, `urls.py` | list, new, explain views |
| `templates/pages/validation_run_list.html`, `validation_new.html` (new) | UI |
| `templates/pages/validation_results.html`, `templates/app_base.html` | Explain button, nav link |
| `README.md` | drop "use Django admin" note |
| `tests/test_csv_import.py`, `tests/test_validation_new_view.py` (new); `tests/test_validation_service.py` | tests |

---

### Task 1: CSV parser

**Files:**
- Create: `apps/validation/csv_import.py`
- Test: `tests/test_csv_import.py`

**Interfaces:**
- Produces: `class LabCsvError(Exception)` (message is user-safe); `parse_lab_csv(file_bytes: bytes) -> tuple[list[dict], list[int]]` returning `(records, row_numbers)`, row numbers 1-based data rows. Record keys are exactly the 7 required headers; `outfall` is `int`, all else stripped `str`. Constants `MAX_BYTES = 1_048_576`, `MAX_ROWS = 5000`, `REQUIRED_HEADERS` tuple.

- [ ] **Step 1: Write failing tests** in `tests/test_csv_import.py` (plain functions, no DB). Cases and assertions:
  - `test_parses_valid_rows`: two rows → records equal `{"id":"r1","outfall":1,"Analyte":"TSS","value":"27.5","unit":"mg/L","sample_date":"2026-03-05","method":"SM2540D"}`; `row_numbers == [1, 2]`.
  - `test_non_detect_passes_through_verbatim`: value `<0.5` stays `"<0.5"`.
  - `test_accepts_bom_and_crlf_and_trailing_blank_lines`.
  - `test_ignores_extra_columns`: output keys == the 7 required.
  - `test_missing_headers_named_in_error`: `pytest.raises(LabCsvError, match="Analyte")`; also a `" id "`/lowercase `analyte` header case raises naming the expected spelling.
  - `test_blank_required_value_reports_row_number`: blank `Analyte` on data row 2 → message contains `"row 2"`.
  - `test_blank_unit_date_method_allowed` (engine's `require-field` rejects later).
  - `test_non_integer_outfall_rejected` (row number in message).
  - `test_duplicate_id_names_both_rows` (message contains `"rows 1 and 3"`).
  - `test_non_utf8_rejected` (`b"\xb5g/L"` content → message contains `"UTF-8"`).
  - `test_size_and_row_limits` (`MAX_BYTES + 1` bytes; `MAX_ROWS + 1` rows).
  - `test_empty_file_rejected`.
- [ ] **Step 2:** Run `PYTHONPATH=.venv/Lib/site-packages python -m pytest tests/test_csv_import.py -q`; expect FAIL (ImportError).
- [ ] **Step 3:** Implement per Interfaces in `apps/validation/csv_import.py` using `csv.DictReader` over `bytes.decode("utf-8-sig")`; skip rows where every value is blank; headers compared exactly after no normalization (error lists missing required names).
- [ ] **Step 4:** Re-run; expect all PASS.
- [ ] **Step 5:** Commit `apps/validation/csv_import.py tests/test_csv_import.py` — `feat: strict lab CSV parser`.

---

### Task 2: `LabRecord` model and service persistence

**Files:**
- Modify: `apps/validation/models.py`, `apps/validation/services.py`
- Create: `apps/validation/migrations/0004_labrecord.py` (via `makemigrations validation -n labrecord`)
- Test: `tests/test_validation_service.py`

**Interfaces:**
- Consumes: `run_validation`, `_fail` (current signatures in `apps/validation/services.py`).
- Produces: `LabRecord(organization FK, run FK related_name="lab_records", row_number PositiveIntegerField, record_id CharField(64), data JSONField)` with `UniqueConstraint(run, record_id)`. `run_validation(*, organization, permit_slug, pipeline_slug, records, period=None, row_numbers: list[int] | None = None)`; `ValueError` if `row_numbers` given and `len != len(records)`, raised before any subprocess call. `_fail(..., records=None, row_numbers=None)` creates the failed run and its `LabRecord`s in one `transaction.atomic()` then raises `EngineError` with the persisted failed run attached as `exc.run` (set `run` attribute before raising; `EngineError.run` defaults to `None`). New helper `available_permit_slugs() -> list[str]`: sorted stems of `settings.DSL_ROOT / "permit/permits" / "*.rkt"`, no subprocess.

- [ ] **Step 1: Write failing tests** appended to `tests/test_validation_service.py` (reuse its `org` fixture, `RECORDS`, `completed`, and a success JSON helper already used there):
  - `test_success_persists_lab_records_matching_sent_records`: with `row_numbers=[1]`, `LabRecord` count 1, `data == RECORDS[0]`, `record_id == "r1"`, `row_number == 1`, `organization == org`.
  - `test_failed_run_still_persists_lab_records` (nonzero exit): run `status == "failed"` and `lab_records.count() == len(RECORDS)`.
  - `test_row_numbers_length_mismatch_raises_before_subprocess`: `patch(...subprocess.run)` not called, `pytest.raises(ValueError)`, no run created.
  - `test_omitting_row_numbers_creates_no_lab_records`.
  - `test_available_permit_slugs_lists_pa0000000`.
- [ ] **Step 2:** Run those tests; expect FAIL.
- [ ] **Step 3:** Add the model, generate migration, and implement the service changes; success path creates records in the existing `transaction.atomic()` block, `_fail` wraps run + records creation atomically (import `transaction` already present).
- [ ] **Step 3b:** Add a test `test_engine_error_carries_failed_run` (`exc_info.value.run.status == "failed"`) before Step 3's implementation.
- [ ] **Step 4:** Run `tests/test_validation_service.py` and `python manage.py makemigrations --check --dry-run`; expect PASS / "No changes detected".
- [ ] **Step 5:** Commit models, migration, services, test — `feat: persist raw lab records with each validation run`.

---

### Task 3: Run list and new-run views

**Files:**
- Modify: `apps/validation/views.py`, `apps/validation/urls.py`, `templates/app_base.html` (add "Validation" nav item after Reports, `active == 'validation_runs'`), `README.md` (remove the "use Django admin to reach results" note)
- Create: `templates/pages/validation_run_list.html`, `templates/pages/validation_new.html`
- Test: `tests/test_validation_new_view.py`

**Interfaces:**
- Consumes: `parse_lab_csv`, `LabCsvError` (Task 1); `run_validation(... row_numbers=)`, `available_permit_slugs` (Task 2); `_visible_runs`.
- Produces: URL names `validation_run_list` (`validation/runs/`) and `validation_new` (`validation/runs/new/`). Route order: `runs/new/` and `runs/` before `runs/<int:run_id>/` is fine (int converter). Form fields: `csv_file` (file), `permit_slug` (select), `period` (text, pattern `\d{4}-(0[1-9]|1[0-2])`).

- [ ] **Step 1: Write failing tests** in `tests/test_validation_new_view.py` using `org_client`, `admin_client`, `client`, and `SimpleUploadedFile`; patch `apps.validation.views.run_validation` where the engine result isn't under test, and patch `apps.validation.services.subprocess.run` for the persistence test:
  - `test_requires_login`: anonymous GET `validation_new` → 302 to login.
  - `test_get_form_lists_permit_slugs`: 200, content contains `pa0000000`.
  - `test_valid_upload_creates_run_and_redirects_to_results`: 302 to `validation_results` for the new run; `run.organization == org_user.organization`; `lab_records.count()` equals CSV rows.
  - `test_parse_error_rerenders_400_with_row_message_and_persists_nothing`.
  - `test_missing_or_empty_file_rerenders_400`.
  - `test_invalid_period_rerenders_400`; unknown permit slug rerenders 400.
  - `test_engine_failure_redirects_to_failed_run_page_with_records_kept` (subprocess nonzero): redirect target shows run status failed; `LabRecord`s exist.
  - `test_admin_post_forbidden_403_and_no_run`; admin GET shows an "organization users only" message.
  - `test_run_list_scoped_to_org_and_admin_sees_all`: other org's run absent for org user, present for admin; legacy null-org run admin only.
- [ ] **Step 2:** Run; expect FAIL (NoReverseMatch).
- [ ] **Step 3:** Implement `validation_run_list` and `validation_new` per spec error table; pipeline slug constant `"lab-csv-import"`; catch `LabCsvError` (400), `InvalidSlugError` (400, generic message), `EngineError` (redirect to `validation_results` for `exc.run`). Templates extend `app_base.html` with `{% block app_content %}`, pass `active='validation_runs'`.
- [ ] **Step 4:** Run `tests/test_validation_new_view.py` plus `tests/test_validation_views.py`; expect PASS.
- [ ] **Step 5:** Commit the listed files (not unrelated dirty files) — `feat: lab CSV upload creates a validation run`.

---

### Task 4: On-demand explanation endpoint

**Files:**
- Modify: `apps/validation/views.py`, `apps/validation/urls.py`, `templates/pages/validation_results.html`
- Test: `tests/test_validation_new_view.py` (explain section) or `tests/test_validation_views.py`

**Interfaces:**
- Consumes: `apps.ai_assist.services.explain_result(limit_result_id) -> str`, `ExplanationError`; `_visible_runs`.
- Produces: URL name `explain_limit_result` (`validation/results/<int:result_id>/explain/`, POST only → `require_POST`); redirects to `validation_results` of the result's run with a `django.contrib.messages` message.

- [ ] **Step 1: Write failing tests** (patch `apps.validation.views.explain_result`):
  - `test_explain_post_calls_service_and_redirects`: 302 to the run page; patched function called once with the result id.
  - `test_explain_get_not_allowed` (405).
  - `test_explain_cross_org_result_404` and legacy null-org result 404 for org user; service not called.
  - `test_explanation_error_shows_generic_message`: patched to raise `ExplanationError("secret path C:\\x")`; followed redirect page contains a generic message and not `secret path`.
  - `test_explain_never_changes_engine_fields`: with the real `explain_result` and `_call_claude` patched to a verified-valid response (reuse helpers/GOOD fixture in `tests/test_ai_assist_service.py`), engine fields snapshot equal before/after.
  - `test_results_page_shows_explain_button_only_for_rows_without_explanation`.
- [ ] **Step 2:** Run; expect FAIL.
- [ ] **Step 3:** Implement the view and the per-row POST form (with `{% csrf_token %}`) in `validation_results.html`; render `messages` in the page if `app_base.html` doesn't already.
- [ ] **Step 4:** Run those tests; expect PASS.
- [ ] **Step 5:** Commit — `feat: on-demand Claude explanation from the results page`.

---

### Task 5: Full verification

- [ ] **Step 1:** `PYTHONPATH=.venv/Lib/site-packages python -m pytest -q`; expect all pass, report the real count.
- [ ] **Step 2:** `"C:\Program Files\Racket\raco.exe" test dsl/`; expect all pass.
- [ ] **Step 3:** `PYTHONPATH=.venv/Lib/site-packages python manage.py makemigrations --check --dry-run`; expect "No changes detected".
- [ ] **Step 4:** Manual smoke if the server can run: upload a 3-row CSV from `tests/fixtures` style data against `pa0000000`, 2026-03; confirm redirect to results with rows and an Explain button.
- [ ] **Step 5:** Update `docs/ARCHITECTURE.md` with a short "Lab CSV intake" section (flow + `LabRecord`), then commit — `docs: describe lab CSV intake`.
