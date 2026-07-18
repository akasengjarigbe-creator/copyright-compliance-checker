import re

from app.models.schemas import (
    ComparisonAssessment,
    ImageAssessment,
    LlmImageAssessment,
)


def _normalise_criterion_name(
    criterion: str,
) -> str:
    """
    Normalise criterion names before comparing them.

    This removes numbering such as:

        1. Copyright owner identified
        2) Licence identified

    It also normalises whitespace and letter case.
    """

    normalised = criterion.strip()

    normalised = re.sub(
        r"^\s*\d+\s*[\.\)\-:]\s*",
        "",
        normalised,
    )

    normalised = re.sub(
        r"\s+",
        " ",
        normalised,
    )

    return normalised.casefold()


def _display_criterion_name(
    criterion: str,
) -> str:
    """
    Return a clean criterion name for explanations.
    """

    cleaned = criterion.strip()

    cleaned = re.sub(
        r"^\s*\d+\s*[\.\)\-:]\s*",
        "",
        cleaned,
    )

    cleaned = re.sub(
        r"\s+",
        " ",
        cleaned,
    )

    return cleaned


def _find_criterion_disagreements(
    rule_assessment: ImageAssessment,
    ai_assessment: LlmImageAssessment,
) -> list[str]:
    """
    Compare criterion-level decisions from the rule engine
    and AI reasoner.

    Criterion names are normalised so harmless formatting
    differences do not create false disagreements.
    """

    rule_results = {
        _normalise_criterion_name(result.criterion): {
            "passed": result.passed,
            "display_name": _display_criterion_name(
                result.criterion
            ),
        }
        for result in rule_assessment.criteria
    }

    ai_results = {
        _normalise_criterion_name(result.criterion): {
            "passed": result.passed,
            "display_name": _display_criterion_name(
                result.criterion
            ),
        }
        for result in ai_assessment.criteria
    }

    disagreements: list[str] = []

    all_criteria = sorted(
        set(rule_results) | set(ai_results)
    )

    for criterion_key in all_criteria:
        rule_result = rule_results.get(
            criterion_key
        )

        ai_result = ai_results.get(
            criterion_key
        )

        if rule_result is None:
            disagreements.append(
                (
                    "The AI assessed "
                    f"'{ai_result['display_name']}', "
                    "but the rule-based engine did not "
                    "return this criterion."
                )
            )
            continue

        if ai_result is None:
            disagreements.append(
                (
                    "The rule-based engine assessed "
                    f"'{rule_result['display_name']}', "
                    "but the AI did not return this criterion."
                )
            )
            continue

        if (
            rule_result["passed"]
            != ai_result["passed"]
        ):
            rule_text = (
                "Pass"
                if rule_result["passed"]
                else "Fail"
            )

            ai_text = (
                "Pass"
                if ai_result["passed"]
                else "Fail"
            )

            disagreements.append(
                (
                    f"{rule_result['display_name']}: "
                    f"the rule-based result was {rule_text}, "
                    f"while the AI result was {ai_text}."
                )
            )

    return disagreements


def _build_comparison_explanation(
    rule_assessment: ImageAssessment,
    ai_assessment: LlmImageAssessment,
    systems_agree: bool,
    criterion_disagreements: list[str],
    manual_review_recommended: bool,
) -> str:
    """
    Build a neutral explanation comparing the two systems.
    """

    if (
        systems_agree
        and not criterion_disagreements
        and not ai_assessment.manual_review_required
    ):
        return (
            "The rule-based engine and AI assessment agree "
            f"that the image is {rule_assessment.label}. "
            f"The rule-based score is "
            f"{rule_assessment.total_score}%. "
            f"AI explanation: "
            f"{ai_assessment.explanation}"
        )

    explanation_parts = [
        (
            "The rule-based engine classified the image as "
            f"{rule_assessment.label} with a score of "
            f"{rule_assessment.total_score}%."
        ),
        (
            "The AI assessment classified the image as "
            f"{ai_assessment.overall_label}."
        ),
    ]

    if criterion_disagreements:
        disagreement_count = len(
            criterion_disagreements
        )

        criterion_word = (
            "criterion"
            if disagreement_count == 1
            else "criteria"
        )

        explanation_parts.append(
            (
                "The two systems disagreed on "
                f"{disagreement_count} compliance "
                f"{criterion_word}."
            )
        )

    if ai_assessment.manual_review_required:
        explanation_parts.append(
            (
                "The AI assessment independently "
                "requested manual review."
            )
        )

    if manual_review_recommended:
        explanation_parts.append(
            (
                "A human reviewer should examine the "
                "available evidence before relying on "
                "either result."
            )
        )

    explanation_parts.append(
        f"AI explanation: {ai_assessment.explanation}"
    )

    return " ".join(explanation_parts)


def compare_rule_and_ai_assessments(
    rule_assessment: ImageAssessment,
    ai_assessment: LlmImageAssessment,
) -> ComparisonAssessment:
    """
    Compare one rule-based result with one AI result.

    This preserves both original assessments and identifies
    genuine disagreements requiring human review.
    """

    if (
        rule_assessment.image_src
        != ai_assessment.image_src
    ):
        raise ValueError(
            (
                "The rule-based and AI assessments refer "
                "to different images."
            )
        )

    systems_agree = (
        rule_assessment.label
        == ai_assessment.overall_label
    )

    criterion_disagreements = (
        _find_criterion_disagreements(
            rule_assessment,
            ai_assessment,
        )
    )

    manual_review_recommended = (
        not systems_agree
        or bool(criterion_disagreements)
        or ai_assessment.manual_review_required
    )

    explanation = _build_comparison_explanation(
        rule_assessment=rule_assessment,
        ai_assessment=ai_assessment,
        systems_agree=systems_agree,
        criterion_disagreements=(
            criterion_disagreements
        ),
        manual_review_recommended=(
            manual_review_recommended
        ),
    )

    return ComparisonAssessment(
        image_src=rule_assessment.image_src,
        rule_assessment=rule_assessment.label,
        ai_assessment=(
            ai_assessment.overall_label
        ),
        systems_agree=systems_agree,
        manual_review_recommended=(
            manual_review_recommended
        ),
        criterion_disagreements=(
            criterion_disagreements
        ),
        explanation=explanation,
    )