from app.models.schemas import (
    AttributionEvidence,
    ComplianceReport,
    ImageAnalysisResult,
    ImageAssessment,
    LlmImageAssessment,
)


def _calculate_overall_rule_score(
    assessments: list[ImageAssessment],
) -> int:
    """
    Calculate average deterministic percentage.
    """

    if not assessments:
        return 0

    return round(
        sum(
            assessment.total_score
            for assessment in assessments
        )
        / len(assessments)
    )


def _build_summary(
    total_images: int,
    overall_rule_score: int,
    manual_review_count: int,
) -> str:
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

    review_word = (
        "image"
        if manual_review_count == 1
        else "images"
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
        f"{manual_review_count} {review_word} "
        f"{review_verb} manual review."
    )


def _validate_lengths(
    evidence_items: list[AttributionEvidence],
    rule_assessments: list[ImageAssessment],
    ai_assessments: list[LlmImageAssessment],
) -> None:
    if not (
        len(evidence_items)
        == len(rule_assessments)
        == len(ai_assessments)
    ):
        raise ValueError(
            "The evidence, rule-based assessment, and AI "
            "assessment lists contain different numbers of images."
        )


def _validate_alignment(
    evidence: AttributionEvidence,
    rule_result: ImageAssessment,
    ai_result: LlmImageAssessment,
) -> None:
    if not (
        evidence.image.src
        == rule_result.image_src
        == ai_result.image_src
    ):
        raise ValueError(
            "The evidence, rule-based assessment, and AI "
            "assessment do not refer to the same image."
        )


def build_report(
    evidence_items: list[AttributionEvidence],
    rule_assessments: list[ImageAssessment],
    ai_assessments: list[LlmImageAssessment],
) -> ComplianceReport:
    """
    Build the final report while keeping deterministic and AI
    assessments independent.
    """

    _validate_lengths(
        evidence_items,
        rule_assessments,
        ai_assessments,
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

    for (
        evidence,
        rule_result,
        ai_result,
    ) in zip(
        evidence_items,
        rule_assessments,
        ai_assessments,
    ):
        _validate_alignment(
            evidence,
            rule_result,
            ai_result,
        )

        if (
            rule_result.manual_review_required
            or ai_result.manual_review_required
        ):
            manual_review_count += 1

        image_results.append(
            ImageAnalysisResult(
                image_src=rule_result.image_src,
                evidence=evidence,
                rule_based_result=rule_result,
                ai_result=ai_result,
            )
        )

    return ComplianceReport(
        overall_rule_score=overall_rule_score,

        total_images=total_images,

        rule_fully_compliant=sum(
            assessment.label
            == "Fully Compliant"
            for assessment in rule_assessments
        ),

        rule_partially_compliant=sum(
            assessment.label
            == "Partially Compliant"
            for assessment in rule_assessments
        ),

        rule_non_compliant=sum(
            assessment.label
            == "Non-Compliant"
            for assessment in rule_assessments
        ),

        ai_fully_compliant=sum(
            assessment.overall_label
            == "Fully Compliant"
            for assessment in ai_assessments
        ),

        ai_partially_compliant=sum(
            assessment.overall_label
            == "Partially Compliant"
            for assessment in ai_assessments
        ),

        ai_non_compliant=sum(
            assessment.overall_label
            == "Non-Compliant"
            for assessment in ai_assessments
        ),

        manual_review_recommended=(
            manual_review_count > 0
        ),

        manual_review_count=(
            manual_review_count
        ),

        summary=_build_summary(
            total_images=total_images,
            overall_rule_score=overall_rule_score,
            manual_review_count=manual_review_count,
        ),

        image_results=image_results,
    )