# Attesta — agent guide

Attesta prepares NPDES/DMR compliance reports for human approval. A
deterministic Racket rule engine decides compliance; Django persists and
displays results; Claude only explains results already computed.

## Non-negotiable rules

- **The rule engine decides, AI only explains.** Never let LLM output set or
  alter `status`, `computed_value`, `reason`, or any engine-owned field. The
  explanation code writes only its own explanation field.
- **Never recompute engine output in Python.** `LimitResult`,
  `ProvenanceEntry`, `RejectionEntry` are copied verbatim from engine JSON.
- **Subprocess safety.** Call Racket with an argument list, a timeout, no
  `shell=True`. Slugs are validated Python-side *and* Racket-side; keep both.
- **Racket is pure.** No network, clock, randomness, or file writes; exact
  rationals only.
- **No fabricated data.** Don't add demo/seed numbers to product pages.
- Don't commit `.env`, `db.sqlite3`, or `media/`.

## Layout

| Path | Purpose |
|---|---|
| `dsl/` | Racket Permit Rules DSL + Evidence Pipeline DSL, CLI at `dsl/main.rkt` (JSON stdin/stdout) |
| `apps/validation/` | Service layer (`services.py`), models, evidence views |
| `apps/ai_assist/` | Claude explanations of stored results |
| `apps/ingestion/` | Evidence upload, Claude review (`claude_review.py`, `review_jobs.py`) |
| `apps/facilities/`, `apps/accounts/`, `apps/reports/` | Facilities, auth/signup, reports |
| `config/` | Django settings/urls (env via `.env`) |
| `templates/`, `static/` | UI |
| `tests/` | pytest-django; Racket tests in `dsl/tests/` |
| `docs/ARCHITECTURE.md`, `dsl/README.md` | Authoritative references |

## Commands

```
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
uv run pytest                 # Django tests
raco test dsl/                # Racket tests (Windows: Racket is not on PATH; use C:\Program Files\Racket\raco.exe)
uv run python manage.py makemigrations --check --dry-run
```

## Conventions

- Python 3.12, Django 6.0, managed with `uv`. Settings via django-environ.
- Match surrounding style; keep comments for non-obvious *why*.
- Changing the engine JSON contract means updating `schema_version`, the
  Racket CLI, `apps/validation/services.py`, and both test suites together.
- Add or update tests with every behavior change; run both suites before
  claiming done.
