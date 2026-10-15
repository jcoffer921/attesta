"""Review an uploaded Evidence file with Claude and persist the result.

Calls the Anthropic Messages API directly (stdlib only). PDFs and images are
sent as document/image blocks; DOCX/XLSX are not accepted by the API, so
their text is extracted locally first. The structured result is obtained by
forcing a single tool call whose input schema is the review format.
"""

import base64
import json
import re
import time
import urllib.error
import urllib.request
import zipfile
from xml.etree import ElementTree

from django.conf import settings
from django.utils import timezone

from .models import Evidence

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
MAX_OUTPUT_TOKENS = 4096
TOOL_NAME = "submit_review"
MAX_INLINE_BYTES = 15 * 1024 * 1024
MAX_TEXT_CHARS = 200_000
TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 529}
ATTEMPTS_PER_MODEL = 2
RETRY_DELAY_SECONDS = 2

INLINE_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}

PROMPT = """You are assisting a human reviewer on a wastewater (NPDES / DMR) compliance platform.
Review the attached evidence document. Describe only what the document actually contains;
do not invent values, signatures or dates. Submit your review with the submit_review tool.

- overall_match: integer 0-100, how well the document works as compliance evidence.
- summary: 1-3 sentences on what the document is.
- key_criteria: compliance-relevant items the document clearly satisfies.
- partial_matches: items only partly addressed.
- potential_gaps: required information that is missing or unclear.
- key_statements: notable verbatim statements, each with confidence high/medium/low.
- recommendation: one of "accept", "needs_follow_up", "reject".
"""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_match": {"type": "integer", "minimum": 0, "maximum": 100},
        "summary": {"type": "string"},
        "key_criteria": {"type": "array", "items": {"type": "string"}},
        "partial_matches": {"type": "array", "items": {"type": "string"}},
        "potential_gaps": {"type": "array", "items": {"type": "string"}},
        "key_statements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"text": {"type": "string"}, "confidence": {"type": "string"}},
                "required": ["text", "confidence"],
            },
        },
        "recommendation": {"type": "string", "enum": ["accept", "needs_follow_up", "reject"]},
    },
    "required": ["overall_match", "summary", "key_criteria", "partial_matches",
                 "potential_gaps", "key_statements", "recommendation"],
}


REVIEW_STEPS = [
    ("reading", "Reading document"),
    ("analyzing", "Analyzing with Claude"),
    ("saving", "Preparing results"),
]


def _set_stage(evidence_id, run, stage):
    Evidence.objects.filter(
        pk=evidence_id, review_run=run, review_status=Evidence.ReviewStatus.IN_REVIEW,
    ).update(review_stage=stage)


class ReviewError(Exception):
    """A review failed in a way the user can be told about."""


def _xml_text(xml_bytes, tag):
    root = ElementTree.fromstring(xml_bytes)
    return root, [el for el in root.iter() if el.tag.endswith(tag)]


def _docx_text(file):
    with zipfile.ZipFile(file) as archive:
        root = ElementTree.fromstring(archive.read("word/document.xml"))
    paragraphs = []
    for paragraph in root.iter():
        if paragraph.tag.endswith("}p"):
            text = "".join(t.text or "" for t in paragraph.iter() if t.tag.endswith("}t"))
            if text.strip():
                paragraphs.append(text)
    return "\n".join(paragraphs)


def _xlsx_text(file):
    with zipfile.ZipFile(file) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            _, items = _xml_text(archive.read("xl/sharedStrings.xml"), "}si")
            shared = ["".join(t.text or "" for t in si.iter() if t.tag.endswith("}t")) for si in items]
        sheets = sorted(n for n in archive.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", n))
        lines = []
        for number, name in enumerate(sheets, start=1):
            lines.append(f"## Sheet {number}")
            _, rows = _xml_text(archive.read(name), "}row")
            for row in rows:
                cells = []
                for cell in row:
                    value = next((c.text for c in cell if c.tag.endswith("}v")), None)
                    inline = "".join(t.text or "" for t in cell.iter() if t.tag.endswith("}t"))
                    if cell.get("t") == "s" and value is not None and value.isdigit():
                        index = int(value)
                        value = shared[index] if index < len(shared) else ""
                    cells.append(value if value is not None else inline)
                if any(cells):
                    lines.append("\t".join(c or "" for c in cells))
        return "\n".join(lines)


def build_content_parts(evidence):
    """Return the Claude content blocks (the document first, then the prompt)."""
    extension = "." + evidence.extension.lower()
    parts = []
    try:
        with evidence.file.open("rb") as handle:
            if extension in INLINE_MIME_TYPES:
                data = handle.read(MAX_INLINE_BYTES + 1)
                if len(data) > MAX_INLINE_BYTES:
                    raise ReviewError("This file is too large to send for AI review (15 MB limit).")
                block_type = "document" if extension == ".pdf" else "image"
                parts.append({"type": block_type, "source": {
                    "type": "base64",
                    "media_type": INLINE_MIME_TYPES[extension],
                    "data": base64.b64encode(data).decode("ascii"),
                }})
            elif extension in (".docx", ".xlsx"):
                extract = _docx_text if extension == ".docx" else _xlsx_text
                try:
                    text = extract(handle)
                except (zipfile.BadZipFile, KeyError, ElementTree.ParseError):
                    raise ReviewError("The document could not be read. Is the file corrupted?")
                if not text.strip():
                    raise ReviewError("No readable text was found in this document.")
                parts.append({"type": "text", "text": f"Document text ({evidence.original_name}):\n\n{text[:MAX_TEXT_CHARS]}"})
            else:
                raise ReviewError(f"{evidence.extension} files cannot be reviewed.")
    except FileNotFoundError:
        raise ReviewError("The uploaded file is no longer available on the server.")
    parts.append({"type": "text", "text": PROMPT})
    return parts


def _call_model(model, body, api_key):
    request = urllib.request.Request(
        API_URL,
        data=json.dumps({**body, "model": model}).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": API_VERSION,
        },
        method="POST",
    )
    for attempt in range(ATTEMPTS_PER_MODEL):
        try:
            with urllib.request.urlopen(request, timeout=settings.CLAUDE_TIMEOUT_SECONDS) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in TRANSIENT_STATUS_CODES and attempt < ATTEMPTS_PER_MODEL - 1:
                time.sleep(RETRY_DELAY_SECONDS)
                continue
            raise


