"""AI interprets; the rule engine decides.

Claude reads an already-persisted LimitResult trace and writes a
plain-language explanation into its own field. It never sees or touches
`status`, and it is only ever called after apps.validation.services.run_validation
has already committed the run.
"""

from __future__ import annotations

from apps.ingestion import claude_review
from apps.validation.models import LimitResult


class ExplanationError(Exception):
    """Raised when Claude could not produce an explanation. Never partially writes."""


def _call_claude(prompt: str) -> str:
    """Ask Claude for a short explanation. Shares the evidence-review HTTP
    client (key, model fallback, retries)."""
    response = claude_review._post_to_claude({
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}],
    })
    blocks = response.get("content") or []
    text = "".join(b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text")
    if not text.strip():
        raise ExplanationError("Claude returned an empty explanation.")
    return text.strip()


def _build_prompt(result: LimitResult) -> str:
    return (
        "Explain the following compliance evaluation result in one or two "
        "plain-language sentences for a non-technical reader. Do not judge "
        "or restate compliance status beyond what is given; only explain it.\n"
        f"Outfall: {result.outfall}\n"
        f"Parameter: {result.parameter}\n"
        f"Clause: {result.clause}\n"
        f"Computed value: {result.computed_value}\n"
        f"Threshold: {result.threshold}\n"
        f"Comparison: {result.comparison}\n"
        f"Status: {result.status}\n"
        f"Engine reason: {result.reason}\n"
    )


def explain_result(limit_result_id: int) -> str:
    """Fetch one LimitResult, ask Claude for a plain-language explanation,
    and persist it via a targeted update of gemini_explanation only.

    Raises ExplanationError on any failure without writing anything, so a
    failed explanation attempt can never blank out or otherwise change a
    previously stored result.
    """
    result = LimitResult.objects.get(pk=limit_result_id)
    prompt = _build_prompt(result)

    try:
        explanation = _call_claude(prompt)
    except Exception as exc:
        raise ExplanationError(f"Claude explanation failed: {exc}") from exc

    LimitResult.objects.filter(pk=limit_result_id).update(gemini_explanation=explanation)
    return explanation
