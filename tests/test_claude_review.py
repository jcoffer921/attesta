import json
import zipfile
from datetime import timedelta
from io import BytesIO

import pytest
from django.core.files.base import ContentFile
from django.urls import reverse
from django.utils import timezone

from apps.ingestion import claude_review
from apps.ingestion.models import Evidence

GEMINI_JSON = {
    "overall_match": 82,
    "summary": "Monthly DMR cover letter with effluent data.",
    "key_criteria": ["Reporting period stated"],
    "partial_matches": ["Flow data missing units"],
    "potential_gaps": ["No signature of responsible official"],
    "key_statements": [{"text": "BOD 12 mg/L", "confidence": "high"}],
    "recommendation": "needs_follow_up",
}


@pytest.fixture(autouse=True)
def review_settings(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.ANTHROPIC_API_KEY = "test-key"


def make_evidence(org_user, name="report.pdf", data=b"%PDF-1.4 test", **kwargs):
    item = Evidence(
        organization=org_user.organization,
        uploaded_by=org_user,
        original_name=name,
        content_type=kwargs.pop("content_type", "application/pdf"),
        size=len(data),
        **kwargs,
    )
    item.file.save(name, ContentFile(data), save=True)
    return item


def claude_response(payload):
    return {"content": [{"type": "tool_use", "name": "submit_review", "input": payload}], "stop_reason": "tool_use"}


def test_run_review_stores_result_and_marks_reviewed(org_user, monkeypatch):
    item = make_evidence(org_user, review_status=Evidence.ReviewStatus.IN_REVIEW, review_run=1)
    monkeypatch.setattr(claude_review, "_post_to_claude", lambda body: claude_response(GEMINI_JSON))

    claude_review.run_review(item.pk, 1)

    item.refresh_from_db()
    assert item.review_status == Evidence.ReviewStatus.REVIEWED
    assert item.review_result["overall_match"] == 82
    assert item.review_completed_at is not None
    assert item.review_error == ""


def test_run_review_failure_marks_error_and_allows_restart(org_client, org_user, monkeypatch):
    item = make_evidence(org_user, review_status=Evidence.ReviewStatus.IN_REVIEW, review_run=1)

    def boom(body):
        raise claude_review.ReviewError("Claude returned HTTP 503.")

    monkeypatch.setattr(claude_review, "_post_to_claude", boom)
    claude_review.run_review(item.pk, 1)

    item.refresh_from_db()
    assert item.review_status == Evidence.ReviewStatus.ERROR
    assert "503" in item.review_error

    payload = org_client.get(reverse("ai_review_status", args=[item.pk])).json()
    assert payload["status"] == "error"
    assert "503" in payload["detail"]

    restart = org_client.post(
        reverse("ai_review"),
        {"evidence_id": item.pk, "action": "start"},
        headers={"x-requested-with": "XMLHttpRequest"},
    )
    item.refresh_from_db()
    assert restart.json()["status"] == "in_review"
    assert item.review_run == 2
    assert item.review_error == ""


def test_stopped_review_result_is_discarded(org_client, org_user, monkeypatch):
    item = make_evidence(org_user, review_status=Evidence.ReviewStatus.IN_REVIEW, review_run=1)

    def slow_claude(body):
        # The user presses Stop while Claude is still working.
        org_client.post(reverse("ai_review"), {"evidence_id": item.pk, "action": "stop"})
        return claude_response(GEMINI_JSON)

    monkeypatch.setattr(claude_review, "_post_to_claude", slow_claude)
    claude_review.run_review(item.pk, 1)

    item.refresh_from_db()
    assert item.review_status == Evidence.ReviewStatus.STOPPED
    assert item.review_result is None


def test_start_enqueues_job_with_new_run_number(org_client, org_user, monkeypatch):
    from apps.ingestion import review_jobs

    calls = []
    monkeypatch.setattr(review_jobs, "enqueue", lambda pk, run: calls.append((pk, run)))
    item = make_evidence(org_user)

    org_client.post(reverse("ai_review"), {"evidence_id": item.pk, "action": "start"})
    org_client.post(reverse("ai_review"), {"evidence_id": item.pk, "action": "stop"})
    org_client.post(reverse("ai_review"), {"evidence_id": item.pk, "action": "start"})

    item.refresh_from_db()
    assert [c[0] for c in calls] == [item.pk, item.pk]
    assert calls[0][1] < calls[1][1]
    assert calls[1][1] == item.review_run
    assert item.review_status == Evidence.ReviewStatus.IN_REVIEW


def test_stale_in_review_item_becomes_error_so_it_can_restart(org_client, org_user, settings):
    settings.REVIEW_STALE_SECONDS = 60
    item = make_evidence(
        org_user,
        review_status=Evidence.ReviewStatus.IN_REVIEW,
        review_started_at=timezone.now() - timedelta(seconds=600),
        review_run=1,
    )

    payload = org_client.get(reverse("ai_review_status", args=[item.pk])).json()

    assert payload["status"] == "error"
    item.refresh_from_db()
    assert item.review_status == Evidence.ReviewStatus.ERROR


def test_missing_api_key_is_a_clear_error(org_user, settings):
    settings.ANTHROPIC_API_KEY = ""
    item = make_evidence(org_user, review_status=Evidence.ReviewStatus.IN_REVIEW, review_run=1)

    claude_review.run_review(item.pk, 1)

    item.refresh_from_db()
    assert item.review_status == Evidence.ReviewStatus.ERROR
    assert "ANTHROPIC_API_KEY" in item.review_error


def test_pdf_is_sent_inline_and_docx_is_sent_as_text(org_user):
    pdf = make_evidence(org_user, "a.pdf", b"%PDF-1.4 x")
    parts = claude_review.build_content_parts(pdf)
    assert parts[0]["type"] == "document"
    assert parts[0]["source"]["media_type"] == "application/pdf"
    assert parts[-1]["type"] == "text"

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(
            "word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body><w:p><w:r><w:t>Effluent limit exceeded</w:t></w:r></w:p></w:body></w:document>",
        )
    docx = make_evidence(org_user, "a.docx", buf.getvalue(), content_type="application/octet-stream")
    parts = claude_review.build_content_parts(docx)
    assert "Effluent limit exceeded" in parts[0]["text"]


def test_results_render_on_review_page(org_client, org_user):
    item = make_evidence(
        org_user,
        review_status=Evidence.ReviewStatus.REVIEWED,
        review_result=GEMINI_JSON,
        review_run=1,
    )

    html = org_client.get(reverse("ai_review"), {"evidence": item.pk}).content.decode()

    assert "82%" in html
    assert "No signature of responsible official" in html
    assert "BOD 12 mg/L" in html


def test_overloaded_model_falls_back_to_next_model(monkeypatch, settings):
    import io
    import urllib.error

    settings.CLAUDE_MODEL = "primary"
    settings.CLAUDE_FALLBACK_MODELS = ["backup"]
    monkeypatch.setattr(claude_review.time, "sleep", lambda s: None)
    models = []

    class Ok:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b'{"ok": true}'

    def fake_urlopen(request, timeout):
        model = json.loads(request.data)["model"]
        models.append(model)
        if model == "primary":
            raise urllib.error.HTTPError("u", 503, "unavailable", {}, io.BytesIO(b""))
        return Ok()

    monkeypatch.setattr(claude_review.urllib.request, "urlopen", fake_urlopen)

    result = claude_review._post_to_claude({})

    assert result["ok"] is True and result["_model"] == "backup"
    assert models == ["primary", "primary", "backup"]


def test_all_models_unavailable_gives_clear_error(monkeypatch, settings):
    import io
    import urllib.error

    settings.CLAUDE_MODEL = "primary"
    settings.CLAUDE_FALLBACK_MODELS = ["backup"]
    monkeypatch.setattr(claude_review.time, "sleep", lambda s: None)

    def always_503(request, timeout):
        raise urllib.error.HTTPError("u", 503, "unavailable", {}, io.BytesIO(b""))

    monkeypatch.setattr(claude_review.urllib.request, "urlopen", always_503)

    with pytest.raises(claude_review.ReviewError, match="unavailable right now"):
        claude_review._post_to_claude({})


def test_status_payload_reports_current_step(org_client, org_user):
    item = make_evidence(
        org_user, review_status=Evidence.ReviewStatus.IN_REVIEW, review_run=1,
        review_stage="analyzing", review_started_at=timezone.now(),
    )

    payload = org_client.get(reverse("ai_review_status", args=[item.pk])).json()

    assert payload["steps"] == ["Reading document", "Analyzing with Claude", "Preparing results"]
    assert payload["step"] == 1


def test_run_review_advances_stage(org_user, monkeypatch):
    item = make_evidence(org_user, review_status=Evidence.ReviewStatus.IN_REVIEW, review_run=1)
    seen = []

    def fake_post(body):
        seen.append(Evidence.objects.get(pk=item.pk).review_stage)
        return claude_response(GEMINI_JSON)

    monkeypatch.setattr(claude_review, "_post_to_claude", fake_post)
    claude_review.run_review(item.pk, 1)

    assert seen == ["analyzing"]
    item.refresh_from_db()
    assert item.review_stage == ""


def overlay_tag(html):
    start = html.index("<div class=\"review-overlay\"")
    return html[start:html.index(">", start)]


def test_overlay_visible_only_while_in_review(org_client, org_user):
    item = make_evidence(org_user, review_status=Evidence.ReviewStatus.IN_REVIEW, review_run=1,
                         review_started_at=timezone.now())
    html = org_client.get(reverse("ai_review"), {"evidence": item.pk}).content.decode()
    assert "hidden" not in overlay_tag(html)

    Evidence.objects.filter(pk=item.pk).update(review_status=Evidence.ReviewStatus.UPLOADED)
    html = org_client.get(reverse("ai_review"), {"evidence": item.pk}).content.decode()
    assert "hidden" in overlay_tag(html)
    assert "Live review status" not in html


def test_error_shows_message_banner(org_client, org_user):
    item = make_evidence(org_user, review_status=Evidence.ReviewStatus.ERROR,
                         review_error="Claude returned HTTP 503.", review_run=1)
    html = org_client.get(reverse("ai_review"), {"evidence": item.pk}).content.decode()
    assert "Claude returned HTTP 503." in html
