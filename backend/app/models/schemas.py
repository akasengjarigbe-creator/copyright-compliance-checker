from typing import List, Literal, Optional

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

    html: str
    base_url: Optional[str] = None
    intended_use: str = "educational coursework"


class AnalyseUrlRequest(BaseModel):
    """
    Request body for analysing a webpage using its URL.
    """

    url: str
    intended_use: str = "educational coursework"


class ParsedHtml(BaseModel):
    """
    Stores parsed HTML, visible page text, and an optional
    base URL.
    """

    html: str
    text: str
    base_url: Optional[str] = None


class ImageRecord(BaseModel):
    """
    Stores information extracted from one image element.
    """

    src: str
    alt: Optional[str] = None
    title: Optional[str] = None


class AttributionEvidence(BaseModel):
    """
    Stores attribution and licence evidence associated
    with one image.
    """

    image: ImageRecord
    nearby_text: str = ""
    caption: Optional[str] = None
    licence_name: Optional[str] = None
    licence_url: Optional[str] = None
    possible_author: Optional[str] = None


class CriterionResult(BaseModel):
    """
    Stores one rule-based compliance criterion result.
    """

    criterion: str
    passed: bool
    score: int = Field(ge=0)
    weight: int = Field(ge=0)
    rationale: str


class ImageAssessment(BaseModel):
    """
    Stores the complete rule-based assessment for one image.
    """

    image_src: str

    total_score: int = Field(
        ge=0,
        le=100,
        description=(
            "Rule-based compliance score expressed "
            "as a percentage."
        ),
    )

    label: ComplianceLabel
    criteria: List[CriterionResult]

    recommendations: List[str] = Field(
        default_factory=list
    )


class LlmCriterionAssessment(BaseModel):
    """
    Stores the AI decision for one compliance criterion.
    """

    criterion: str
    passed: bool

    rationale: str = Field(
        min_length=1
    )


class LlmImageAssessment(BaseModel):
    """
    Stores the complete structured AI assessment
    for one image.
    """

    image_src: str
    overall_label: ComplianceLabel
    criteria: List[LlmCriterionAssessment]

    explanation: str = Field(
        min_length=1
    )

    manual_review_required: bool = False


class HybridImageAssessment(BaseModel):
    """
    Stores the combined rule-based and AI decision
    for one image.
    """

    image_src: str

    rule_score: int = Field(
        ge=0,
        le=100,
        description=(
            "Rule-based compliance score expressed "
            "as a percentage."
        ),
    )

    rule_assessment: ComplianceLabel
    ai_assessment: ComplianceLabel
    final_assessment: ComplianceLabel

    systems_agree: bool
    manual_review_required: bool

    criterion_disagreements: List[str] = Field(
        default_factory=list
    )

    explanation: str = Field(
        min_length=1
    )

    recommendations: List[str] = Field(
        default_factory=list
    )


class ComplianceReport(BaseModel):
    """
    Stores the overall rule-based compliance report.
    """

    overall_score: int = Field(
        ge=0,
        le=100,
        description=(
            "Overall rule-based compliance score "
            "expressed as a percentage."
        ),
    )

    total_images: int = Field(ge=0)
    fully_compliant: int = Field(ge=0)
    partially_compliant: int = Field(ge=0)
    non_compliant: int = Field(ge=0)

    image_assessments: List[ImageAssessment]


class HybridComplianceReport(BaseModel):
    """
    Stores the final combined report produced by the
    hybrid decision engine.

    The frontend will display user-friendly headings such as:

    - Overall Score
    - Overall Assessment
    - Images Analysed
    - Manual Review Required
    """

    overall_score: int = Field(
        ge=0,
        le=100,
        description=(
            "Average rule-based compliance score "
            "expressed as a percentage."
        ),
    )

    overall_assessment: ComplianceLabel

    total_images: int = Field(ge=0)
    fully_compliant: int = Field(ge=0)
    partially_compliant: int = Field(ge=0)
    non_compliant: int = Field(ge=0)

    manual_review_required: bool
    manual_review_count: int = Field(ge=0)

    systems_agree_count: int = Field(ge=0)
    systems_disagree_count: int = Field(ge=0)

    summary: str = Field(
        min_length=1
    )

    image_assessments: List[HybridImageAssessment]

class ComparisonAssessment(BaseModel):
    """
    Compares the rule-based and AI assessments without
    automatically replacing them with one final decision.
    """

    image_src: str

    rule_assessment: ComplianceLabel
    ai_assessment: ComplianceLabel

    systems_agree: bool
    manual_review_recommended: bool

    criterion_disagreements: List[str] = Field(
        default_factory=list
    )

    explanation: str = Field(
        min_length=1
    )


class ThreeResultImageAssessment(BaseModel):
    """
    Presents the three separate results for one image:

    1. Rule-based assessment
    2. AI assessment
    3. Comparison assessment
    """

    image_src: str

    rule_based_result: ImageAssessment
    ai_result: LlmImageAssessment
    comparison_result: ComparisonAssessment


class ThreeResultComplianceReport(BaseModel):
    """
    Stores the complete three-result report for a webpage
    or ZIP submission.
    """

    overall_rule_score: int = Field(
        ge=0,
        le=100,
        description=(
            "Average deterministic rule-based score "
            "expressed as a percentage."
        ),
    )

    total_images: int = Field(ge=0)

    rule_fully_compliant: int = Field(ge=0)
    rule_partially_compliant: int = Field(ge=0)
    rule_non_compliant: int = Field(ge=0)

    ai_fully_compliant: int = Field(ge=0)
    ai_partially_compliant: int = Field(ge=0)
    ai_non_compliant: int = Field(ge=0)

    systems_agree_count: int = Field(ge=0)
    systems_disagree_count: int = Field(ge=0)

    manual_review_recommended: bool
    manual_review_count: int = Field(ge=0)

    summary: str = Field(
        min_length=1
    )

    image_results: List[ThreeResultImageAssessment]