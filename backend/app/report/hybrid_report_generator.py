from app.hybrid.hybrid_engine import (
    create_hybrid_assessment,
)
from app.models.schemas import (
    ComplianceLabel,
    HybridComplianceReport,
    HybridImageAssessment,
    ImageAssessment,
    LlmImageAssessment,
)


def _calculate_overall_score(
    assessments: list[HybridImageAssessment],
) -> int:
    """
    Calculate the average rule-based percentage.

    The hybrid system retains the deterministic rule score
    rather than inventing a separate AI-generated percentage.
    """

    if not assessments:
        return 0

    total_score = sum(
        assessment.rule_score
        for assessment in assessments
    )

    return round(
        total_score / len(assessments)
    )


def _select_overall_assessment(
    assessments: list[HybridImageAssessment],
) -> ComplianceLabel:
    """
    Select a conservative overall assessment.

    Rules:
        - If any image is Non-Compliant, the overall result
          is Non-Compliant.
        - Otherwise, if any image is Partially Compliant,
          the overall result is Partially Compliant.
        - Otherwise, all images are Fully Compliant.
    """

    final_labels = {
        assessment.final_assessment
        for assessment in assessments
    }

    if "Non-Compliant" in final_labels:
        return "Non-Compliant"

    if "Partially Compliant" in final_labels:
        return "Partially Compliant"

    return "Fully Compliant"


def _build_summary(
    overall_score: int,
    overall_assessment: ComplianceLabel,
    total_images: int,
    manual_review_count: int,
    systems_disagree_count: int,
) -> str:
    """
    Build a concise user-facing summary.
    """

    image_word = (
        "image"
        if total_images == 1
        else "images"
    )

    review_text = (
        (
            f"{manual_review_count} {image_word} "
            "requires manual review."
        )
        if manual_review_count > 0
        else "No manual review is currently required."
    )

    disagreement_text = (
        (
            f"The rule-based and AI systems disagreed "
            f"on {systems_disagree_count} {image_word}."
        )
        if systems_disagree_count > 0
        else (
            "The rule-based and AI systems agreed "
            "on all image-level classifications."
        )
    )

    return (
        f"The overall assessment is {overall_assessment}, "
        f"with an average rule-based score of "
        f"{overall_score}% across {total_images} {image_word}. "
        f"{review_text} {disagreement_text}"
    )


def build_hybrid_report(
    rule_assessments: list[ImageAssessment],
    llm_assessments: list[LlmImageAssessment],
) -> HybridComplianceReport:
    """
    Combine rule-based and AI assessments into one final report.

    Args:
        rule_assessments:
            Rule-based assessments for the detected images.

        llm_assessments:
            AI assessments for the same detected images.

    Returns:
        A complete HybridComplianceReport.

    Raises:
        ValueError:
            If the assessment lists contain different numbers
            of images, are empty, contain duplicate image sources,
            or do not refer to the same images.
    """

    if not rule_assessments:
        raise ValueError(
            "At least one rule-based image assessment is required."
        )

    if len(rule_assessments) != len(
        llm_assessments
    ):
        raise ValueError(
            (
                "The rule-based and AI assessment lists "
                "contain different numbers of images."
            )
        )

    llm_by_image = {
        assessment.image_src: assessment
        for assessment in llm_assessments
    }

    if len(llm_by_image) != len(
        llm_assessments
    ):
        raise ValueError(
            "Duplicate image sources were found in the AI assessments."
        )

    hybrid_assessments: list[
        HybridImageAssessment
    ] = []

    for rule_assessment in rule_assessments:
        llm_assessment = llm_by_image.get(
            rule_assessment.image_src
        )

        if llm_assessment is None:
            raise ValueError(
                (
                    "No matching AI assessment was found for "
                    f"the image: {rule_assessment.image_src}"
                )
            )

        hybrid_assessments.append(
            create_hybrid_assessment(
                rule_assessment=rule_assessment,
                llm_assessment=llm_assessment,
            )
        )

    overall_score = _calculate_overall_score(
        hybrid_assessments
    )

    overall_assessment = (
        _select_overall_assessment(
            hybrid_assessments
        )
    )

    fully_compliant = sum(
        assessment.final_assessment
        == "Fully Compliant"
        for assessment in hybrid_assessments
    )

    partially_compliant = sum(
        assessment.final_assessment
        == "Partially Compliant"
        for assessment in hybrid_assessments
    )

    non_compliant = sum(
        assessment.final_assessment
        == "Non-Compliant"
        for assessment in hybrid_assessments
    )

    manual_review_count = sum(
        assessment.manual_review_required
        for assessment in hybrid_assessments
    )

    systems_agree_count = sum(
        assessment.systems_agree
        for assessment in hybrid_assessments
    )

    systems_disagree_count = (
        len(hybrid_assessments)
        - systems_agree_count
    )

    summary = _build_summary(
        overall_score=overall_score,
        overall_assessment=overall_assessment,
        total_images=len(hybrid_assessments),
        manual_review_count=manual_review_count,
        systems_disagree_count=(
            systems_disagree_count
        ),
    )

    return HybridComplianceReport(
        overall_score=overall_score,
        overall_assessment=(
            overall_assessment
        ),
        total_images=len(
            hybrid_assessments
        ),
        fully_compliant=fully_compliant,
        partially_compliant=(
            partially_compliant
        ),
        non_compliant=non_compliant,
        manual_review_required=(
            manual_review_count > 0
        ),
        manual_review_count=(
            manual_review_count
        ),
        systems_agree_count=(
            systems_agree_count
        ),
        systems_disagree_count=(
            systems_disagree_count
        ),
        summary=summary,
        image_assessments=(
            hybrid_assessments
        ),
    )