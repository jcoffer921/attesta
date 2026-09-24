"""Gunicorn config for Attesta.

apps.validation.services.run_validation shells out to the Racket rule
engine and blocks the calling worker/thread for up to
RACKET_TIMEOUT_SECONDS (default 30s, see config/settings.py). Two things
follow directly from that:

1. Use more than one worker, or threads per worker (this file uses
   `gthread` with several threads per worker) -- otherwise a single
   in-flight validation blocks every other request the process would
   otherwise be serving.
2. Gunicorn's own `timeout` must be comfortably larger than
   RACKET_TIMEOUT_SECONDS. If it isn't, Gunicorn will SIGKILL the worker
   for being "silent" before apps.validation.services ever gets a chance
   to catch subprocess.TimeoutExpired and return its own structured
   {"error": {...}} response -- the client would see a raw connection
   reset instead of the documented error contract.

Run with: gunicorn config.wsgi:application -c gunicorn.conf.py
"""

import multiprocessing
import os

# Mirrors config/settings.py's RACKET_TIMEOUT_SECONDS default. Keep these in
# sync if you change one (or set both from the same env var in your
# deployment config).
_racket_timeout = int(os.environ.get("RACKET_TIMEOUT_SECONDS", 30))

bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")

worker_class = "gthread"
workers = int(os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
threads = int(os.environ.get("GUNICORN_THREADS", 4))

# Must exceed RACKET_TIMEOUT_SECONDS plus normal request/DB overhead, so a
# validation that legitimately runs the full engine timeout can still
# return its own error response instead of being killed mid-request.
timeout = int(os.environ.get("GUNICORN_TIMEOUT", _racket_timeout + 15))
graceful_timeout = timeout
