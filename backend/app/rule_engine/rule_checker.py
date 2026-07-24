from app.models.schemas import (
    AttributionEvidence,
    CriterionResult,
    ImageAssessment,
)


SELF_AUTHORED_LICENCE = "Self-authored claim"

SELF_AUTHORED_MANUAL_REVIEW_REASON = (
    "The image is declared as self-authored. The attribution information "
    "is sufficient for the automated assessment, but the system cannot "
    "independently verify that the named person created the image or owns "
    "the copyright."
)


def _has_text(value: str | None) -> bool:
    """
    Return True when a value contains meaningful text.
    """

    return bool(
        value
        and value.strip()
    )


def _is_self_authored(
    evidence: AttributionEvidence,
) -> bool:
    """
    Return True when the extracted evidence contains the
    recognised self-authorship permission basis.
    """

    if not evidence.licence_name:
        return False

    return (
        evidence.licence_name.strip().casefold()
        == SELF_AUTHORED_LICENCE.casefold()
    )


def _criterion(
    name: str,
    passed: bool,
    weight: int,
    rationale: str,
) -> CriterionResult:
    """
    Create the result for one deterministic compliance criterion.
    """

    return CriterionResult(
        criterion=name,
        passed=passed,
        score=weight if passed else 0,
        weight=weight,
        rationale=rationale,
    )


def _format_missing_items(
    missing_items: list[str],
) -> str:
    """
    Convert a list of missing attribution items into a
    readable sentence fragment.
    """

    if not missing_items:
        return ""

    if len(missing_items) == 1:
        return missing_items[0]

    if len(missing_items) == 2:
        return (
            f"{missing_items[0]} and "
            f"{missing_items[1]}"
        )

    return (
        ", ".join(
            missing_items[:-1]
        )
        + f", and {missing_items[-1]}"
    )


def _build_recommendations(
    criteria: list[CriterionResult],
    is_self_authored: bool,
) -> list[str]:
    """
    Build corrective recommendations from failed criteria.

    Self-authored images also receive a verification recommendation,
    even when all four automated criteria pass.
    """

    recommendation_map = {
        "Copyright owner identified": (
            "Identify the image creator, photographer, author, "
            "or copyright holder."
        ),
        "Licence identified": (
            "State the image licence or provide a clear permission "
            "or ownership statement."
        ),
        "Licence URL provided": (
            "Add a direct link to the applicable licence terms."
        ),
        "Attribution completeness": (
            "Provide complete attribution containing the creator, "
            "licence or permission basis, and licence link where "
            "applicable."
        ),
    }

    recommendations: list[str] = []

    for criterion in criteria:
        if criterion.passed:
            continue

        recommendation = recommendation_map.get(
            criterion.criterion
        )

        if (
            recommendation
            and recommendation not in recommendations
        ):
            recommendations.append(
                recommendation
            )

    if is_self_authored:
        verification_recommendation = (
            "Manually verify the self-authorship claim and confirm "
            "that the named person created the image or owns its copyright."
        )

        if (
            verification_recommendation
            not in recommendations
        ):
            recommendations.append(
                verification_recommendation
            )

    return recommendations


def _determine_label(
    total_score: int,
    attribution_complete: bool,
) -> str:
    """
    Convert the deterministic score into a compliance label.

    Full compliance requires all four criteria to pass.
    """

    if (
        total_score == 100
        and attribution_complete
    ):
        return "Fully Compliant"

    if total_score > 0:
        return "Partially Compliant"

    return "Non-Compliant"


def _build_copyright_rationale(
    creator_identified: bool,
    possible_author: str | None,
    is_self_authored: bool,
) -> str:
    """
    Explain the copyright-owner criterion result.
    """

    if not creator_identified:
        return (
            "No clear image creator, photographer, author, "
            "or copyright owner was detected."
        )

    author = possible_author.strip() if possible_author else ""

    if is_self_authored:
        return (
            f"The image creator or copyright owner was identified as "
            f"'{author}' through a self-authorship claim. The identity "
            "is accepted for the automated assessment but should be "
            "manually verified."
        )

    return (
        f"The image creator or copyright owner was identified as "
        f"'{author}'."
    )


def _build_licence_rationale(
    licence_identified: bool,
    licence_name: str | None,
    is_self_authored: bool,
) -> str:
    """
    Explain the licence criterion result.
    """

    if is_self_authored:
        return (
            "A self-authorship claim was detected and is treated as "
            "the permission basis for using the image. The claim should "
            "be manually verified because the system cannot independently "
            "confirm ownership."
        )

    if licence_identified:
        licence = licence_name.strip() if licence_name else ""

        return (
            f"The licence or permission basis was identified as "
            f"'{licence}'."
        )

    return (
        "No licence name, permission statement, or ownership basis "
        "was detected."
    )


