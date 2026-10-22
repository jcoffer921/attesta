import json
import subprocess
from unittest.mock import patch

import pytest

from apps.validation.models import LimitResult, ProvenanceEntry, RejectionEntry, ValidationRun
from apps.validation.services import EngineError, InvalidSlugError, run_validation

PERMIT_SLUG = "pa0000000"
PIPELINE_SLUG = "lab-csv-import"

RECORDS = [
    {"id": "r1", "outfall": 1, "Analyte": "TSS", "value": "27.5", "unit": "mg/L",
     "sample_date": "2026-03-05", "method": "SM2540D"},
]


def completed(returncode, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=[], returncode=returncode,
                                        stdout=stdout.encode("utf-8"),
                                        stderr=stderr.encode("utf-8"))


@pytest.fixture
def org(db):
    from apps.facilities.models import Organization

    return Organization.objects.create(name="Svc Org", slug="svc-org")


def counts():
    return (ValidationRun.objects.count(), LimitResult.objects.count(),
            ProvenanceEntry.objects.count(), RejectionEntry.objects.count())


@pytest.mark.django_db
def test_nonzero_exit_with_structured_error_persists_failed_run_and_no_children(org):
    error_body = json.dumps({"error": {"code": "invalid-path", "message": "--permit must be under ..."}})
    with patch("apps.validation.services.subprocess.run", return_value=completed(1, stdout=error_body)):
        with pytest.raises(EngineError) as exc_info:
            run_validation(organization=org, permit_slug=PERMIT_SLUG, pipeline_slug=PIPELINE_SLUG, records=RECORDS)

    assert exc_info.value.code == "invalid-path"
    assert counts() == (1, 0, 0, 0)
    run = ValidationRun.objects.get()
    assert run.status == "failed"
    assert run.error_code == "invalid-path"


@pytest.mark.django_db
def test_timeout_persists_failed_run_with_timeout_code(org):
    with patch("apps.validation.services.subprocess.run",
               side_effect=subprocess.TimeoutExpired(cmd=["racket"], timeout=30)):
        with pytest.raises(EngineError) as exc_info:
            run_validation(organization=org, permit_slug=PERMIT_SLUG, pipeline_slug=PIPELINE_SLUG, records=RECORDS)

    assert exc_info.value.code == "timeout"
    assert counts() == (1, 0, 0, 0)
    assert ValidationRun.objects.get().status == "failed"


@pytest.mark.django_db
def test_malformed_json_on_success_exit_persists_failed_run(org):
    with patch("apps.validation.services.subprocess.run", return_value=completed(0, stdout="not json")):
        with pytest.raises(EngineError) as exc_info:
            run_validation(organization=org, permit_slug=PERMIT_SLUG, pipeline_slug=PIPELINE_SLUG, records=RECORDS)

    assert exc_info.value.code == "invalid-json"
    assert counts() == (1, 0, 0, 0)


@pytest.mark.django_db
def test_unexpected_schema_version_persists_failed_run(org):
    body = json.dumps({"schema_version": 4, "results": [], "provenance": [], "rejections": []})
    with patch("apps.validation.services.subprocess.run", return_value=completed(0, stdout=body)):
        with pytest.raises(EngineError) as exc_info:
            run_validation(organization=org, permit_slug=PERMIT_SLUG, pipeline_slug=PIPELINE_SLUG, records=RECORDS)

    assert exc_info.value.code == "unexpected-schema-version"
    run = ValidationRun.objects.get()
    assert run.status == "failed"
    assert run.schema_version == 4
    assert counts() == (1, 0, 0, 0)


@pytest.mark.django_db
def test_successful_run_persists_results_exactly_as_returned(org):
    body = json.dumps({
        "schema_version": 3,
        "results": [{
            "outfall": 1, "parameter": "TSS", "clause": "monthly-avg",
            "sample_ids": ["r1"], "sample_values": ["55/2"],
            "computed_value": "55/2", "threshold": "30", "comparison": "mean <= threshold",
            "status": "pass", "reason": "monthly-avg is within limits (computed 55/2).",
        }],
        "provenance": [{
            "step": "map-column", "record_id": "r1",
            "before": {"Analyte": "TSS"}, "after": {"parameter": "TSS"},
            "note": "renamed column Analyte to parameter",
        }],
        "rejections": [{"step": "require-field", "record_id": "r2", "reason": "missing required field(s): method"}],
    })
    with patch("apps.validation.services.subprocess.run", return_value=completed(0, stdout=body)):
        run = run_validation(organization=org, permit_slug=PERMIT_SLUG, pipeline_slug=PIPELINE_SLUG, records=RECORDS)

    assert run.status == "success"
    assert run.permit_file_sha256 and run.pipeline_file_sha256

    result = run.results.get()
    assert result.status == "pass"  # engine's status, unchanged
    assert result.computed_value == "55/2"

    prov = run.provenance_entries.get()
    assert prov.note == "renamed column Analyte to parameter"

    rej = run.rejection_entries.get()
    assert rej.reason == "missing required field(s): method"

    assert counts() == (1, 1, 1, 1)


