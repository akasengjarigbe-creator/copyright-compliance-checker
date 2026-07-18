import asyncio
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from fastapi import HTTPException
from starlette.datastructures import UploadFile

from app.api import routes
from app.models.schemas import (
    AnalyseUrlRequest,
    LlmCriterionAssessment,
    LlmImageAssessment,
)


def _build_test_zip(
    files: dict[str, str],
) -> bytes:
    """
    Create an in-memory ZIP archive for API testing.
    """

    buffer = BytesIO()

    with ZipFile(
        buffer,
        mode="w",
        compression=ZIP_DEFLATED,
    ) as archive:
        for filename, content in files.items():
            archive.writestr(
                filename,
                content,
            )

    return buffer.getvalue()


def _fake_llm_assessment(
    evidence,
    intended_use: str,
) -> LlmImageAssessment:
    """
    Return a controlled AI assessment without contacting Ollama.

    This keeps the API tests fast, predictable, and independent
    of whether the local model is currently running.
    """

    assert intended_use == "educational coursework"

    return LlmImageAssessment(
        image_src=evidence.image.src,
        overall_label="Fully Compliant",
        criteria=[
            LlmCriterionAssessment(
                criterion="Copyright owner identified",
                passed=True,
                rationale=(
                    "Jane Smith is explicitly identified "
                    "as the image creator."
                ),
            ),
            LlmCriterionAssessment(
                criterion="Licence identified",
                passed=True,
                rationale=(
                    "The CC BY 4.0 licence is explicitly stated."
                ),
            ),
            LlmCriterionAssessment(
                criterion="Licence URL provided",
                passed=True,
                rationale=(
                    "A direct link to the CC BY 4.0 licence "
                    "terms is provided."
                ),
            ),
            LlmCriterionAssessment(
                criterion="Attribution completeness",
                passed=True,
                rationale=(
                    "The attribution includes both the creator "
                    "and the applicable licence."
                ),
            ),
            LlmCriterionAssessment(
                criterion="Licence conditions understood",
                passed=True,
                rationale=(
                    "The webpage explains that educational use "
                    "is permitted when attribution is provided."
                ),
            ),
            LlmCriterionAssessment(
                criterion="Usage limits checked",
                passed=True,
                rationale=(
                    "The declared educational use does not "
                    "conflict with the detected licence."
                ),
            ),
        ],
        explanation=(
            "The image contains a named creator, a recognised "
            "licence, a licence URL, complete attribution, and "
            "an intended use that is compatible with the licence."
        ),
        manual_review_required=False,
    )


def test_analyse_url_runs_complete_pipeline(
    monkeypatch,
):
    """
    Confirm that URL analysis returns separate rule-based,
    AI, and comparison results.
    """

    fake_html = """
    <html>
        <body>
            <figure>
                <img src="cat.jpg" alt="Cat photograph">

                <figcaption>
                    Photo by Jane Smith.
                    Licensed under CC BY 4.0.
                </figcaption>
            </figure>

            <p>
                This licence permits educational use
                when attribution is provided.
            </p>

            <a href="https://creativecommons.org/licenses/by/4.0/">
                View licence
            </a>
        </body>
    </html>
    """

    def fake_fetch_webpage_html(
        url: str,
    ) -> str:
        assert url == "https://example.com/page.html"
        return fake_html

    monkeypatch.setattr(
        routes,
        "fetch_webpage_html",
        fake_fetch_webpage_html,
    )

    monkeypatch.setattr(
        routes,
        "assess_image_with_llm",
        _fake_llm_assessment,
    )

    payload = AnalyseUrlRequest(
        url="https://example.com/page.html",
        intended_use="educational coursework",
    )

    report = routes.analyse_url(payload)

    assert report.total_images == 1
    assert report.overall_rule_score == 100

    assert report.rule_fully_compliant == 1
    assert report.rule_partially_compliant == 0
    assert report.rule_non_compliant == 0

    assert report.ai_fully_compliant == 1
    assert report.ai_partially_compliant == 0
    assert report.ai_non_compliant == 0

    assert report.systems_agree_count == 1
    assert report.systems_disagree_count == 0

    assert report.manual_review_recommended is False
    assert report.manual_review_count == 0

    assert len(report.image_results) == 1

    image_result = report.image_results[0]

    assert image_result.image_src == (
        "https://example.com/cat.jpg"
    )

    assert (
        image_result.rule_based_result.label
        == "Fully Compliant"
    )

    assert (
        image_result.rule_based_result.total_score
        == 100
    )

    assert (
        image_result.ai_result.overall_label
        == "Fully Compliant"
    )

    assert (
        image_result.comparison_result.systems_agree
        is True
    )

    assert (
        image_result.comparison_result
        .manual_review_recommended
        is False
    )


