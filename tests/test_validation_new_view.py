import json
import subprocess
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.facilities.models import Organization
from apps.validation.models import LabRecord, ValidationRun

CSV = (
    "id,outfall,Analyte,value,unit,sample_date,method\n"
    "r1,1,TSS,27.5,mg/L,2026-03-05,SM2540D\n"
    "r2,1,TSS,<0.5,mg/L,2026-03-12,SM2540D\n"
    "r3,1,TSS,30,mg/L,2026-03-19,SM2540D\n"
).encode()


def upload(content=CSV, name="lab.csv"):
    return SimpleUploadedFile(name, content, content_type="text/csv")


def form(**overrides):
    data = {"csv_file": upload(), "permit_slug": "pa0000000", "period": "2026-03"}
    data.update(overrides)
    return data


def completed(returncode, stdout=""):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout.encode(), stderr=b"")


SUCCESS = json.dumps({"schema_version": 3, "results": [], "provenance": [], "rejections": []})


def test_requires_login(client):
    response = client.get(reverse("validation_new"))
    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))


def test_get_form_lists_permit_slugs(org_client):
    response = org_client.get(reverse("validation_new"))
    assert response.status_code == 200
    assert "pa0000000" in response.content.decode()


def test_valid_upload_creates_run_and_redirects_to_results(org_client, org_user):
    with patch("apps.validation.services.subprocess.run", return_value=completed(0, SUCCESS)) as sub:
        response = org_client.post(reverse("validation_new"), form())

    run = ValidationRun.objects.get()
    assert response.status_code == 302
    assert response.url == reverse("validation_results", args=[run.pk])
    assert run.organization == org_user.organization
    assert run.pipeline_slug == "lab-csv-import"
    assert run.period == "2026-03"
    assert run.lab_records.count() == 3
    assert run.lab_records.get(record_id="r2").data["value"] == "<0.5"
    assert "shell" not in sub.call_args.kwargs


@pytest.mark.parametrize("bad_csv, fragment", [
    (CSV.replace(b"r2,1,TSS", b"r2,x,TSS"), "row 2"),
    (b"id,outfall\nr1,1\n", "Analyte"),
    (b"\xb5", "UTF-8"),
])
def test_parse_error_rerenders_400_with_row_message_and_persists_nothing(org_client, bad_csv, fragment):
    with patch("apps.validation.views.run_validation") as rv:
        response = org_client.post(reverse("validation_new"), form(csv_file=upload(bad_csv)))

    assert response.status_code == 400
    assert fragment in response.content.decode()
    rv.assert_not_called()
    assert ValidationRun.objects.count() == 0


def test_missing_or_empty_file_rerenders_400(org_client):
    data = form()
    del data["csv_file"]
    assert org_client.post(reverse("validation_new"), data).status_code == 400
    assert org_client.post(reverse("validation_new"), form(csv_file=upload(b""))).status_code == 400
    assert ValidationRun.objects.count() == 0


@pytest.mark.parametrize("override", [
    {"period": "2026-13"}, {"period": "March"}, {"period": ""}, {"permit_slug": "nope"}, {"permit_slug": "../x"},
])
def test_invalid_period_or_permit_rerenders_400(org_client, override):
    with patch("apps.validation.views.run_validation") as rv:
        response = org_client.post(reverse("validation_new"), form(**override))

    assert response.status_code == 400
    rv.assert_not_called()


def test_engine_failure_redirects_to_failed_run_page_with_records_kept(org_client):
    with patch("apps.validation.services.subprocess.run", return_value=completed(1, "crash")):
        response = org_client.post(reverse("validation_new"), form())

    run = ValidationRun.objects.get()
    assert response.status_code == 302
    assert response.url == reverse("validation_results", args=[run.pk])
    assert run.status == "failed"
    assert LabRecord.objects.filter(run=run).count() == 3
    assert "Run failed" in org_client.get(response.url).content.decode()


def test_admin_post_forbidden_403_and_no_run(admin_client):
    with patch("apps.validation.views.run_validation") as rv:
        response = admin_client.post(reverse("validation_new"), form())

    assert response.status_code == 403
    rv.assert_not_called()
    assert ValidationRun.objects.count() == 0
    assert "organization users only" in admin_client.get(reverse("validation_new")).content.decode()


def test_run_list_scoped_to_org_and_admin_sees_all(org_client, org_user, admin_user, client):
    other = Organization.objects.create(name="Other", slug="other")
    mine = ValidationRun.objects.create(organization=org_user.organization, permit_slug="mine-permit",
                                        pipeline_slug="p", status="success", period="2026-01")
    theirs = ValidationRun.objects.create(organization=other, permit_slug="other-permit",
                                          pipeline_slug="p", status="success")
    legacy = ValidationRun.objects.create(organization=None, permit_slug="legacy-permit",
                                          pipeline_slug="p", status="success")

    body = org_client.get(reverse("validation_run_list")).content.decode()
    assert "mine-permit" in body and "other-permit" not in body and "legacy-permit" not in body
    assert reverse("validation_results", args=[mine.pk]) in body

    client.force_login(admin_user)
    body = client.get(reverse("validation_run_list")).content.decode()
    assert all(s in body for s in ("mine-permit", "other-permit", "legacy-permit"))
    assert theirs.pk and legacy.pk
