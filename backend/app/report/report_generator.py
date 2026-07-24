from app.models.schemas import (
    ComplianceReport,
    ImageAnalysisResult,
    ImageAssessment,
    LlmImageAssessment,
)


def _calculate_overall_rule_score(
    assessments: list[ImageAssessment],
) -> int:
    """
    Calculate the average deterministic rule-based score.

    Returns zero when no image assessments are available.
    """

    if not assessments:
        return 0

    total_score = sum(
        assessment.total_score
        for assessment in assessments
    )

    return round(
        total_score / len(assessments)
    )


def _build_summary(
    total_images: int,
    overall_rule_score: int,
    manual_review_count: int,
) -> str:
    """
    Build a concise human-readable report summary.
    """

    if total_images == 0:
        return (
            "No images were found, so no copyright compliance "
            "assessment could be performed."
        )

    image_word = (
        "image"
        if total_images == 1
        else "images"
    )

    analysed_verb = (
        "was"
        if total_images == 1
        else "were"
    )

    review_verb = (
        "requires"
        if manual_review_count == 1
        else "require"
    )

    return (
        f"{total_images} {image_word} {analysed_verb} analysed. "
        f"The average rule-based compliance score was "
        f"{overall_rule_score}%. "
        f"{manual_review_count} "
        f"{'image' if manual_review_count == 1 else 'images'} "
        f"{review_verb} manual review."
    )


def build_report(
    rule_assessments: list[ImageAssessment],
    ai_assessments: list[LlmImageAssessment],
) -> ComplianceReport:
    """
    Build the final copyright compliance report.

    The report contains separate rule-based and AI assessments.
    It does not compare the two systems and does not generate
    a hybrid assessment.
    """

    if len(rule_assessments) != len(
        ai_assessments
    ):
        raise ValueError(
            "The rule-based and AI assessment lists contain "
            "different numbers of images."
        )

    total_images = len(
        rule_assessments
    )

    overall_rule_score = (
        _calculate_overall_rule_score(
            rule_assessments
        )
    )

    image_results: list[
        ImageAnalysisResult
    ] = []

    manual_review_count = 0

    for rule_result, ai_result in zip(
        rule_assessments,
        ai_assessments,
    ):
        if (
            rule_result.image_src
            != ai_result.image_src
        ):
            raise ValueError(
                "The rule-based and AI assessments do not "
                "refer to the same image."
            )

        manual_review_required = (
            rule_result.manual_review_required
            or ai_result.manual_review_required
        )

        if manual_review_required:
            manual_review_count += 1

        image_results.append(
            ImageAnalysisResult(
                image_src=rule_result.image_src,
                rule_based_result=rule_result,
                ai_result=ai_result,
            )
        )

    rule_fully_compliant = sum(
        assessment.label
        == "Fully Compliant"
        for assessment in rule_assessments
    )

    rule_partially_compliant = sum(
        assessment.label
        == "Partially Compliant"
        for assessment in rule_assessments
    )

    rule_non_compliant = sum(
        assessment.label
        == "Non-Compliant"
        for assessment in rule_assessments
    )

    ai_fully_compliant = sum(
        assessment.overall_label
        == "Fully Compliant"
        for assessment in ai_assessments
    )

    ai_partially_compliant = sum(
        assessment.overall_label
        == "Partially Compliant"
        for assessment in ai_assessments
    )

    ai_non_compliant = sum(
        assessment.overall_label
        == "Non-Compliant"
        for assessment in ai_assessments
    )

    summary = _build_summary(
        total_images=total_images,
        overall_rule_score=overall_rule_score,
        manual_review_count=manual_review_count,
    )

    return ComplianceReport(
        overall_rule_score=overall_rule_score,
        total_images=total_images,
        rule_fully_compliant=rule_fully_compliant,
        rule_partially_compliant=rule_partially_compliant,
        rule_non_compliant=rule_non_compliant,
        ai_fully_compliant=ai_fully_compliant,
        ai_partially_compliant=ai_partially_compliant,
        ai_non_compliant=ai_non_compliant,
        manual_review_recommended=(
            manual_review_count > 0
        ),
        manual_review_count=manual_review_count,
        summary=summary,
        image_results=image_results,
    )