"""AI interprets; the rule engine decides.

Claude reads an already-persisted LimitResult trace and writes a
plain-language explanation into its own field. It never sees or touches
`status`, and it is only ever called after apps.validation.services.run_validation
has already committed the run.

The model is given a closed context (the result, its provenance and
rejection rows, and the citation keys that apply) and must name which items
it relied on. `verify_explanation` rejects anything that cites outside that
context or states a number that is not in it.
"""

from __future__ import annotations

import json
import re

from apps.ai_assist import citations
from apps.ingestion import claude_review
from apps.validation.models import LimitResult, ProvenanceEntry, RejectionEntry


class ExplanationError(Exception):
    """Raised when Claude could not produce a verified explanation. Never partially writes."""


_NUMBER = re.compile(r"\d+(?:\.\d+)?")


def _call_claude(prompt: str) -> str:
    """Ask Claude for a short explanation. Shares the evidence-review HTTP
    client (key, model fallback, retries)."""
    response = claude_review._post_to_claude({
        "max_tokens": 500,
        "messages": [{"role": "user", "content": prompt}],
    })
    blocks = response.get("content") or []
    text = "".join(b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text")
    if not text.strip():
        raise ExplanationError("Claude returned an empty explanation.")
    return text.strip()


def build_context(result: LimitResult) -> dict:
    """The only material the model may draw on, with a stable id per item."""
    sample_ids = [str(s) for s in (result.sample_ids or [])]
    provenance = ProvenanceEntry.objects.filter(
        run_id=result.run_id, record_id__in=sample_ids
    ).order_by("pk")
    rejections = RejectionEntry.objects.filter(
        run_id=result.run_id, record_id__in=sample_ids
    ).order_by("pk")

    return {
        "result": {
            "outfall": result.outfall,
            "parameter": result.parameter,
            "clause": result.clause,
            "sample_values": result.sample_values,
            "computed_value": result.computed_value,
            "threshold": result.threshold,
            "comparison": result.comparison,
            "status": result.status,
            "reason": result.reason,
        },
        "provenance": [
            {"id": f"prov:{p.pk}", "step": p.step, "record_id": p.record_id,
             "before": p.before, "after": p.after, "note": p.note}
            for p in provenance
        ],
        "rejections": [
            {"id": f"rej:{r.pk}", "step": r.step, "record_id": r.record_id, "reason": r.reason}
            for r in rejections
        ],
        "citations": [
            {"id": f"cite:{key}", "cite": citations.CITATIONS[key]["cite"],
             "summary": citations.CITATIONS[key]["summary"]}
            for key in citations.applicable_keys(result.clause)
        ],
    }


def allowed_refs(context: dict) -> set[str]:
    return {item["id"] for section in ("provenance", "rejections", "citations") for item in context[section]}


def _build_prompt(context: dict) -> str:
    return (
        "Explain the compliance evaluation result below in one or two "
        "plain-language sentences for a non-technical reader.\n"
        "Rules:\n"
        "- Use ONLY facts in the JSON context. If something is not there, do not say it.\n"
        "- Do not judge or restate compliance status beyond what is given; only explain it.\n"
        "- Do not introduce any number that is not in the context.\n"
        "- Cite every provenance, rejection and citation item you rely on by its id.\n"
        'Respond with JSON only: {"explanation": "<text>", "refs": ["<id>", ...]}\n\n'
        f"Context:\n{json.dumps(context, sort_keys=True, default=str)}\n"
    )


def verify_explanation(raw: str, context: dict) -> tuple[str, list[str]]:
    """Parse the model output and check it against `context`.

    Returns (explanation, refs). Raises ExplanationError if the output is not
    the requested JSON, cites an id that is not in the context, cites
    nothing, or states a number the context does not contain.
    """
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        payload = json.loads(text)
    except ValueError as exc:
        raise ExplanationError("Explanation was not valid JSON.") from exc
    if not isinstance(payload, dict):
        raise ExplanationError("Explanation JSON was not an object.")

    explanation = payload.get("explanation")
    refs = payload.get("refs")
    if not isinstance(explanation, str) or not explanation.strip():
        raise ExplanationError("Explanation text was missing.")
    if not isinstance(refs, list) or not all(isinstance(r, str) for r in refs):
        raise ExplanationError("Explanation refs were missing or malformed.")
    if not refs:
        raise ExplanationError("Explanation cited no sources.")

    unknown = sorted(set(refs) - allowed_refs(context))
    if unknown:
        raise ExplanationError(f"Explanation cited sources not in the context: {', '.join(unknown)}")

    context_numbers = set(_NUMBER.findall(json.dumps(context, default=str)))
    unsupported = sorted(set(_NUMBER.findall(explanation)) - context_numbers)
    if unsupported:
        raise ExplanationError(f"Explanation stated numbers not in the context: {', '.join(unsupported)}")

    return explanation.strip(), list(dict.fromkeys(refs))


def explain_result(limit_result_id: int) -> str:
    """Fetch one LimitResult, ask Claude for a grounded explanation, verify
    it, and persist it via a targeted update of the explanation fields only.

    Raises ExplanationError on any failure -- API error or failed
    verification -- without writing anything, so a failed attempt can never
    blank out or otherwise change a previously stored result.
    """
    result = LimitResult.objects.get(pk=limit_result_id)
    context = build_context(result)

    try:
        raw = _call_claude(_build_prompt(context))
    except ExplanationError:
        raise
    except Exception as exc:
        raise ExplanationError(f"Claude explanation failed: {exc}") from exc

    explanation, refs = verify_explanation(raw, context)

    LimitResult.objects.filter(pk=limit_result_id).update(
        gemini_explanation=explanation,
        explanation_refs={"refs": refs, "citations_version": citations.CITATIONS_VERSION},
    )
    return explanation
