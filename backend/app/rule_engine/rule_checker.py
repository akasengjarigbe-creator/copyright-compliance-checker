import re

from app.knowledgebase.licence_loader import (
    get_licence_rules,
)
from app.models.schemas import (
    AttributionEvidence,
    CriterionResult,
    ImageAssessment,
)


SELF_AUTHORED_LICENCE = "Self-authored claim"


def _criterion(
    name: str,
    passed: bool,
    weight: int,
    rationale: str,
) -> CriterionResult:
    """
    Create a result for one compliance criterion.
    """

    return CriterionResult(
        criterion=name,
        passed=passed,
        score=weight if passed else 0,
        weight=weight,
        rationale=rationale,
    )


def _normalise_text(
    text: str,
) -> str:
    return re.sub(
        r"\s+",
        " ",
        text.casefold(),
    ).strip()


def _conditions_are_explained(
    nearby_text: str,
    licence_name: str | None,
) -> bool:
    """
    Detect a genuine explanation of permission or conditions.

    A generic occurrence of the word 'use' is not sufficient.
    """

    if licence_name == SELF_AUTHORED_LICENCE:
        return True

    text = _normalise_text(
        nearby_text
    )

    permission_phrases = [
        "permits",
        "permit",
        "is permitted",
        "is allowed",
        "may be used",
        "can be used",
        "reuse is allowed",
        "free to use",
        "with attribution",
        "under the terms",
        "subject to the licence",
    ]

    return any(
        phrase in text
        for phrase in permission_phrases
    )


def _check_usage_compatibility(
    licence_name: str | None,
    intended_use: str,
) -> tuple[bool, bool, str]:
    """
    Compare intended use with detected licence rules.
    """

    if not licence_name:
        return (
            False,
            False,
            "Cannot check usage limits because no licence was identified.",
        )

    rules = get_licence_rules(
        licence_name
    )

    if rules is None:
        return (
            False,
            False,
            (
                f"The licence '{licence_name}' is not currently "
                "supported by the licence knowledge base."
            ),
        )

    use = intended_use.casefold()

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

    if (
        is_commercial
        and not rules.get(
            "commercial_use",
            False,
        )
    ):
        return (
            False,
            True,
            (
                f"The detected {licence_name} licence does not "
                "permit the declared commercial use."
            ),
        )

    if (
        is_modified
        and not rules.get(
            "modification",
            False,
        )
    ):
        return (
            False,
            True,
            (
                f"The detected {licence_name} licence does not "
                "permit modified or adapted versions to be shared."
            ),
        )

    if (
        rules.get(
            "requires_share_alike",
            False,
        )
        and is_modified
        and is_shared
        and share_alike_missing
    ):
        return (
            False,
            True,
            (
                f"The detected {licence_name} licence requires "
                "the modified work to be shared under the same "
                "or a compatible ShareAlike licence."
            ),
        )

    if licence_name == SELF_AUTHORED_LICENCE:
        return (
            True,
            False,
            (
                "The page contains a self-authorship claim. "
                "The declared use does not conflict with that claim, "
                "although ownership may require independent verification."
            ),
        )

    return (
        True,
        False,
        (
            "The declared use does not conflict with the detected "
            "licence restrictions."
        ),
    )


def _build_recommendations(
    criteria: list[CriterionResult],
) -> list[str]:
    """
    Convert failed criteria into corrective recommendations.
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
            "Explain why the licence permits the intended use "
            "of the image."
        ),
    }

    recommendations: list[str] = []

    for criterion in criteria:
        if criterion.passed:
            continue

        if criterion.criterion == "Usage limits checked":
            recommendations.append(
                criterion.rationale
            )
            continue

        recommendations.append(
            recommendation_map.get(
                criterion.criterion,
                (
                    "Review and correct: "
                    f"{criterion.criterion}."
                ),
            )
        )

    return recommendations


def assess_images(
    evidence_items: list[AttributionEvidence],
    intended_use: str = "educational coursework",
) -> list[ImageAssessment]:
    """
    Assess every image against six compliance criteria.
    """

    assessments: list[ImageAssessment] = []

    for evidence in evidence_items:
        is_self_authored = (
            evidence.licence_name
            == SELF_AUTHORED_LICENCE
        )

        (
            usage_passed,
            confirmed_usage_conflict,
            usage_rationale,
        ) = _check_usage_compatibility(
            evidence.licence_name,
            intended_use,
        )

        conditions_understood = (
            _conditions_are_explained(
                evidence.nearby_text,
                evidence.licence_name,
            )
        )

        creator_identified = bool(
            evidence.possible_author
        )

        permission_basis_identified = bool(
            evidence.licence_name
        )

        licence_url_satisfied = bool(
            evidence.licence_url
        ) or is_self_authored

        attribution_complete = (
            creator_identified
            and permission_basis_identified
        )

        criteria = [
            _criterion(
                "Copyright owner identified",
                creator_identified,
                20,
                (
                    "Author or creator detected."
                    if creator_identified
                    else (
                        "No clear author or rights holder "
                        "was detected."
                    )
                ),
            ),
            _criterion(
                "Licence identified",
                permission_basis_identified,
                20,
                (
                    (
                        "A self-authorship claim was detected. "
                        "A third-party licence is not required "
                        "when the claim is genuine."
                    )
                    if is_self_authored
                    else (
                        "Licence information detected."
                        if permission_basis_identified
                        else (
                            "No licence name or permission "
                            "statement was detected."
                        )
                    )
                ),
            ),
            _criterion(
                "Licence URL provided",
                licence_url_satisfied,
                15,
                (
                    (
                        "A licence URL is not applicable to the "
                        "declared self-authored image."
                    )
                    if is_self_authored
                    else (
                        "Licence URL detected."
                        if evidence.licence_url
                        else "No licence URL was detected."
                    )
                ),
            ),
            _criterion(
                "Attribution completeness",
                attribution_complete,
                15,
                (
                    "Attribution includes both creator and "
                    "licence or permission evidence."
                    if attribution_complete
                    else "The attribution is incomplete."
                ),
            ),
            _criterion(
                "Licence conditions understood",
                conditions_understood,
                15,
                (
                    (
                        "The image is declared as self-authored, "
                        "so third-party licence conditions are "
                        "not applicable."
                    )
                    if is_self_authored
                    else (
                        "An explanation of permitted use was detected."
                        if conditions_understood
                        else (
                            "No clear explanation of why the licence "
                            "permits the intended use was detected."
                        )
                    )
                ),
            ),
            _criterion(
                "Usage limits checked",
                usage_passed,
                15,
                usage_rationale,
            ),
        ]

        total = sum(
            criterion.score
            for criterion in criteria
        )

        if (
            total >= 80
            and not confirmed_usage_conflict
        ):
            label = "Fully Compliant"
        elif total >= 50:
            label = "Partially Compliant"
        else:
            label = "Non-Compliant"

        assessments.append(
            ImageAssessment(
                image_src=evidence.image.src,
                total_score=total,
                label=label,
                criteria=criteria,
                recommendations=(
                    _build_recommendations(
                        criteria
                    )
                ),
            )
        )

    return assessments