from typing import Literal

from pydantic import BaseModel, Field


ComplianceLabel = Literal[
    "Fully Compliant",
    "Partially Compliant",
    "Non-Compliant",
]


class AnalyseHtmlRequest(BaseModel):
    """
    Request body for analysing HTML supplied directly.
    """

    html: str = Field(
        min_length=1,
        description="The complete HTML content to analyse.",
    )

    base_url: str | None = Field(
        default=None,
        description=(
            "Optional base URL used to resolve relative image "
            "and hyperlink paths."
        ),
    )

    intended_use: str = Field(
        default="educational coursework",
        min_length=1,
        description=(
            "The declared purpose for which the images are used."
        ),
    )


class AnalyseUrlRequest(BaseModel):
    """
    Request body for analysing a webpage by URL.
    """

    url: str = Field(
        min_length=1,
        description="The webpage URL to analyse.",
    )

    intended_use: str = Field(
        default="educational coursework",
        min_length=1,
        description=(
            "The declared purpose for which the images are used."
        ),
    )


class ParsedHtml(BaseModel):
    """
    Store parsed HTML, visible page text, and optional base URL.
    """

    html: str
    text: str
    base_url: str | None = None


class ImageRecord(BaseModel):
    """
    Information extracted from one HTML img element.
    """

    src: str = Field(
        min_length=1,
        description=(
            "The resolved technical image source path or URL. "
            "This is not automatically copyright attribution."
        ),
    )

    alt: str | None = None
    title: str | None = None

    attributes: dict[str, str] = Field(
        default_factory=dict,
    )


class AttributionEvidence(BaseModel):
    """
    Copyright and licence evidence associated with one image.
    """

    image: ImageRecord

    nearby_text: str = ""
    caption: str | None = None

    # ---------------------------------------------------------
    # Copyright owner / creator
    # ---------------------------------------------------------

    possible_author: str | None = None

    author_evidence_text: str | None = None
    author_evidence_source: str | None = None

    # ---------------------------------------------------------
    # Explicit source/reference information
    # ---------------------------------------------------------

    source_name: str | None = Field(
        default=None,
        description=(
            "Explicitly supplied source website/domain. "
            "This must not be inferred solely from image.src."
        ),
    )

    source_url: str | None = Field(
        default=None,
        description=(
            "Explicitly supplied image source/reference URL. "
            "This must not be inferred solely from image.src."
        ),
    )

    source_evidence_text: str | None = None
    source_evidence_source: str | None = None

    # ---------------------------------------------------------
    # Licence / permission
    # ---------------------------------------------------------

    licence_name: str | None = None

    licence_evidence_text: str | None = None
    licence_evidence_source: str | None = None

    # Location of applicable licence terms.
    licence_url: str | None = None

    licence_url_evidence_text: str | None = None
    licence_url_evidence_source: str | None = None

    # Optional copyright/rights information.
    rights_url: str | None = None

    rights_evidence_text: str | None = None
    rights_evidence_source: str | None = None

    # ---------------------------------------------------------
    # Internal diagnostics
    # ---------------------------------------------------------

    image_html: str | None = None
    analysed_html_fragment: str | None = None


class CriterionResult(BaseModel):
    """
    One deterministic criterion result.
    """

    criterion: str = Field(
        min_length=1,
    )

    passed: bool

    score: int = Field(
        ge=0,
    )

    weight: int = Field(
        ge=0,
    )

    rationale: str = Field(
        min_length=1,
    )


class ImageAssessment(BaseModel):
    """
    Complete deterministic assessment for one image.
    """

    image_src: str = Field(
        min_length=1,
    )

    total_score: int = Field(
        ge=0,
        le=100,
    )

    label: ComplianceLabel

    criteria: list[CriterionResult]

    manual_review_required: bool = False

    manual_review_reason: str | None = None

    recommendations: list[str] = Field(
        default_factory=list,
    )


class LlmCriterionAssessment(BaseModel):
    """
    One AI criterion result.
    """

    criterion: str = Field(
        min_length=1,
    )

    passed: bool

    rationale: str = Field(
        min_length=1,
    )


class LlmImageAssessment(BaseModel):
    """
    Complete structured AI assessment for one image.
    """

    image_src: str = Field(
        min_length=1,
    )

    overall_label: ComplianceLabel

    criteria: list[LlmCriterionAssessment]

    explanation: str = Field(
        min_length=1,
    )

    manual_review_required: bool = False

    manual_review_reason: str | None = None


class ImageAnalysisResult(BaseModel):
    """
    Evidence and two independent assessments for one image.
    """

    image_src: str = Field(
        min_length=1,
    )

    evidence: AttributionEvidence

    rule_based_result: ImageAssessment
    ai_result: LlmImageAssessment


class ComplianceReport(BaseModel):
    """
    Complete assessment report.
    """

    overall_rule_score: int = Field(
        ge=0,
        le=100,
    )

    total_images: int = Field(
        ge=0,
    )

    rule_fully_compliant: int = Field(
        ge=0,
    )

    rule_partially_compliant: int = Field(
        ge=0,
    )

    rule_non_compliant: int = Field(
        ge=0,
    )

    ai_fully_compliant: int = Field(
        ge=0,
    )

    ai_partially_compliant: int = Field(
        ge=0,
    )

    ai_non_compliant: int = Field(
        ge=0,
    )

    manual_review_recommended: bool = False

    manual_review_count: int = Field(
        default=0,
        ge=0,
    )

    summary: str = Field(
        min_length=1,
    )

    analysed_html: str | None = None

    image_results: list[ImageAnalysisResult] = Field(
        default_factory=list,
    )