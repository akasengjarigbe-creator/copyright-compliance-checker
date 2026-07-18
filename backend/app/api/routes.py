from pathlib import PurePosixPath

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
from app.detector.image_detector import (
    detect_images,
)
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
    ImageAssessment,
    LlmImageAssessment,
    ThreeResultComplianceReport,
)
from app.parser.html_parser import parse_html
from app.report.three_result_report_generator import (
    build_three_result_report,
)
from app.rule_engine.rule_checker import (
    assess_images,
)


router = APIRouter()


def _analyse_html_content(
    html: str,
    base_url: str | None,
    intended_use: str,
) -> ThreeResultComplianceReport:
    """
    Analyse one HTML page using:

    1. The deterministic rule engine
    2. The local AI reasoning module
    3. The comparison engine
    """

    parsed = parse_html(
        html,
        base_url=base_url,
    )

    images = detect_images(parsed)

    evidence_items = (
        extract_attribution_evidence(
            parsed,
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

    return build_three_result_report(
        rule_assessments=rule_assessments,
        ai_assessments=ai_assessments,
    )


def _create_zip_page_base_url(
    relative_path: str,
) -> str:
    """
    Create an internal base URL for an HTML page
    contained in a ZIP submission.
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
) -> ThreeResultComplianceReport:
    """
    Analyse every HTML page contained in a ZIP file.

    All rule-based and AI image assessments are combined
    into one three-result report.
    """

    documents = read_html_documents_from_zip(
        zip_data
    )

    all_rule_assessments: list[
        ImageAssessment
    ] = []

    all_ai_assessments: list[
        LlmImageAssessment
    ] = []

    for document in documents:
        base_url = _create_zip_page_base_url(
            document.relative_path
        )

        parsed = parse_html(
            document.html,
            base_url=base_url,
        )

        images = detect_images(parsed)

        evidence_items = (
            extract_attribution_evidence(
                parsed,
                images,
            )
        )

        page_rule_assessments = assess_images(
            evidence_items,
            intended_use=intended_use,
        )

        page_ai_assessments: list[
            LlmImageAssessment
        ] = []

        for evidence in evidence_items:
            ai_assessment = (
                assess_image_with_llm(
                    evidence=evidence,
                    intended_use=intended_use,
                )
            )

            page_ai_assessments.append(
                ai_assessment
            )

        all_rule_assessments.extend(
            page_rule_assessments
        )

        all_ai_assessments.extend(
            page_ai_assessments
        )

    return build_three_result_report(
        rule_assessments=(
            all_rule_assessments
        ),
        ai_assessments=(
            all_ai_assessments
        ),
    )


@router.post(
    "/analyse-html",
    response_model=ThreeResultComplianceReport,
)
def analyse_html(
    payload: AnalyseHtmlRequest,
) -> ThreeResultComplianceReport:
    """
    Analyse HTML and return separate rule-based,
    AI, and comparison results.
    """

    try:
        return _analyse_html_content(
            html=payload.html,
            base_url=payload.base_url,
            intended_use=payload.intended_use,
        )

    except LlmReasoningError as error:
        raise HTTPException(
            status_code=503,
            detail=(
                "The AI assessment could not "
                f"be completed: {error}"
            ),
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error


@router.post(
    "/analyse-url",
    response_model=ThreeResultComplianceReport,
)
def analyse_url(
    payload: AnalyseUrlRequest,
) -> ThreeResultComplianceReport:
    """
    Retrieve a webpage and return separate rule-based,
    AI, and comparison results.
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
        raise HTTPException(
            status_code=503,
            detail=(
                "The AI assessment could not "
                f"be completed: {error}"
            ),
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error


@router.post(
    "/analyse-zip",
    response_model=ThreeResultComplianceReport,
)
async def analyse_zip(
    file: UploadFile = File(...),
    intended_use: str = Form(
        "educational coursework"
    ),
) -> ThreeResultComplianceReport:
    """
    Analyse every HTML page in an uploaded ZIP file
    and return separate rule-based, AI, and comparison
    results.
    """

    filename = file.filename or ""

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
        raise HTTPException(
            status_code=503,
            detail=(
                "The AI assessment could not "
                f"be completed: {error}"
            ),
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    finally:
        await file.close()