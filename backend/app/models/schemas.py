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
            "and licence links."
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
    Request body for analysing a webpage using its URL.
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
    Store parsed HTML, visible page text, and an optional base URL.
    """

    html: str
    text: str
    base_url: str | None = None


class ImageRecord(BaseModel):
    """
    Store information extracted from one HTML image element.
    """

    src: str = Field(
        min_length=1,
        description="The image source path or URL.",
    )

    alt: str | None = None
    title: str | None = None


class AttributionEvidence(BaseModel):
    """
    Store attribution and licence evidence associated with one image.
    """

    image: ImageRecord

    nearby_text: str = ""
    caption: str | None = None

    possible_author: str | None = None
    licence_name: str | None = None
    licence_url: str | None = None


class CriterionResult(BaseModel):
    """
    Store one deterministic rule-based criterion result.
    """

    criterion: str = Field(
        min_length=1,
    )

    passed: bool

    score: int = Field(
        ge=0,
        description="Points awarded for this criterion.",
    )

    weight: int = Field(
        ge=0,
        description="Maximum points available for this criterion.",
    )

    rationale: str = Field(
        min_length=1,
        description=(
            "Explanation of why the criterion passed or failed."
        ),
    )


class ImageAssessment(BaseModel):
    """
    Store the complete deterministic rule-based assessment
    for one image.
    """

    image_src: str = Field(
        min_length=1,
    )

    total_score: int = Field(
        ge=0,
        le=100,
        description=(
            "Rule-based compliance score expressed as a percentage."
        ),
    )

    label: ComplianceLabel

    criteria: list[CriterionResult] = Field(
        description=(
            "Results for the four required copyright criteria."
        ),
    )

    manual_review_required: bool = False

    manual_review_reason: str | None = Field(
        default=None,
        description=(
            "A clear explanation of why human review is required. "
            "This should be null when manual review is not required."
        ),
    )

    recommendations: list[str] = Field(
        default_factory=list,
    )


class LlmCriterionAssessment(BaseModel):
    """
    Store the AI assessment for one compliance criterion.
    """

    criterion: str = Field(
        min_length=1,
    )

    passed: bool

    rationale: str = Field(
        min_length=1,
        description=(
            "The AI explanation for why the criterion passed or failed."
        ),
    )


class LlmImageAssessment(BaseModel):
    """
    Store the complete structured AI assessment for one image.
    """

    image_src: str = Field(
        min_length=1,
    )

    overall_label: ComplianceLabel

    criteria: list[LlmCriterionAssessment] = Field(
        description=(
            "AI results for the four required copyright criteria."
        ),
    )

    explanation: str = Field(
        min_length=1,
        description=(
            "A concise explanation of the AI's overall classification."
        ),
    )

    manual_review_required: bool = False

    manual_review_reason: str | None = Field(
        default=None,
        description=(
            "A specific explanation of why the AI recommends human "
            "review. This should be null when review is not required."
        ),
    )


class ImageAnalysisResult(BaseModel):
    """
    Store the two separate assessments produced for one image.

    The rule-based result and AI result remain independent.
    No automated comparison or hybrid result is produced.
    """

    image_src: str = Field(
        min_length=1,
    )

    rule_based_result: ImageAssessment
    ai_result: LlmImageAssessment


class ComplianceReport(BaseModel):
    """
    Store the complete report for a webpage or ZIP submission.

    The report presents deterministic and AI assessments separately.
    It does not contain comparison-engine output, agreement counts,
    disagreement counts, or a hybrid final assessment.
    """

    overall_rule_score: int = Field(
        ge=0,
        le=100,
        description=(
            "Average deterministic rule-based score expressed "
            "as a percentage."
        ),
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
        description=(
            "Number of images for which either assessment recommends "
            "manual review."
        ),
    )

    summary: str = Field(
        min_length=1,
    )

    image_results: list[ImageAnalysisResult] = Field(
        default_factory=list,
    )