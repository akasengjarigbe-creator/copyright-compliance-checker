from app.models.schemas import (
    CriterionResult,
    ImageAssessment,
    LlmCriterionAssessment,
    LlmImageAssessment,
)
from app.report.three_result_report_generator import (
    build_three_result_report,
)


def _rule_result(
    image_src: str,
    label: str,
    score: int,
) -> ImageAssessment:
    return ImageAssessment(
        image_src=image_src,
        total_score=score,
        label=label,
        criteria=[
            CriterionResult(
                criterion=(
                    "Copyright owner identified"
                ),
                passed=True,
                score=20,
                weight=20,
                rationale="Rule result.",
            )
        ],
        recommendations=[],
    )


def _ai_result(
    image_src: str,
    label: str,
) -> LlmImageAssessment:
    return LlmImageAssessment(
        image_src=image_src,
        overall_label=label,
        criteria=[
            LlmCriterionAssessment(
                criterion=(
                    "Copyright owner identified"
                ),
                passed=True,
                rationale="AI result.",
            )
        ],
        explanation=(
            "The AI assessed the evidence."
        ),
        manual_review_required=False,
    )


def test_three_result_report_preserves_all_results():
    report = build_three_result_report(
        rule_assessments=[
            _rule_result(
                "cat.jpg",
                "Fully Compliant",
                100,
            )
        ],
        ai_assessments=[
            _ai_result(
                "cat.jpg",
                "Fully Compliant",
            )
        ],
    )

    assert report.overall_rule_score == 100
    assert report.total_images == 1
    assert report.systems_agree_count == 1
    assert report.systems_disagree_count == 0

    image_result = report.image_results[0]

    assert (
        image_result.rule_based_result.label
        == "Fully Compliant"
    )

    assert (
        image_result.ai_result.overall_label
        == "Fully Compliant"
    )

    assert (
        image_result.comparison_result
        .systems_agree
        is True
    )


def test_three_result_report_records_disagreement():
    report = build_three_result_report(
        rule_assessments=[
            _rule_result(
                "cat.jpg",
                "Fully Compliant",
                100,
            )
        ],
        ai_assessments=[
            _ai_result(
                "cat.jpg",
                "Partially Compliant",
            )
        ],
    )

    assert report.systems_agree_count == 0
    assert report.systems_disagree_count == 1

    assert (
        report.manual_review_recommended
        is True
    )

    assert report.manual_review_count == 1


def test_three_result_report_calculates_average_rule_score():
    report = build_three_result_report(
        rule_assessments=[
            _rule_result(
                "cat.jpg",
                "Fully Compliant",
                100,
            ),
            _rule_result(
                "dog.jpg",
                "Partially Compliant",
                60,
            ),
        ],
        ai_assessments=[
            _ai_result(
                "cat.jpg",
                "Fully Compliant",
            ),
            _ai_result(
                "dog.jpg",
                "Partially Compliant",
            ),
        ],
    )

    assert report.overall_rule_score == 80
    assert report.total_images == 2

    assert report.rule_fully_compliant == 1

    assert (
        report.rule_partially_compliant
        == 1
    )

    assert report.ai_fully_compliant == 1

    assert (
        report.ai_partially_compliant
        == 1
    )