@pytest.mark.django_db
def test_invalid_slug_is_rejected_before_any_subprocess_call(org):
    with patch("apps.validation.services.subprocess.run") as mock_run:
        with pytest.raises(InvalidSlugError):
            run_validation(organization=org, permit_slug="../../etc/passwd", pipeline_slug=PIPELINE_SLUG, records=RECORDS)
    mock_run.assert_not_called()
    assert counts() == (0, 0, 0, 0)


def _success_body():
    return json.dumps({"schema_version": 3, "results": [], "provenance": [], "rejections": []})


@pytest.mark.django_db
def test_success_persists_lab_records_matching_sent_records(org):
    from apps.validation.models import LabRecord

    with patch("apps.validation.services.subprocess.run", return_value=completed(0, stdout=_success_body())):
        run = run_validation(organization=org, permit_slug=PERMIT_SLUG, pipeline_slug=PIPELINE_SLUG,
                             records=RECORDS, row_numbers=[1])

    lab = LabRecord.objects.get()
    assert lab.run == run
    assert lab.organization == org
    assert lab.data == RECORDS[0]
    assert lab.record_id == "r1"
    assert lab.row_number == 1


@pytest.mark.django_db
def test_failed_run_still_persists_lab_records(org):
    with patch("apps.validation.services.subprocess.run", return_value=completed(1, stdout="boom")):
        with pytest.raises(EngineError):
            run_validation(organization=org, permit_slug=PERMIT_SLUG, pipeline_slug=PIPELINE_SLUG,
                           records=RECORDS, row_numbers=[1])

    run = ValidationRun.objects.get()
    assert run.status == "failed"
    assert run.lab_records.count() == len(RECORDS)


@pytest.mark.django_db
def test_engine_error_carries_failed_run(org):
    with patch("apps.validation.services.subprocess.run", return_value=completed(1, stdout="boom")):
        with pytest.raises(EngineError) as exc_info:
            run_validation(organization=org, permit_slug=PERMIT_SLUG, pipeline_slug=PIPELINE_SLUG, records=RECORDS)

    assert exc_info.value.run.status == "failed"


@pytest.mark.django_db
def test_row_numbers_length_mismatch_raises_before_subprocess(org):
    with patch("apps.validation.services.subprocess.run") as run_mock:
        with pytest.raises(ValueError):
            run_validation(organization=org, permit_slug=PERMIT_SLUG, pipeline_slug=PIPELINE_SLUG,
                           records=RECORDS, row_numbers=[1, 2])

    run_mock.assert_not_called()
    assert ValidationRun.objects.count() == 0


@pytest.mark.django_db
def test_omitting_row_numbers_creates_no_lab_records(org):
    from apps.validation.models import LabRecord

    with patch("apps.validation.services.subprocess.run", return_value=completed(0, stdout=_success_body())):
        run_validation(organization=org, permit_slug=PERMIT_SLUG, pipeline_slug=PIPELINE_SLUG, records=RECORDS)

    assert LabRecord.objects.count() == 0


def test_available_permit_slugs_lists_pa0000000():
    from apps.validation.services import available_permit_slugs

    assert "pa0000000" in available_permit_slugs()


@pytest.mark.django_db
def test_missing_racket_executable_persists_failed_run_with_lab_records(org):
    with patch("apps.validation.services.subprocess.run", side_effect=FileNotFoundError("racket")):
        with pytest.raises(EngineError) as exc_info:
            run_validation(organization=org, permit_slug=PERMIT_SLUG, pipeline_slug=PIPELINE_SLUG,
                           records=RECORDS, row_numbers=[1])

    assert exc_info.value.code == "engine-unavailable"
    run = exc_info.value.run
    assert run.status == "failed" and run.lab_records.count() == 1
