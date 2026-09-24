"""AI interprets; the rule engine decides.

Gemini reads an already-persisted LimitResult trace and writes a
plain-language explanation into its own field. It never sees or touches
`status`, and it is only ever called after apps.validation.services.run_validation
has already committed the run.
"""

from __future__ import annotations

from django.conf import settings

from apps.validation.models import LimitResult


class ExplanationError(Exception):
    """Raised when Gemini could not produce an explanation. Never partially writes."""


def _call_gemini(prompt: str) -> str:  # pragma: no cover - thin wrapper around the real API call
    import google.generativeai as genai

    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(prompt)
    return response.text


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
    """Fetch one LimitResult, ask Gemini for a plain-language explanation,
    and persist it via a targeted update of gemini_explanation only.

    Raises ExplanationError on any failure without writing anything, so a
    failed explanation attempt can never blank out or otherwise change a
    previously stored result.
    """
    result = LimitResult.objects.get(pk=limit_result_id)
    prompt = _build_prompt(result)

    try:
        explanation = _call_gemini(prompt)
    except Exception as exc:
        raise ExplanationError(f"Gemini explanation failed: {exc}") from exc

    LimitResult.objects.filter(pk=limit_result_id).update(gemini_explanation=explanation)
    return explanation
