import json
from unittest.mock import patch

import pytest

from apps.ai_assist.citations import CITATIONS_VERSION
from apps.ai_assist.services import ExplanationError, build_context, explain_result
from apps.validation.models import LimitResult, ProvenanceEntry, RejectionEntry, ValidationRun


def make_result(**overrides):
    run = ValidationRun.objects.create(
        organization=None, permit_slug="pa0000000", pipeline_slug="lab-csv-import",
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

    with patch("apps.ai_assist.services._call_claude", side_effect=RuntimeError("quota exceeded")):
        with pytest.raises(ExplanationError):
            explain_result(result.pk)

    after = snapshot(result)
    assert after == before
    assert result.explanation is None


def model_output(explanation, refs):
    return json.dumps({"explanation": explanation, "refs": refs})


GOOD = "TSS averaged 27.5 against a limit of 30, so it stayed within the monthly average limit."


@pytest.mark.django_db
def test_successful_explanation_only_changes_explanation_fields():
    result = make_result()
    before = snapshot(result)

    with patch("apps.ai_assist.services._call_claude",
               return_value=model_output(GOOD, ["cite:monthly-avg"])):
        explanation = explain_result(result.pk)

    after = snapshot(result)
    assert after == before  # every engine-owned field is untouched
    result.refresh_from_db()
    assert result.explanation == explanation == GOOD
    assert result.explanation_refs == {"refs": ["cite:monthly-avg"], "citations_version": CITATIONS_VERSION}
    assert result.status == "pass"  # explicitly: Claude never wrote status


@pytest.mark.django_db
def test_context_contains_only_this_results_provenance_and_applicable_citations():
    result = make_result(sample_ids=["r1"])
    mine = ProvenanceEntry.objects.create(
        run=result.run, step="convert-units", record_id="r1", before={"v": "27500"}, after={"v": "27.5"}, note="ug/L -> mg/L")
    ProvenanceEntry.objects.create(
        run=result.run, step="convert-units", record_id="other", before={}, after={}, note="unrelated")
    rejected = RejectionEntry.objects.create(run=result.run, step="require-field", record_id="r1", reason="missing method")

    context = build_context(result)

    assert [p["id"] for p in context["provenance"]] == [f"prov:{mine.pk}"]
    assert [r["id"] for r in context["rejections"]] == [f"rej:{rejected.pk}"]
    assert [c["id"] for c in context["citations"]] == ["cite:monthly-avg", "cite:averaging", "cite:dmr-reporting"]


@pytest.mark.django_db
@pytest.mark.parametrize("raw, why", [
    ("not json", "not valid JSON"),
    (model_output(GOOD, []), "cited no sources"),
    (model_output(GOOD, ["cite:made-up"]), "not in the context"),
    (model_output(GOOD, ["prov:99999"]), "not in the context"),
    (model_output("TSS averaged 28 against a limit of 30.", ["cite:monthly-avg"]), "numbers not in the context"),
    (model_output("", ["cite:monthly-avg"]), "text was missing"),
])
def test_unverified_explanation_is_rejected_and_nothing_is_written(raw, why):
    result = make_result()
    before = snapshot(result)

    with patch("apps.ai_assist.services._call_claude", return_value=raw):
        with pytest.raises(ExplanationError, match=why):
            explain_result(result.pk)

    assert snapshot(result) == before
    assert result.explanation is None
    assert result.explanation_refs is None


@pytest.mark.django_db
def test_json_in_a_code_fence_is_accepted():
    result = make_result()
    fenced = "```json\n" + model_output(GOOD, ["cite:monthly-avg"]) + "\n```"

    with patch("apps.ai_assist.services._call_claude", return_value=fenced):
        assert explain_result(result.pk) == GOOD
