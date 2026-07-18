from app.knowledgebase.licence_loader import get_licence_rules
from app.models.schemas import (
    AttributionEvidence,
    CriterionResult,
    ImageAssessment,
)


def _criterion(
    name: str,
    passed: bool,
    weight: int,
    rationale: str
) -> CriterionResult:
    """
    Create a result for one compliance criterion.

    A criterion receives its full weight when it passes
    and zero points when it fails.
    """
    return CriterionResult(
        criterion=name,
        passed=passed,
        score=weight if passed else 0,
        weight=weight,
        rationale=rationale,
    )


def _check_usage_compatibility(
    licence_name: str | None,
    intended_use: str
) -> tuple[bool, bool, str]:
    """
    Compare the intended image use with the detected licence rules.

    Returns:
        usage_passed:
            True when the intended use is compatible.

        confirmed_conflict:
            True only when a supported licence directly conflicts
            with the intended use.

        rationale:
            A human-readable explanation of the result.
    """

    if not licence_name:
        return (
            False,
            False,
            "Cannot check usage limits because no licence was identified."
        )

    rules = get_licence_rules(licence_name)

    if rules is None:
        return (
            False,
            False,
            (
                f"The licence '{licence_name}' is not currently supported "
                "by the licence knowledge base."
            )
        )

    use = intended_use.lower()

    is_non_commercial = (
        "non-commercial" in use
        or "noncommercial" in use
    )

    is_commercial = (
        "commercial" in use
        and not is_non_commercial
    )

    is_modified = any(
        word in use
        for word in [
            "modified",
            "modify",
            "adapted",
            "adapt",
            "cropped",
            "crop",
            "edited",
            "edit",
            "remixed",
            "remix",
            "derivative",
        ]
    )

    is_shared = any(
        word in use
        for word in [
            "distributed",
            "shared",
            "published",
            "redistributed",
            "released",
        ]
    )

    share_alike_missing = any(
        phrase in use
        for phrase in [
            "without a sharealike licence",
            "without sharealike",
            "not under sharealike",
            "not licensed under sharealike",
            "without a compatible licence",
        ]
    )

    if is_commercial and not rules["commercial_use"]:
        return (
            False,
            True,
            (
                f"The detected {licence_name} licence does not permit "
                "the declared commercial use."
            )
        )

    if is_modified and not rules["modification"]:
        return (
            False,
            True,
            (
                f"The detected {licence_name} licence does not permit "
                "modified or adapted versions to be shared."
            )
        )

    if (
        rules["requires_share_alike"]
        and is_modified
        and is_shared
        and share_alike_missing
    ):
        return (
            False,
            True,
            (
                f"The detected {licence_name} licence requires the modified "
                "work to be shared under the same or a compatible "
                "ShareAlike licence."
            )
        )

    return (
        True,
        False,
        (
            "The declared use does not conflict with the detected "
            "licence restrictions."
        )
    )


def _build_recommendations(
    criteria: list[CriterionResult]
) -> list[str]:
    """
    Convert failed criteria into specific corrective recommendations.
    """

    recommendation_map = {
        "Copyright owner identified": (
            "Identify the image creator, photographer, author, "
            "or copyright holder."
        ),
        "Licence identified": (
            "State the licence name or provide a clear permission "
            "statement for the image."
        ),
        "Licence URL provided": (
            "Add a direct link to the licence terms or the relevant "
            "source permission page."
        ),
        "Attribution completeness": (
            "Provide a complete attribution containing the creator "
            "and the applicable licence."
        ),
        "Licence conditions understood": (
            "Explain why the licence permits the intended use of "
            "the image."
        ),
    }

    recommendations: list[str] = []

    for criterion in criteria:
        if criterion.passed:
            continue

        if criterion.criterion == "Usage limits checked":
            recommendations.append(criterion.rationale)
            continue

        recommendation = recommendation_map.get(
            criterion.criterion,
            f"Review and correct: {criterion.criterion}."
        )

        recommendations.append(recommendation)

    return recommendations


def assess_images(
    evidence_items: list[AttributionEvidence],
    intended_use: str = "educational coursework"
) -> list[ImageAssessment]:
    """
    Assess every image against the six compliance criteria.
    """

    assessments: list[ImageAssessment] = []

    for evidence in evidence_items:
        (
            usage_passed,
            confirmed_usage_conflict,
            usage_rationale,
        ) = _check_usage_compatibility(
            evidence.licence_name,
            intended_use
        )

        nearby_text_lower = evidence.nearby_text.lower()

        conditions_understood = (
            "permit" in nearby_text_lower
            or "allowed" in nearby_text_lower
            or "use" in nearby_text_lower
        )

        criteria = [
            _criterion(
                "Copyright owner identified",
                bool(evidence.possible_author),
                20,
                (
                    "Author or creator detected."
                    if evidence.possible_author
                    else "No clear author or rights holder was detected."
                )
            ),
            _criterion(
                "Licence identified",
                bool(evidence.licence_name),
                20,
                (
                    "Licence information detected."
                    if evidence.licence_name
                    else "No licence name or permission statement was detected."
                )
            ),
            _criterion(
                "Licence URL provided",
                bool(evidence.licence_url),
                15,
                (
                    "Licence or source URL detected."
                    if evidence.licence_url
                    else "No licence URL was detected."
                )
            ),
            _criterion(
                "Attribution completeness",
                bool(
                    evidence.possible_author
                    and evidence.licence_name
                ),
                15,
                (
                    "Attribution includes both creator and licence evidence."
                    if (
                        evidence.possible_author
                        and evidence.licence_name
                    )
                    else "The attribution is incomplete."
                )
            ),
            _criterion(
                "Licence conditions understood",
                conditions_understood,
                15,
                (
                    "An explanation of permitted use was detected."
                    if conditions_understood
                    else (
                        "No clear explanation of why the licence permits "
                        "the intended use was detected."
                    )
                )
            ),
            _criterion(
                "Usage limits checked",
                usage_passed,
                15,
                usage_rationale
            ),
        ]

        total = sum(
            criterion.score
            for criterion in criteria
        )

        if total >= 80 and not confirmed_usage_conflict:
            label = "Fully Compliant"
        elif total >= 50:
            label = "Partially Compliant"
        else:
            label = "Non-Compliant"

        recommendations = _build_recommendations(criteria)

        assessments.append(
            ImageAssessment(
                image_src=evidence.image.src,
                total_score=total,
                label=label,
                criteria=criteria,
                recommendations=recommendations,
            )
        )

    return assessments