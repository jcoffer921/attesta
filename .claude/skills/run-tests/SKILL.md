---
name: run-tests
description: Run Attesta's Django (pytest) and Racket (raco) test suites and report real results. Use whenever the user says test, tests, pytest, raco, "is it passing", "verify", "does it still work", or before claiming a change is done, committing, or opening a PR - and whenever a test fails and you need to triage it.
---

# Run the tests

Passing output is the only evidence a change works, so run the suites and
quote what they print instead of summarizing from memory.

1. `uv run pytest` - Django service layer, models, views, accounts, uploads.
2. `raco test dsl/` - run when `dsl/` changed or the engine JSON contract is
   touched. Racket may not be on PATH; on Windows try
   `C:\Program Files\Racket\raco.exe`. If it truly isn't installed, say so
   rather than skipping silently.
3. After editing any `models.py`: `uv run python manage.py makemigrations --check --dry-run`.
4. Single test: `uv run pytest tests/test_x.py::test_name -x`.

## Triage notes

- `uv run` can fail offline because `google-generativeai` isn't cached; if
  `.venv` exists, `.venv/Scripts/python.exe -m pytest` works.
- `PermissionError ... pytest-of-<user>` during setup of upload/review tests
  is a Windows temp-directory problem in the environment, not a code
  regression. Report it as an environment error and run the rest.
- Quote failing test names and assertion output. Don't describe a failing
  run as success, and don't skip a failing test to get green.
