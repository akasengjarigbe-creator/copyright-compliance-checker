from pathlib import PurePosixPath
from typing import NoReturn

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from app.crawler.webpage_fetcher import (
    WebpageFetchError,
    fetch_webpage_html,
)
from app.crawler.zip_processor import (
    ZipProcessingError,
    read_html_documents_from_zip,
)
from app.detector.image_detector import detect_images
from app.extractor.attribution_extractor import (
    extract_attribution_evidence,
)
from app.llm.llm_reasoner import (
    LlmReasoningError,
    assess_image_with_llm,
)
from app.models.schemas import (
    AnalyseHtmlRequest,
    AnalyseUrlRequest,
    AttributionEvidence,
    ComplianceReport,
    ImageAssessment,
    LlmImageAssessment,
)
from app.parser.html_parser import parse_html
from app.report.report_generator import build_report
from app.rule_engine.rule_checker import assess_images


router = APIRouter()


def _analyse_page(
    html: str,
    base_url: str | None,
    intended_use: str,
) -> tuple[
    list[AttributionEvidence],
    list[ImageAssessment],
    list[LlmImageAssessment],
]:
    """
    Analyse one HTML page.

    The analysis process:

    1. Parses the HTML.
    2. Detects images.
    3. Extracts copyright, source and licence evidence.
    4. Runs the deterministic rule-based assessment.
    5. Runs the AI-assisted assessment.

    The rule-based and AI assessments remain independent.
    """

    parsed_document = parse_html(
        html,
        base_url=base_url,
    )

    images = detect_images(
        parsed_document
    )

    evidence_items = (
        extract_attribution_evidence(
            parsed_document,
            images,
        )
    )

    rule_assessments = assess_images(
        evidence_items,
        intended_use=intended_use,
    )

    ai_assessments: list[
        LlmImageAssessment
    ] = []

    for evidence in evidence_items:
        ai_assessment = (
            assess_image_with_llm(
                evidence=evidence,
                intended_use=intended_use,
            )
        )

        ai_assessments.append(
            ai_assessment
        )

    return (
        evidence_items,
        rule_assessments,
        ai_assessments,
    )


def _analyse_html_content(
    html: str,
    base_url: str | None,
    intended_use: str,
) -> ComplianceReport:
    """
    Analyse one HTML document and build the final report.

    The complete HTML document is not included in the final
    report. Only the evidence associated with each detected
    image and the relevant analysed fragment are retained.
    """

    (
        evidence_items,
        rule_assessments,
        ai_assessments,
    ) = _analyse_page(
        html=html,
        base_url=base_url,
        intended_use=intended_use,
    )

    return build_report(
        evidence_items=evidence_items,
        rule_assessments=rule_assessments,
        ai_assessments=ai_assessments,
    )


def _create_zip_page_base_url(
    relative_path: str,
) -> str:
    """
    Create an internal URL representing an HTML file inside
    a ZIP submission.

    This allows relative image paths and relative links to be
    resolved consistently.
    """

    normalised_path = PurePosixPath(
        relative_path
    )

    return (
        "https://submission.local/"
        f"{normalised_path.as_posix()}"
    )


def _analyse_zip_content(
    zip_data: bytes,
    intended_use: str,
) -> ComplianceReport:
    """
    Analyse all HTML documents contained in a ZIP file.

    Evidence and assessments from each HTML page are combined
    into a single compliance report.
    """

    documents = (
        read_html_documents_from_zip(
            zip_data
        )
    )

    all_evidence_items: list[
        AttributionEvidence
    ] = []

    all_rule_assessments: list[
        ImageAssessment
    ] = []

    all_ai_assessments: list[
        LlmImageAssessment
    ] = []

    for document in documents:
        base_url = (
            _create_zip_page_base_url(
                document.relative_path
            )
        )

        (
            page_evidence_items,
            page_rule_assessments,
            page_ai_assessments,
        ) = _analyse_page(
            html=document.html,
            base_url=base_url,
            intended_use=intended_use,
        )

        all_evidence_items.extend(
            page_evidence_items
        )

        all_rule_assessments.extend(
            page_rule_assessments
        )

        all_ai_assessments.extend(
            page_ai_assessments
        )

    return build_report(
        evidence_items=all_evidence_items,
        rule_assessments=all_rule_assessments,
        ai_assessments=all_ai_assessments,
    )


def _raise_llm_http_error(
    error: LlmReasoningError,
) -> NoReturn:
    """
    Convert an AI-assessment failure into HTTP 503.

    A 503 is used because the main application may be running
    correctly while the local Ollama service is unavailable or
    unable to complete the assessment.
    """

    raise HTTPException(
        status_code=503,
        detail=(
            "The AI assessment could not be completed: "
            f"{error}"
        ),
    ) from error


def _raise_value_http_error(
    error: ValueError,
) -> NoReturn:
    """
    Convert a validation or report-building error into HTTP 400.
    """

    raise HTTPException(
        status_code=400,
        detail=str(error),
    ) from error


@router.post(
    "/analyse-html",
    response_model=ComplianceReport,
)
def analyse_html(
    payload: AnalyseHtmlRequest,
) -> ComplianceReport:
    """
    Analyse HTML supplied directly by the user.
    """

    try:
        return _analyse_html_content(
            html=payload.html,
            base_url=payload.base_url,
            intended_use=payload.intended_use,
        )

    except LlmReasoningError as error:
        _raise_llm_http_error(
            error
        )

    except ValueError as error:
        _raise_value_http_error(
            error
        )


@router.post(
    "/analyse-url",
    response_model=ComplianceReport,
)
def analyse_url(
    payload: AnalyseUrlRequest,
) -> ComplianceReport:
    """
    Retrieve a webpage and analyse its images.
    """

    try:
        html = fetch_webpage_html(
            payload.url
        )

        return _analyse_html_content(
            html=html,
            base_url=payload.url,
            intended_use=payload.intended_use,
        )

    except WebpageFetchError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except LlmReasoningError as error:
        _raise_llm_http_error(
            error
        )

    except ValueError as error:
        _raise_value_http_error(
            error
        )


@router.post(
    "/analyse-zip",
    response_model=ComplianceReport,
)
async def analyse_zip(
    file: UploadFile = File(...),
    intended_use: str = Form(
        "educational coursework"
    ),
) -> ComplianceReport:
    """
    Analyse all HTML pages contained in a ZIP submission.
    """

    filename = (
        file.filename or ""
    )

    if not filename.lower().endswith(
        ".zip"
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "The uploaded file must have "
                "a .zip extension."
            ),
        )

    try:
        zip_data = await file.read()

        if not zip_data:
            raise HTTPException(
                status_code=400,
                detail=(
                    "The uploaded ZIP file is empty."
                ),
            )

        return _analyse_zip_content(
            zip_data=zip_data,
            intended_use=intended_use,
        )

    except ZipProcessingError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except LlmReasoningError as error:
        _raise_llm_http_error(
            error
        )

    except ValueError as error:
        _raise_value_http_error(
            error
        )

    finally:
        await file.close()