import pytest
from django.urls import reverse
from django.contrib.messages import get_messages

from apps.validation.models import LimitResult, ValidationRun
from apps.validation.templatetags.validation_extras import decimal_display


@pytest.mark.parametrize("raw, shown", [
    ("57/2", "28.5 (57/2)"),
    ("1/2", "0.5 (1/2)"),
    ("1/3", "≈ 0.3333 (1/3)"),
    ("30", "30"),
    ("n/a", "n/a"),
    ("", ""),
    (None, ""),
])
def test_decimal_display_shows_decimal_beside_fraction(raw, shown):
    assert decimal_display(raw) == shown


def make_run(org, statuses):
    run = ValidationRun.objects.create(organization=org, permit_slug="pa0000000",
                                       pipeline_slug="lab-csv-import", status="success", schema_version=3)
    for i, status in enumerate(statuses):
        LimitResult.objects.create(
            run=run, outfall=1, parameter=f"P{i}", clause="monthly-avg", sample_ids=["r1"],
            sample_values=["55/2"], computed_value="57/2", threshold="30", comparison="mean <= threshold",
            status=status, reason="x")
    return run


def test_results_list_problem_rows_before_passes(org_client, org_user):
    run = make_run(org_user.organization, ["pass", "missing-data", "pass", "exceedance"])
    order = [r.status for r in org_client.get(reverse("validation_results", args=[run.pk])).context["results"]]
    assert order == ["exceedance", "missing-data", "pass", "pass"]


def test_results_page_shows_decimals(org_client, org_user):
    run = make_run(org_user.organization, ["pass"])
    assert "28.5 (57/2)" in org_client.get(reverse("validation_results", args=[run.pk])).content.decode()


def test_error_flash_is_styled_as_error(org_client, org_user):
    from unittest.mock import patch
    from apps.ai_assist.services import ExplanationError

    run = make_run(org_user.organization, ["pass"])
    result = run.results.get()
    with patch("apps.validation.views.explain_result", side_effect=ExplanationError("x")):
        body = org_client.post(reverse("explain_limit_result", args=[result.pk]), follow=True).content.decode()
    assert 'class="alert alert-error"' in body and 'role="alert"' in body


def test_form_error_is_an_alert_block(org_client):
    from django.core.files.uploadedfile import SimpleUploadedFile

    body = org_client.post(reverse("validation_new"), {
        "csv_file": SimpleUploadedFile("a.csv", b"id\n1\n"), "permit_slug": "pa0000000", "period": "2026-03",
    }).content.decode()
    assert 'class="alert alert-error"' in body


def test_empty_run_list_points_to_new_run(org_client):
    body = org_client.get(reverse("validation_run_list")).content.decode()
    assert "Upload a lab CSV" in body and reverse("validation_new") in body
