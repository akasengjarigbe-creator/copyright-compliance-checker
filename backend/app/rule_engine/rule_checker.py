import re

from app.models.schemas import (
    AttributionEvidence,
    CriterionResult,
    ImageAssessment,
)


SELF_AUTHORED_LICENCE = "Self-authored claim"


CRITERION_OWNER = (
    "Copyright owner identified"
)

CRITERION_LICENCE = (
    "Licence or permission identified"
)

CRITERION_TERMS = (
    "Licence terms location provided"
)


OWNER_WEIGHT = 34
LICENCE_WEIGHT = 33
TERMS_WEIGHT = 33


SELF_AUTHORED_MANUAL_REVIEW_REASON = (
    "The image is declared as self-authored. The automated "
    "assessment accepts the supplied claim, but the system "
    "cannot independently verify that the named person created "
    "the image or owns the copyright."
)


KNOWN_LICENCE_PATTERNS = [
    r"\bcc\s*by\s*1\.0\b",
    r"\bcc\s*by\s*2\.0\b",
    r"\bcc\s*by\s*2\.5\b",
    r"\bcc\s*by\s*3\.0\b",
    r"\bcc\s*by\s*4\.0\b",
    r"\bcc\s*by-sa\b",
    r"\bcc\s*by-nc\b",
    r"\bcc\s*by-nd\b",
    r"\bcc\s*by-nc-sa\b",
    r"\bcc\s*by-nc-nd\b",
    r"\bcc0\b",
    r"\bcreative commons\b",
    r"\bpexels\s+(?:license|licence)\b",
    r"\bunsplash\s+(?:license|licence)\b",
    r"\bpixabay(?:\s+content)?\s+(?:license|licence)\b",
    r"\bpublic domain\b",
    r"\bmit\s+license\b",
    r"\bapache\s+license\b",
    r"\bgnu\s+general\s+public\s+license\b",
    r"\bgpl\b",
    r"\blgpl\b",
    r"\bbsd\b",
    r"\bmozilla\s+public\s+license\b",
    r"\bopen\s+government\s+licen[cs]e\b",
    r"\bfree\s+art\s+licen[cs]e\b",
    r"\bartistic\s+licen[cs]e\b",
]


def _has_text(
    value: str | None,
) -> bool:
    return bool(
        value
        and value.strip()
    )


def _normalise(
    value: str | None,
) -> str:
    if not value:
        return ""

    return " ".join(
        value.casefold().split()
    )


def _is_self_authored(
    evidence: AttributionEvidence,
) -> bool:
    return (
        _normalise(
            evidence.licence_name
        )
        == _normalise(
            SELF_AUTHORED_LICENCE
        )
    )


def _is_known_licence(
    licence_name: str | None,
) -> bool:
    if not _has_text(
        licence_name
    ):
        return False

    return any(
        re.search(
            pattern,
            licence_name,
            flags=re.IGNORECASE,
        )
        is not None
        for pattern
        in KNOWN_LICENCE_PATTERNS
    )


def _criterion(
    name: str,
    passed: bool,
    weight: int,
    rationale: str,
) -> CriterionResult:
    return CriterionResult(
        criterion=name,
        passed=passed,
        score=(
            weight
            if passed
            else 0
        ),
        weight=weight,
        rationale=rationale,
    )


def _explicit_source_reference(
    evidence: AttributionEvidence,
) -> str | None:
    """
    Return explicit source attribution only.

    evidence.image.src is intentionally never used here.
    """

    if not (
        _has_text(
            evidence.source_evidence_source
        )
        or _has_text(
            evidence.source_evidence_text
        )
    ):
        return None

    if _has_text(
        evidence.source_url
    ):
        return (
            evidence.source_url.strip()
        )

    if _has_text(
        evidence.source_name
    ):
        return (
            evidence.source_name.strip()
        )

    if _has_text(
        evidence.source_evidence_text
    ):
        return (
            evidence.source_evidence_text.strip()
        )

    return None


