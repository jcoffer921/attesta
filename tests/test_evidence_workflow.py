import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.accounts.models import User
from apps.facilities.models import Organization
from apps.ingestion.models import Evidence


@pytest.fixture(autouse=True)
def temporary_media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"


def docx_upload(name="monthly-report.docx"):
    return SimpleUploadedFile(
        name,
        b"PK\x03\x04 synthetic docx content",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


def test_upload_persists_evidence_and_opens_confirmation(org_client, org_user):
    response = org_client.post(reverse("evidence"), {"files": docx_upload()})

    item = Evidence.objects.get()
    assert response.status_code == 302
    assert response.url == f"{reverse('evidence')}?uploaded={item.pk}"
    assert item.organization == org_user.organization
    assert item.uploaded_by == org_user
    assert item.original_name == "monthly-report.docx"
    assert item.review_status == Evidence.ReviewStatus.UPLOADED

    confirmation = org_client.get(response.url)
    confirmation_html = confirmation.content.decode()
    assert "Confirm this document" in confirmation_html
    assert "monthly-report.docx" in confirmation_html
    assert f"{reverse('ai_review')}?evidence={item.pk}&uploaded=1" in confirmation_html


def test_ajax_upload_returns_live_update_payload(org_client, org_user):
    response = org_client.post(
        reverse("evidence"),
        {"files": docx_upload("live-report.docx")},
        headers={"x-requested-with": "XMLHttpRequest"},
    )

    item = Evidence.objects.get()
    payload = response.json()
    assert response.status_code == 200
    assert payload["evidence_id"] == item.pk
    assert payload["filename"] == "live-report.docx"
    assert payload["review_url"] == f"{reverse('ai_review')}?evidence={item.pk}&uploaded=1"
    assert f'data-evidence-id="{item.pk}"' in payload["rows_html"]
    assert "live-report.docx" in payload["rows_html"]


def test_ajax_upload_validation_error_is_json(org_client):
    response = org_client.post(
        reverse("evidence"),
        {"files": SimpleUploadedFile("payload.exe", b"not allowed")},
        headers={"x-requested-with": "XMLHttpRequest"},
    )

    assert response.status_code == 400
    assert response.json() == {"error": "payload.exe is not a supported file type."}
    assert not Evidence.objects.exists()


def test_selected_upload_can_begin_review(org_client, org_user):
    item = Evidence.objects.create(
        organization=org_user.organization,
        uploaded_by=org_user,
        file=docx_upload(),
        original_name="monthly-report.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        size=24,
    )

    select_response = org_client.get(reverse("ai_review"), {"evidence": item.pk})
    assert select_response.status_code == 200
    assert "monthly-report.docx" in select_response.content.decode()
    assert "Begin Review" in select_response.content.decode()

    start_response = org_client.post(reverse("ai_review"), {"evidence_id": item.pk})
    item.refresh_from_db()
    assert start_response.status_code == 302
    assert start_response.url == f"{reverse('ai_review')}?evidence={item.pk}&started=1"
    assert item.review_status == Evidence.ReviewStatus.IN_REVIEW
    assert item.review_started_by == org_user
    assert item.review_started_at is not None

    active_response = org_client.get(start_response.url)
    active_html = active_response.content.decode()
    assert "Review in progress" in active_html
    assert "Review started successfully" in active_html


def test_ajax_review_start_and_live_status(org_client, org_user):
    item = Evidence.objects.create(
        organization=org_user.organization,
        uploaded_by=org_user,
        file=docx_upload(),
        original_name="monthly-report.docx",
        size=24,
    )

    start_response = org_client.post(
        reverse("ai_review"),
        {"evidence_id": item.pk},
        headers={"x-requested-with": "XMLHttpRequest"},
    )
    start_payload = start_response.json()
    assert start_response.status_code == 200
    assert start_payload["status"] == Evidence.ReviewStatus.IN_REVIEW
    assert start_payload["stage"] == "Review in progress"
    assert start_payload["progress"] == 35
    assert start_payload["status_url"] == reverse("ai_review_status", args=[item.pk])

    status_response = org_client.get(start_payload["status_url"])
    assert status_response.status_code == 200
    assert status_response.json()["status"] == Evidence.ReviewStatus.IN_REVIEW

    stop_response = org_client.post(
        reverse("ai_review"),
        {"evidence_id": item.pk, "action": "stop"},
        headers={"x-requested-with": "XMLHttpRequest"},
    )
    item.refresh_from_db()
    stop_payload = stop_response.json()
    assert stop_response.status_code == 200
    assert stop_payload["status"] == Evidence.ReviewStatus.STOPPED
    assert stop_payload["stage"] == "Review stopped"
    assert item.review_stopped_by == org_user
    assert item.review_stopped_at is not None

    stopped_page = org_client.get(reverse("ai_review"), {"evidence": item.pk})
    stopped_html = stopped_page.content.decode()
    assert "Resume Review" in stopped_html
    assert 'data-review-stop hidden' in stopped_html

    resume_response = org_client.post(
        reverse("ai_review"),
        {"evidence_id": item.pk, "action": "start"},
        headers={"x-requested-with": "XMLHttpRequest"},
    )
    item.refresh_from_db()
    assert resume_response.json()["status"] == Evidence.ReviewStatus.IN_REVIEW
    assert item.review_stopped_by is None
    assert item.review_stopped_at is None


def test_org_cannot_poll_another_orgs_review(org_client):
    other_org = Organization.objects.create(name="Status Water", slug="status-water")
    other_user = User.objects.create_user(
        username="status-user", password="pw", role=User.Role.ORG, organization=other_org,
    )
    item = Evidence.objects.create(
        organization=other_org,
        uploaded_by=other_user,
        file=docx_upload("status-private.docx"),
        original_name="status-private.docx",
        size=24,
    )

    assert org_client.get(reverse("ai_review_status", args=[item.pk])).status_code == 404


def test_unsupported_upload_is_rejected(org_client):
    response = org_client.post(
        reverse("evidence"),
        {"files": SimpleUploadedFile("payload.exe", b"not allowed")},
    )

    assert response.status_code == 200
    assert "not a supported file type" in response.content.decode()
    assert not Evidence.objects.exists()


def test_org_cannot_select_or_download_another_orgs_evidence(org_client, org_user):
    other_org = Organization.objects.create(name="Other Water", slug="other-water")
    other_user = User.objects.create_user(
        username="other-user", password="pw", role=User.Role.ORG, organization=other_org,
    )
    item = Evidence.objects.create(
        organization=other_org,
        uploaded_by=other_user,
        file=docx_upload("private.docx"),
        original_name="private.docx",
        size=24,
    )

    assert org_client.get(reverse("ai_review"), {"evidence": item.pk}).status_code == 404
    assert org_client.get(reverse("evidence_download", args=[item.pk])).status_code == 404


def test_uploaded_evidence_is_listed_and_downloadable(org_client, org_user):
    item = Evidence.objects.create(
        organization=org_user.organization,
        uploaded_by=org_user,
        file=docx_upload(),
        original_name="monthly-report.docx",
        size=24,
    )

    list_response = org_client.get(reverse("evidence"))
    download_response = org_client.get(reverse("evidence_download", args=[item.pk]))

    assert "monthly-report.docx" in list_response.content.decode()
    assert download_response.status_code == 200
    assert download_response["Content-Disposition"].endswith('filename="monthly-report.docx"')
