# Attesta

Compliance you can prove. Attesta prepares NPDES/DMR compliance reports for
human approval: a deterministic rule engine decides whether monitoring data
complies with a permit, and every decision carries a full evidence trail —
which samples were used, what was computed, and why.

**Core principle: the rule engine decides, AI only explains.** Gemini is
used solely to produce plain-language explanations of results that have
already been computed and stored; it never determines or alters a status. A
human approves before any report leaves the system.

## Architecture

Attesta has two halves that talk over a JSON contract on stdin/stdout — no
Python/Racket FFI, no shared memory, easy to test independently:

```
┌─────────────────────────┐   subprocess    ┌───────────────────────────┐
│  Django app (Python)     │ ──────────────> │  Racket rule engine       │
│  apps/validation,        │   JSON stdin    │  dsl/                     │
│  apps/ai_assist          │ <────────────── │  (pure, deterministic)    │
└─────────────────────────┘   JSON stdout    └───────────────────────────┘
```

1. **Rule core** (`dsl/`, Racket) — two small embedded DSLs: a **Permit
   Rules DSL** (declares permit/outfall/limit clauses and evaluates
   monitoring samples against them) and an **Evidence Pipeline DSL**
   (declares ordered normalization steps over raw lab records, logging
   every change). Exposed as a CLI (`dsl/main.rkt`) that reads/writes JSON
   only. Pure: no network, no file writes beyond stdout, no randomness, no
   clock reads, exact-rational arithmetic throughout. See
   [`dsl/README.md`](dsl/README.md).

2. **Service layer** (`apps/validation/services.py`) — invokes the Racket
   CLI via `subprocess.run` (argument list, timeout, no `shell=True`),
   validates its JSON contract (schema version, error envelope), and
   persists the outcome atomically. A failed or garbled engine run leaves
   the database in a consistent state: one `ValidationRun(status="failed")`
   row with the classified error, and no partial child rows.

3. **Explanation layer** (`apps/ai_assist/services.py`) — reads an
   already-persisted `LimitResult` and asks Gemini for a one- or
   two-sentence plain-language explanation, written to its own
   `gemini_explanation` field via a targeted update. It never touches
   `status` or any other engine-owned field.

4. **Evidence views** (`apps/validation/views.py`) — three read-only pages
   that make every determination inspectable: permit rules (rendered from
   the engine's `describe` output, never parsed from Racket source),
   validation results (one row per limit, status badge, expandable trace
   shown by default), and pipeline provenance (ordered steps and
   rejections per record). See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
   for the full model/view/error-code reference.

## Setup

Requires Python 3.12+, [uv](https://docs.astral.sh/uv/), and
[Racket](https://racket-lang.org/) (CS variant, v8.x+) on `PATH` (or set
`RACKET_EXECUTABLE` to its full path — see below).

```
uv sync
cp .env.example .env   # if present; otherwise set SECRET_KEY at minimum
uv run python manage.py migrate
uv run python manage.py createsuperuser   # to reach the evidence pages via /admin/
uv run python manage.py runserver
```

Relevant settings (`config/settings.py`, overridable via `.env`):

| Setting | Default | Purpose |
|---|---|---|
| `RACKET_EXECUTABLE` | `racket` | Executable used to invoke the rule engine |
| `RACKET_TIMEOUT_SECONDS` | `30` | Hard timeout on every engine subprocess call |
| `DSL_ROOT` | `BASE_DIR / "dsl"` | Root the service layer resolves permit/pipeline slugs under |
| `GEMINI_API_KEY` | `""` | Required for `apps.ai_assist.services.explain_result` |

## Running the tests

```
uv run pytest          # Django: service layer, models, views (tests/)
raco test dsl/         # Racket: both DSLs, evaluator, pipeline, CLI (dsl/tests/)
```

## Finding your way to the evidence pages

There is no dedicated "run list" page yet (see `docs/ARCHITECTURE.md` for
what's next). Until then, Django admin (`/admin/`) lists every
`ValidationRun` with direct links to its results and provenance pages.
