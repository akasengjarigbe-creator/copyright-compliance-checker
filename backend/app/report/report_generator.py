from app.models.schemas import (
    ComplianceReport,
    ImageAssessment,
)


def build_report(
    assessments: list[ImageAssessment],
) -> ComplianceReport:
    """
    Build an overall rule-based compliance report
    from individual image assessments.
    """

    total_images = len(assessments)

    if total_images == 0:
        overall_score = 0
    else:
        overall_score = round(
            sum(
                assessment.total_score
                for assessment in assessments
            )
            / total_images
        )

    fully_compliant = sum(
        assessment.label == "Fully Compliant"
        for assessment in assessments
    )

    partially_compliant = sum(
        assessment.label == "Partially Compliant"
        for assessment in assessments
    )

    non_compliant = sum(
        assessment.label == "Non-Compliant"
        for assessment in assessments
    )

    return ComplianceReport(
        overall_score=overall_score,
        total_images=total_images,
        fully_compliant=fully_compliant,
        partially_compliant=partially_compliant,
        non_compliant=non_compliant,
        image_assessments=assessments,
    )