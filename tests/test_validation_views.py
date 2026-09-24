from unittest.mock import patch

import pytest
from django.urls import reverse

from apps.validation.models import LimitResult, ProvenanceEntry, RejectionEntry, ValidationRun
from apps.validation.services import EngineError, InvalidSlugError

PERMIT_SLUG = "pa0000000"
PIPELINE_SLUG = "lab-csv-import"


def make_run(**overrides):
    fields = dict(permit_slug=PERMIT_SLUG, pipeline_slug=PIPELINE_SLUG,
                  status="success", schema_version=1, period="2026-03")
    fields.update(overrides)
    return ValidationRun.objects.create(**fields)


def make_result(run, **overrides):
    fields = dict(
        run=run, outfall=1, parameter="TSS", clause="daily-max",
        sample_ids=["r1"], sample_values=["70"],
        computed_value="70", threshold="60", comparison="max <= threshold",
        status="pass", reason="engine reason text",
    )
    fields.update(overrides)
    return LimitResult.objects.create(**fields)


# --- validation_results: badges and trace values ---

@pytest.mark.django_db
def test_exceedance_row_displays_its_trace_values_correctly(client):
    run = make_run()
    make_result(run, status="exceedance", parameter="TSS", clause="daily-max",
                sample_ids=["r1", "r2"], sample_values=["65", "70"],
                computed_value="70", threshold="60", reason="daily-max exceeds the permit limit (computed 70).")

    response = client.get(reverse("validation_results", args=[run.pk]))

    assert response.status_code == 200
    content = response.content.decode()
    assert 'badge danger' in content
    assert 'data-status="exceedance"' in content
    assert "70" in content and "60" in content
    assert "r1, r2" in content
    assert "daily-max exceeds the permit limit (computed 70)." in content


@pytest.mark.django_db
@pytest.mark.parametrize("status,expected_class", [
    ("pass", "badge success"),
    ("exceedance", "badge danger"),
    ("missing-data", "badge warning"),
    ("unit-error", "badge unit-error"),
    ("report-only", "badge info"),
])
def test_each_status_renders_its_own_badge_class(client, status, expected_class):
    run = make_run()
    make_result(run, status=status, parameter=status.upper())

    response = client.get(reverse("validation_results", args=[run.pk]))
    content = response.content.decode()

    assert f'data-status="{status}"' in content
    # the badge span for this exact status carries the expected class
    marker = f'class="{expected_class}" data-status="{status}"'
    assert marker in content


@pytest.mark.django_db
def test_failed_run_shows_error_state_not_a_blank_page(client):
    run = make_run(status="failed", error_code="timeout",
                    error_message="racket did not exit within 30s")

    response = client.get(reverse("validation_results", args=[run.pk]))
    content = response.content.decode()

    assert response.status_code == 200
    assert "timeout" in content
    assert "racket did not exit within 30s" in content
    assert "<table" not in content  # no misleading empty results table


@pytest.mark.django_db
def test_validation_results_unknown_run_is_404(client):
    response = client.get(reverse("validation_results", args=[999999]))
    assert response.status_code == 404


# --- provenance_timeline ---

@pytest.mark.django_db
def test_rejected_record_appears_in_its_timeline_with_reason(client):
    run = make_run()
    ProvenanceEntry.objects.create(run=run, step="map-column", record_id="bad1",
                                    before={"Analyte": "TSS"}, after={"parameter": "TSS"},
                                    note="renamed column Analyte to parameter")
    RejectionEntry.objects.create(run=run, step="require-field", record_id="bad1",
                                   reason="missing required field(s): method")
    ProvenanceEntry.objects.create(run=run, step="map-column", record_id="good1",
                                    before={"Analyte": "TSS"}, after={"parameter": "TSS"},
                                    note="renamed column Analyte to parameter")

    response = client.get(reverse("provenance_timeline", args=[run.pk]))
    content = response.content.decode()

    assert response.status_code == 200
    assert "rejected at require-field" in content
    assert "missing required field(s): method" in content
    # the clean record shows no rejection marker
    assert content.index('data-record-id="bad1"') < content.index('data-record-id="good1"')
    good_section = content.split('data-record-id="good1"')[1]
    assert "rejected at" not in good_section.split('</section>')[0]


# --- permit_rules: 404 vs 502 split ---

@pytest.mark.django_db
def test_unknown_permit_slug_is_404_and_never_calls_subprocess(client):
    with patch("apps.validation.services.subprocess.run") as mock_run:
        response = client.get(reverse("permit_rules", args=["not-a-real-permit"]))

    assert response.status_code == 404
    mock_run.assert_not_called()


@pytest.mark.django_db
def test_engine_error_renders_error_state_with_5xx_status(client):
    with patch("apps.validation.views.describe_permit",
               side_effect=EngineError("engine-crash", "/some/internal/path leaked here")):
        response = client.get(reverse("permit_rules", args=[PERMIT_SLUG]))

    assert response.status_code == 502
    content = response.content.decode()
    assert "engine-crash" in content
    assert "/some/internal/path" not in content  # raw engine message never shown


@pytest.mark.django_db
def test_permit_rules_happy_path_renders_describe_output(client):
    fake_permit = {
        "permit_id": "PA0000000",
        "outfalls": [{
            "outfall": 1,
            "limits": [{
                "parameter": "TSS",
                "clauses": [{"type": "daily-max", "threshold": "60", "unit": "mg/L"}],
            }],
        }],
    }
    with patch("apps.validation.views.describe_permit", return_value=fake_permit):
        response = client.get(reverse("permit_rules", args=[PERMIT_SLUG]))

    assert response.status_code == 200
    content = response.content.decode()
    assert "PA0000000" in content
    assert "TSS" in content
    assert "60" in content and "mg/L" in content
