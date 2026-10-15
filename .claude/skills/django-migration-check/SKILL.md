---
name: django-migration-check
description: Verify Django model changes have migrations and apply cleanly. Use whenever models.py is edited, a field is added/removed/renamed, the user mentions migration, makemigrations, schema change or a database column, or before committing changes under apps/*/models.py.
---

# Check migrations

Models and migrations drift silently, and a missing migration only fails in
a fresh database, so check before committing.

1. `uv run python manage.py makemigrations --check --dry-run` - non-zero
   means a migration is missing.
2. If missing: `uv run python manage.py makemigrations <app>` and read the
   generated file; confirm it only does what you intended.
3. Apply to a scratch database (not the working `db.sqlite3`), then run
   `uv run pytest`.
4. Never edit an applied migration; add a new one.
5. Engine-owned fields (`LimitResult.status`, `computed_value`, ...) are
   copied verbatim from the engine; don't add computed or AI-written values
   to them.
