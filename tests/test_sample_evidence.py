"""The fictional files in tests/fixtures/sample_evidence must stay reviewable.

Claude is mocked; this covers upload -> text extraction -> review persistence
for each real fixture file, so a break in the xlsx/docx reader shows up here
rather than in the browser.
"""

from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.ingestion import claude_review
from apps.ingestion.models import Evidence

FIXTURES = Path(__file__).parent / "fixtures" / "sample_evidence"
FILES = ["01_lab_results_complete.xlsx", "02_lab_results_incomplete.xlsx", "03_chain_of_custody_gaps.docx"]

TOOL_RESPONSE = {
    "content": [{
        "type": "tool_use", "name": claude_review.TOOL_NAME,
        "input": {
            "overall_match": 80, "summary": "A fictional document.", "key_criteria": [],
            "partial_matches": [], "potential_gaps": [], "key_statements": [],
            "recommendation": "accept",
        },
    }],
}


@pytest.fixture(autouse=True)
def temporary_media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def make_evidence(org_user, name):
    return Evidence.objects.create(
        organization=org_user.organization,
        uploaded_by=org_user,
        file=SimpleUploadedFile(name, (FIXTURES / name).read_bytes()),
        original_name=name,
        size=(FIXTURES / name).stat().st_size,
        review_status=Evidence.ReviewStatus.IN_REVIEW,
        review_run=1,
    )


@pytest.mark.parametrize("name", FILES)
def test_fixture_is_read_into_prompt_text(org_user, name):
    item = make_evidence(org_user, name)

    parts = claude_review.build_content_parts(item)

    document = parts[0]["text"]
    assert name in document
    assert "FICTIONAL TEST DATA" in document


def test_non_detect_and_columns_survive_extraction(org_user):
    item = make_evidence(org_user, "01_lab_results_complete.xlsx")

    document = claude_review.build_content_parts(item)[0]["text"]

    assert "S-0319-TSS\t2026-03-19\tTSS\t<2.5\tmg/L" in document


@pytest.mark.parametrize("name", FILES)
def test_fixture_completes_a_review(org_user, name):
    item = make_evidence(org_user, name)

    with patch("apps.ingestion.claude_review._post_to_claude", return_value=TOOL_RESPONSE):
        claude_review.run_review(item.pk, 1)

    item.refresh_from_db()
    assert item.review_status == Evidence.ReviewStatus.REVIEWED, item.review_error
    assert item.review_result["overall_match"] == 80