def _build_licence_url_rationale(
    licence_url_provided: bool,
    licence_url: str | None,
    is_self_authored: bool,
) -> str:
    """
    Explain the licence-URL criterion result.
    """

    if is_self_authored:
        return (
            "A separate licence URL is not applicable because the image "
            "is declared as self-authored. This criterion therefore passes, "
            "although the ownership claim still requires manual verification."
        )

    if licence_url_provided:
        url = licence_url.strip() if licence_url else ""

        return (
            f"A licence URL was detected: {url}"
        )

    return (
        "No direct URL to the applicable licence terms was detected."
    )


def _build_attribution_rationale(
    creator_identified: bool,
    licence_identified: bool,
    licence_url_satisfied: bool,
    is_self_authored: bool,
) -> str:
    """
    Explain whether the complete attribution requirement was met.
    """

    attribution_complete = (
        creator_identified
        and licence_identified
        and licence_url_satisfied
    )

    if attribution_complete:
        if is_self_authored:
            return (
                "The attribution identifies the creator and includes a "
                "self-authorship permission basis. A separate licence URL "
                "is not applicable. The attribution is complete for the "
                "automated assessment, but the ownership claim should be "
                "manually verified."
            )

        return (
            "The attribution contains the identified creator or copyright "
            "owner, the applicable licence or permission basis, and a "
            "licence URL."
        )

    missing_items: list[str] = []

    if not creator_identified:
        missing_items.append(
            "the copyright owner"
        )

    if not licence_identified:
        missing_items.append(
            "the licence or permission basis"
        )

    if not licence_url_satisfied:
        missing_items.append(
            "the licence URL"
        )

    formatted_missing_items = _format_missing_items(
        missing_items
    )

    return (
        "The attribution is incomplete because the system did not detect "
        f"{formatted_missing_items}."
    )


def assess_images(
    evidence_items: list[AttributionEvidence],
    intended_use: str = "educational coursework",
) -> list[ImageAssessment]:
    """
    Assess every image against the four required criteria:

    1. Copyright owner identified
    2. Licence identified
    3. Licence URL provided
    4. Attribution completeness

    Self-authored images may receive a Fully Compliant automated result
    when the creator and self-authorship claim are present. A separate
    licence URL is not required for such images. Manual review is still
    required because ownership cannot be independently verified.

    The intended_use parameter is retained for compatibility with the
    wider application. Usage restrictions are not assessed by this
    four-criterion rule engine.
    """

    _ = intended_use

    assessments: list[ImageAssessment] = []

    for evidence in evidence_items:
        is_self_authored = _is_self_authored(
            evidence
        )

        creator_identified = _has_text(
            evidence.possible_author
        )

        licence_identified = _has_text(
            evidence.licence_name
        )

        licence_url_provided = _has_text(
            evidence.licence_url
        )

        licence_url_satisfied = (
            licence_url_provided
            or is_self_authored
        )

        attribution_complete = (
            creator_identified
            and licence_identified
            and licence_url_satisfied
        )

        criteria = [
            _criterion(
                name="Copyright owner identified",
                passed=creator_identified,
                weight=25,
                rationale=_build_copyright_rationale(
                    creator_identified=creator_identified,
                    possible_author=evidence.possible_author,
                    is_self_authored=is_self_authored,
                ),
            ),
            _criterion(
                name="Licence identified",
                passed=licence_identified,
                weight=25,
                rationale=_build_licence_rationale(
                    licence_identified=licence_identified,
                    licence_name=evidence.licence_name,
                    is_self_authored=is_self_authored,
                ),
            ),
            _criterion(
                name="Licence URL provided",
                passed=licence_url_satisfied,
                weight=25,
                rationale=_build_licence_url_rationale(
                    licence_url_provided=licence_url_provided,
                    licence_url=evidence.licence_url,
                    is_self_authored=is_self_authored,
                ),
            ),
            _criterion(
                name="Attribution completeness",
                passed=attribution_complete,
                weight=25,
                rationale=_build_attribution_rationale(
                    creator_identified=creator_identified,
                    licence_identified=licence_identified,
                    licence_url_satisfied=licence_url_satisfied,
                    is_self_authored=is_self_authored,
                ),
            ),
        ]

        total_score = sum(
            criterion.score
            for criterion in criteria
        )

        label = _determine_label(
            total_score=total_score,
            attribution_complete=attribution_complete,
        )

        manual_review_required = (
            is_self_authored
        )

        manual_review_reason = (
            SELF_AUTHORED_MANUAL_REVIEW_REASON
            if manual_review_required
            else None
        )

        recommendations = _build_recommendations(
            criteria=criteria,
            is_self_authored=is_self_authored,
        )

        assessments.append(
            ImageAssessment(
                image_src=evidence.image.src,
                total_score=total_score,
                label=label,
                criteria=criteria,
                manual_review_required=manual_review_required,
                manual_review_reason=manual_review_reason,
                recommendations=recommendations,
            )
        )

    return assessments