def _owner_result(
    evidence: AttributionEvidence,
) -> tuple[
    bool,
    str,
]:
    if _has_text(
        evidence.possible_author
    ):
        author = (
            evidence.possible_author.strip()
        )

        rationale = (
            "The image creator or copyright holder was "
            f"identified as '{author}'."
        )

        if _has_text(
            evidence.author_evidence_source
        ):
            rationale += (
                " The information was found in the "
                f"{evidence.author_evidence_source.strip()}."
            )

        if _has_text(
            evidence.author_evidence_text
        ):
            rationale += (
                " Relevant evidence: "
                f"'{evidence.author_evidence_text.strip()}'."
            )

        return (
            True,
            rationale,
        )

    source_reference = (
        _explicit_source_reference(
            evidence
        )
    )

    if source_reference:
        rationale = (
            "No separate named image creator or copyright "
            "holder was detected. However, the student "
            f"explicitly supplied '{source_reference}' as "
            "the image source/reference. Under the coursework "
            "assessment policy, this explicit source reference "
            "is accepted as the student's copyright reference."
        )

        if _has_text(
            evidence.source_evidence_source
        ):
            rationale += (
                " The source information was found in the "
                f"{evidence.source_evidence_source.strip()}."
            )

        if _has_text(
            evidence.source_evidence_text
        ):
            rationale += (
                " Relevant source evidence: "
                f"'{evidence.source_evidence_text.strip()}'."
            )

        return (
            True,
            rationale,
        )

    return (
        False,
        (
            "No image creator or copyright holder was identified "
            "in the supplied webpage evidence, and no explicit "
            "source attribution was detected. The technical "
            "image URL is not treated as copyright attribution."
        ),
    )


def _licence_result(
    evidence: AttributionEvidence,
    is_self_authored: bool,
) -> tuple[
    bool,
    str,
    bool,
]:
    """
    Returns:
        passed,
        rationale,
        ambiguous_or_unknown
    """

    if is_self_authored:
        rationale = (
            "The image is explicitly declared as self-authored. "
            "The self-authorship claim is accepted as the "
            "permission basis for this automated assessment."
        )

        if _has_text(
            evidence.licence_evidence_text
        ):
            rationale += (
                " Relevant evidence: "
                f"'{evidence.licence_evidence_text.strip()}'."
            )

        return (
            True,
            rationale,
            False,
        )

    if not _has_text(
        evidence.licence_name
    ):
        return (
            False,
            (
                "No licence name, licensing statement, "
                "permission statement, or self-authorship "
                "claim was detected."
            ),
            False,
        )

    licence = (
        evidence.licence_name.strip()
    )

    if not _is_known_licence(
        licence
    ):
        rationale = (
            f"The webpage appears to provide a licence or "
            f"permission basis identified as '{licence}', "
            "but the deterministic rule engine does not "
            "recognise this licence reliably enough to "
            "classify it automatically."
        )

        if _has_text(
            evidence.licence_evidence_source
        ):
            rationale += (
                " The information was found in the "
                f"{evidence.licence_evidence_source.strip()}."
            )

        if _has_text(
            evidence.licence_evidence_text
        ):
            rationale += (
                " Relevant evidence: "
                f"'{evidence.licence_evidence_text.strip()}'."
            )

        return (
            False,
            rationale,
            True,
        )

    rationale = (
        "The supplied licence or permission basis was "
        f"identified as '{licence}'."
    )

    if _has_text(
        evidence.licence_evidence_source
    ):
        rationale += (
            " The information was found in the "
            f"{evidence.licence_evidence_source.strip()}."
        )

    if _has_text(
        evidence.licence_evidence_text
    ):
        rationale += (
            " Relevant evidence: "
            f"'{evidence.licence_evidence_text.strip()}'."
        )

    return (
        True,
        rationale,
        False,
    )


