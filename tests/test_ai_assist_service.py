from unittest.mock import patch

import pytest

from apps.ai_assist.services import ExplanationError, explain_result
from apps.validation.models import LimitResult, ValidationRun


def make_result(**overrides):
    run = ValidationRun.objects.create(
        permit_slug="pa0000000", pipeline_slug="lab-csv-import",
        status="success", schema_version=1,
    )
    fields = dict(
        run=run, outfall=1, parameter="TSS", clause="monthly-avg",
        sample_ids=["r1"], sample_values=["27.5"],
        computed_value="27.5", threshold="30", comparison="mean <= threshold",
        status="pass", reason="monthly-avg is within limits.",
    )
    fields.update(overrides)
    return LimitResult.objects.create(**fields)


def snapshot(result):
    result.refresh_from_db()
    return {f: getattr(result, f) for f in
            ("outfall", "parameter", "clause", "sample_ids", "sample_values",
             "computed_value", "threshold", "comparison", "status", "reason")}


@pytest.mark.django_db
def test_failed_explanation_does_not_alter_stored_status_or_any_other_field():
    result = make_result()
    before = snapshot(result)

    with patch("apps.ai_assist.services._call_gemini", side_effect=RuntimeError("quota exceeded")):
        with pytest.raises(ExplanationError):
            explain_result(result.pk)

    after = snapshot(result)
    assert after == before
    assert result.gemini_explanation is None


@pytest.mark.django_db
def test_successful_explanation_only_changes_gemini_explanation_field():
    result = make_result()
    before = snapshot(result)

    with patch("apps.ai_assist.services._call_gemini", return_value="TSS stayed within its monthly average limit."):
        explanation = explain_result(result.pk)

    after = snapshot(result)
    assert after == before  # every engine-owned field is untouched
    result.refresh_from_db()
    assert result.gemini_explanation == explanation == "TSS stayed within its monthly average limit."
    assert result.status == "pass"  # explicitly: Gemini never wrote status
