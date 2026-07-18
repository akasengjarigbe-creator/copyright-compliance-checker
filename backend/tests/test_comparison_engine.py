import pytest

from app.hybrid.comparison_engine import (
    compare_rule_and_ai_assessments,
)
from app.models.schemas import (
    CriterionResult,
    ImageAssessment,
    LlmCriterionAssessment,
    LlmImageAssessment,
)


def _rule_result(
    label: str = "Fully Compliant",
    passed: bool = True,
) -> ImageAssessment:
    return ImageAssessment(
        image_src="cat.jpg",
        total_score=100 if passed else 60,
        label=label,
        criteria=[
            CriterionResult(
                criterion=(
                    "Copyright owner identified"
                ),
                passed=passed,
                score=20 if passed else 0,
                weight=20,
                rationale="Rule result.",
            )
        ],
        recommendations=[],
    )


def _ai_result(
    label: str = "Fully Compliant",
    passed: bool = True,
    manual_review: bool = False,
) -> LlmImageAssessment:
    return LlmImageAssessment(
        image_src="cat.jpg",
        overall_label=label,
        criteria=[
            LlmCriterionAssessment(
                criterion=(
                    "Copyright owner identified"
                ),
                passed=passed,
                rationale="AI result.",
            )
        ],
        explanation=(
            "The AI assessed the evidence."
        ),
        manual_review_required=manual_review,
    )


def test_comparison_records_agreement():
    result = compare_rule_and_ai_assessments(
        _rule_result(),
        _ai_result(),
    )

    assert result.systems_agree is True

    assert (
        result.manual_review_recommended
        is False
    )

    assert result.criterion_disagreements == []


def test_comparison_records_label_disagreement():
    result = compare_rule_and_ai_assessments(
        _rule_result(
            label="Fully Compliant"
        ),
        _ai_result(
            label="Partially Compliant"
        ),
    )

    assert result.systems_agree is False

    assert (
        result.manual_review_recommended
        is True
    )


def test_comparison_records_criterion_disagreement():
    result = compare_rule_and_ai_assessments(
        _rule_result(
            label="Partially Compliant",
            passed=True,
        ),
        _ai_result(
            label="Partially Compliant",
            passed=False,
        ),
    )

    assert result.systems_agree is True

    assert len(
        result.criterion_disagreements
    ) == 1

    assert (
        result.manual_review_recommended
        is True
    )


def test_comparison_rejects_different_images():
    ai_result = _ai_result()
    ai_result.image_src = "dog.jpg"

    with pytest.raises(
        ValueError,
        match="different images",
    ):
        compare_rule_and_ai_assessments(
            _rule_result(),
            ai_result,
        )