def test_analyse_url_converts_fetch_error_to_http_400(
    monkeypatch,
):
    """
    Confirm that webpage-retrieval errors become HTTP 400
    responses.
    """

    def fake_fetch_webpage_html(
        url: str,
    ) -> str:
        raise routes.WebpageFetchError(
            "The webpage could not be retrieved."
        )

    monkeypatch.setattr(
        routes,
        "fetch_webpage_html",
        fake_fetch_webpage_html,
    )

    payload = AnalyseUrlRequest(
        url="https://example.com/missing.html",
    )

    with pytest.raises(
        HTTPException
    ) as captured_error:
        routes.analyse_url(payload)

    assert captured_error.value.status_code == 400

    assert captured_error.value.detail == (
        "The webpage could not be retrieved."
    )


def test_analyse_zip_runs_complete_pipeline(
    monkeypatch,
):
    """
    Confirm that a ZIP submission returns separate rule-based,
    AI, and comparison results.
    """

    html = """
    <html>
        <body>
            <figure>
                <img
                    src="images/cat.jpg"
                    alt="Cat photograph"
                >

                <figcaption>
                    Photo by Jane Smith.
                    Licensed under CC BY 4.0.
                </figcaption>
            </figure>

            <p>
                This licence permits educational use
                when attribution is provided.
            </p>

            <a
                href="https://creativecommons.org/licenses/by/4.0/"
            >
                View licence
            </a>
        </body>
    </html>
    """

    zip_data = _build_test_zip(
        {
            "index.html": html,
            "images/cat.jpg": "fake-image-data",
        }
    )

    monkeypatch.setattr(
        routes,
        "assess_image_with_llm",
        _fake_llm_assessment,
    )

    uploaded_file = UploadFile(
        filename="coursework.zip",
        file=BytesIO(zip_data),
    )

    report = asyncio.run(
        routes.analyse_zip(
            file=uploaded_file,
            intended_use="educational coursework",
        )
    )

    assert report.total_images == 1
    assert report.overall_rule_score == 100

    assert report.rule_fully_compliant == 1
    assert report.rule_partially_compliant == 0
    assert report.rule_non_compliant == 0

    assert report.ai_fully_compliant == 1
    assert report.ai_partially_compliant == 0
    assert report.ai_non_compliant == 0

    assert report.systems_agree_count == 1
    assert report.systems_disagree_count == 0

    assert report.manual_review_recommended is False
    assert report.manual_review_count == 0

    assert len(report.image_results) == 1

    image_result = report.image_results[0]

    assert image_result.image_src == (
        "https://submission.local/images/cat.jpg"
    )

    assert (
        image_result.rule_based_result.label
        == "Fully Compliant"
    )

    assert (
        image_result.rule_based_result.total_score
        == 100
    )

    assert (
        image_result.ai_result.overall_label
        == "Fully Compliant"
    )

    assert (
        image_result.comparison_result.systems_agree
        is True
    )

    assert (
        image_result.comparison_result
        .manual_review_recommended
        is False
    )


def test_analyse_zip_rejects_non_zip_filename():
    """
    Confirm that files without a .zip extension are rejected.
    """

    uploaded_file = UploadFile(
        filename="coursework.txt",
        file=BytesIO(
            b"Not a ZIP file"
        ),
    )

    with pytest.raises(
        HTTPException
    ) as captured_error:
        asyncio.run(
            routes.analyse_zip(
                file=uploaded_file,
                intended_use=(
                    "educational coursework"
                ),
            )
        )

    assert captured_error.value.status_code == 400

    assert captured_error.value.detail == (
        "The uploaded file must have a .zip extension."
    )