def _terms_result(
    evidence: AttributionEvidence,
    is_self_authored: bool,
) -> tuple[
    bool,
    str,
]:
    if is_self_authored:
        return (
            True,
            (
                "The image is declared as self-authored, so "
                "a separate external licence-terms URL is not "
                "required for this assessment."
            ),
        )

    if not _has_text(
        evidence.licence_url
    ):
        return (
            False,
            (
                "No URL or hyperlink identifying the location "
                "of the applicable licence terms was detected."
            ),
        )

    return (
        True,
        (
            "The location of the applicable licence terms was "
            f"supplied as '{evidence.licence_url.strip()}'."
        ),
    )


def _determine_label(
    score: int,
) -> str:
    if score == 100:
        return "Fully Compliant"

    if score > 0:
        return "Partially Compliant"

    return "Non-Compliant"


def _build_recommendations(
    owner_passed: bool,
    licence_passed: bool,
    terms_passed: bool,
    unknown_licence: bool,
    self_authored: bool,
) -> list[str]:
    recommendations: list[str] = []

    if not owner_passed:
        recommendations.append(
            "Identify the image creator or copyright holder."
        )

    if (
        not licence_passed
        and not unknown_licence
    ):
        recommendations.append(
            "State the licence or permission basis that allows "
            "the image to be used."
        )

    if not terms_passed:
        recommendations.append(
            "Provide a URL or hyperlink to the applicable "
            "licence terms."
        )

    if self_authored:
        recommendations.append(
            "Manually verify the self-authorship claim and "
            "confirm that the named person created the image "
            "or owns the copyright."
        )

    return recommendations


def assess_images(
    evidence_items: list[AttributionEvidence],
    intended_use: str = "educational coursework",
) -> list[ImageAssessment]:
    """
    Assess exactly three criteria:

    1. Copyright owner identified - 34
    2. Licence or permission identified - 33
    3. Licence terms location provided - 33
    """

    _ = intended_use

    assessments: list[
        ImageAssessment
    ] = []

    for evidence in evidence_items:
        self_authored = (
            _is_self_authored(
                evidence
            )
        )

        (
            owner_passed,
            owner_rationale,
        ) = _owner_result(
            evidence
        )

        (
            licence_passed,
            licence_rationale,
            unknown_licence,
        ) = _licence_result(
            evidence,
            self_authored,
        )

        (
            terms_passed,
            terms_rationale,
        ) = _terms_result(
            evidence,
            self_authored,
        )

        criteria = [
            _criterion(
                CRITERION_OWNER,
                owner_passed,
                OWNER_WEIGHT,
                owner_rationale,
            ),
            _criterion(
                CRITERION_LICENCE,
                licence_passed,
                LICENCE_WEIGHT,
                licence_rationale,
            ),
            _criterion(
                CRITERION_TERMS,
                terms_passed,
                TERMS_WEIGHT,
                terms_rationale,
            ),
        ]

        total_score = sum(
            criterion.score
            for criterion
            in criteria
        )

        manual_review_required = (
            self_authored
            or unknown_licence
        )

        manual_review_reason: (
            str | None
        ) = None

        if self_authored:
            manual_review_reason = (
                SELF_AUTHORED_MANUAL_REVIEW_REASON
            )

        elif unknown_licence:
            manual_review_reason = (
                "The webpage supplies licence or permission "
                "information, but the deterministic rule engine "
                "does not recognise the licence reliably enough "
                "to assess it automatically. Human review is "
                "recommended."
            )

        recommendations = (
            _build_recommendations(
                owner_passed=(
                    owner_passed
                ),
                licence_passed=(
                    licence_passed
                ),
                terms_passed=(
                    terms_passed
                ),
                unknown_licence=(
                    unknown_licence
                ),
                self_authored=(
                    self_authored
                ),
            )
        )

        assessments.append(
            ImageAssessment(
                image_src=(
                    evidence.image.src
                ),
                total_score=(
                    total_score
                ),
                label=(
                    _determine_label(
                        total_score
                    )
                ),
                criteria=criteria,
                manual_review_required=(
                    manual_review_required
                ),
                manual_review_reason=(
                    manual_review_reason
                ),
                recommendations=(
                    recommendations
                ),
            )
        )

    return assessments