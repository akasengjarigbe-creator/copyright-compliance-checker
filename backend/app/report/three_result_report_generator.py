from app.hybrid.comparison_engine import (
    compare_rule_and_ai_assessments,
)
from app.models.schemas import (
    ImageAssessment,
    LlmImageAssessment,
    ThreeResultComplianceReport,
    ThreeResultImageAssessment,
)


def _calculate_rule_score(
    assessments: list[ImageAssessment],
) -> int:
    """
    Calculate the average deterministic rule-based score.
    """

    if not assessments:
        return 0

    total = sum(
        assessment.total_score
        for assessment in assessments
    )

    return round(total / len(assessments))


def _build_summary(
    total_images: int,
    overall_rule_score: int,
    systems_disagree_count: int,
    manual_review_count: int,
) -> str:
    """
    Build a concise summary suitable for the frontend.
    """

    if total_images == 0:
        return (
            "No analysable images were detected in the submitted content."
        )

    image_word = (
        "image"
        if total_images == 1
        else "images"
    )

    if systems_disagree_count == 0:
        agreement_text = (
            "The rule-based and AI assessments agreed "
            "on all image-level classifications."
        )
    else:
        agreement_text = (
            "The two assessment methods disagreed on "
            f"{systems_disagree_count} {image_word}."
        )

    if manual_review_count == 0:
        review_text = (
            "No manual review is currently recommended."
        )
    else:
        review_text = (
            "Manual review is recommended for "
            f"{manual_review_count} {image_word}."
        )

    return (
        f"{total_images} {image_word} were analysed. "
        f"The average rule-based score was "
        f"{overall_rule_score}%. "
        f"{agreement_text} {review_text}"
    )


def build_three_result_report(
    rule_assessments: list[ImageAssessment],
    ai_assessments: list[LlmImageAssessment],
) -> ThreeResultComplianceReport:
    """
    Build a report containing three separate outputs:

    1. Rule-based result
    2. AI result
    3. Comparison result

    The function does not produce a replacement final
    compliance classification.
    """

    if len(rule_assessments) != len(
        ai_assessments
    ):
        raise ValueError(
            (
                "The rule-based and AI assessment lists "
                "contain different numbers of images."
            )
        )

    image_results: list[
        ThreeResultImageAssessment
    ] = []

    for rule_assessment, ai_assessment in zip(
        rule_assessments,
        ai_assessments,
    ):
        if (
            rule_assessment.image_src
            != ai_assessment.image_src
        ):
            raise ValueError(
                (
                    "The rule-based and AI assessments "
                    "do not refer to the same image."
                )
            )

        comparison = (
            compare_rule_and_ai_assessments(
                rule_assessment,
                ai_assessment,
            )
        )

        image_results.append(
            ThreeResultImageAssessment(
                image_src=(
                    rule_assessment.image_src
                ),
                rule_based_result=(
                    rule_assessment
                ),
                ai_result=ai_assessment,
                comparison_result=comparison,
            )
        )

    overall_rule_score = (
        _calculate_rule_score(
            rule_assessments
        )
    )

    rule_fully_compliant = sum(
        item.label == "Fully Compliant"
        for item in rule_assessments
    )

    rule_partially_compliant = sum(
        item.label == "Partially Compliant"
        for item in rule_assessments
    )

    rule_non_compliant = sum(
        item.label == "Non-Compliant"
        for item in rule_assessments
    )

    ai_fully_compliant = sum(
        item.overall_label == "Fully Compliant"
        for item in ai_assessments
    )

    ai_partially_compliant = sum(
        item.overall_label
        == "Partially Compliant"
        for item in ai_assessments
    )

    ai_non_compliant = sum(
        item.overall_label == "Non-Compliant"
        for item in ai_assessments
    )

    systems_agree_count = sum(
        result.comparison_result.systems_agree
        for result in image_results
    )

    systems_disagree_count = (
        len(image_results)
        - systems_agree_count
    )

    manual_review_count = sum(
        result.comparison_result
        .manual_review_recommended
        for result in image_results
    )

    summary = _build_summary(
        total_images=len(image_results),
        overall_rule_score=(
            overall_rule_score
        ),
        systems_disagree_count=(
            systems_disagree_count
        ),
        manual_review_count=(
            manual_review_count
        ),
        
    )

    return ThreeResultComplianceReport(
        overall_rule_score=(
            overall_rule_score
        ),
        total_images=len(image_results),
        rule_fully_compliant=(
            rule_fully_compliant
        ),
        rule_partially_compliant=(
            rule_partially_compliant
        ),
        rule_non_compliant=(
            rule_non_compliant
        ),
        ai_fully_compliant=(
            ai_fully_compliant
        ),
        ai_partially_compliant=(
            ai_partially_compliant
        ),
        ai_non_compliant=(
            ai_non_compliant
        ),
        systems_agree_count=(
            systems_agree_count
        ),
        systems_disagree_count=(
            systems_disagree_count
        ),
        manual_review_recommended=(
            manual_review_count > 0
        ),
        manual_review_count=(
            manual_review_count
        ),
        summary=summary,
        image_results=image_results,
    )