def _post_to_claude(body):
    """POST to Claude, falling back to the next configured model on HTTP errors."""
    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        raise ReviewError("ANTHROPIC_API_KEY is not configured on the server.")
    models = [settings.CLAUDE_MODEL, *settings.CLAUDE_FALLBACK_MODELS]
    last_code = None
    for model in models:
        try:
            response = _call_model(model, body, api_key)
        except urllib.error.HTTPError as exc:
            last_code = exc.code
            if exc.code in (401, 403):
                raise ReviewError("The Anthropic API key was rejected. Check ANTHROPIC_API_KEY.") from exc
            continue
        except (urllib.error.URLError, TimeoutError) as exc:
            raise ReviewError("Could not reach Claude. Check the connection and try again.") from exc
        if isinstance(response, dict):
            response["_model"] = model
        return response
    raise ReviewError(f"Claude is unavailable right now (HTTP {last_code}). Please try again shortly.")


def _parse_result(response):
    result = None
    if isinstance(response, dict):
        for block in response.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == TOOL_NAME:
                result = block.get("input")
                break
    if not isinstance(result, dict) or "summary" not in result:
        if isinstance(response, dict) and response.get("stop_reason") == "refusal":
            raise ReviewError("Claude declined to review this document.")
        raise ReviewError("Claude returned an unreadable response.")
    try:
        result["overall_match"] = max(0, min(100, int(result.get("overall_match", 0))))
    except (TypeError, ValueError):
        result["overall_match"] = 0
    for key in ("key_criteria", "partial_matches", "potential_gaps", "key_statements"):
        if not isinstance(result.get(key), list):
            result[key] = []
    return result


def run_review(evidence_id, run):
    """Review one Evidence item. Safe to call from a background thread.

    The result is only written if the item is still in review under the same
    `run` number, so a Stop or Restart while Claude is working wins.
    """
    try:
        evidence = Evidence.objects.get(pk=evidence_id)
        _set_stage(evidence_id, run, "reading")
        parts = build_content_parts(evidence)
        _set_stage(evidence_id, run, "analyzing")
        response = _post_to_claude({
            "max_tokens": MAX_OUTPUT_TOKENS,
            "messages": [{"role": "user", "content": parts}],
            "tools": [{
                "name": TOOL_NAME,
                "description": "Submit the structured compliance review of the document.",
                "input_schema": RESPONSE_SCHEMA,
            }],
            # Newer models reject a forced tool_choice; the prompt asks for the tool.
            "tool_choice": {"type": "auto"},
        })
        _set_stage(evidence_id, run, "saving")
        outcome = {
            "review_status": Evidence.ReviewStatus.REVIEWED,
            "review_result": {**_parse_result(response), "model": response.get("_model", "")},
            "review_error": "",
        }
    except Evidence.DoesNotExist:
        return
    except ReviewError as exc:
        outcome = {"review_status": Evidence.ReviewStatus.ERROR, "review_error": str(exc)}
    except Exception:  # never leave the item stuck in review
        outcome = {
            "review_status": Evidence.ReviewStatus.ERROR,
            "review_error": "Unexpected error during review. Please try again.",
        }
    Evidence.objects.filter(
        pk=evidence_id, review_run=run, review_status=Evidence.ReviewStatus.IN_REVIEW,
    ).update(review_completed_at=timezone.now(), review_stage="", **outcome)
