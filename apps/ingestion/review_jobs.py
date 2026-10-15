"""Run Claude reviews off the request thread.

Status lives in the database, so any web worker can serve the polling
endpoint. If the process dies mid-review, the status view expires the item
after settings.REVIEW_STALE_SECONDS so it can be restarted.
"""

import logging
import threading

from django.db import close_old_connections

from . import claude_review

logger = logging.getLogger(__name__)


def _run(evidence_id, run):
    try:
        claude_review.run_review(evidence_id, run)
    except Exception:
        logger.exception("Evidence review %s (run %s) crashed", evidence_id, run)
    finally:
        close_old_connections()


def enqueue(evidence_id, run):
    threading.Thread(
        target=_run, args=(evidence_id, run), name=f"review-{evidence_id}-{run}", daemon=True,
    ).start()
