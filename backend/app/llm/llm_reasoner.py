import json

import requests
from pydantic import ValidationError

from app.models.schemas import (
    AttributionEvidence,
    LlmCriterionAssessment,
    LlmImageAssessment,
)


OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"

DEFAULT_MODEL = "llama3:8b"


CRITERION_OWNER = (
    "Copyright owner identified"
)

CRITERION_LICENCE = (
    "Licence or permission identified"
)

CRITERION_TERMS = (
    "Licence terms location provided"
)


REQUIRED_CRITERIA = (
    CRITERION_OWNER,
    CRITERION_LICENCE,
    CRITERION_TERMS,
)


SELF_AUTHORED_LICENCE = (
    "Self-authored claim"
)


SELF_AUTHORSHIP_REVIEW_REASON = (
    "The image is declared as self-authored. The supplied "
    "claim is sufficient for automated coursework assessment, "
    "but the system cannot independently verify that the named "
    "person created the image or owns the copyright."
)


class LlmReasoningError(Exception):
    """
    Raised when Ollama cannot produce a valid assessment.
    """


def _has_text(
    value: str | None,
) -> bool:
    return bool(
        value
        and value.strip()
    )


def _display(
    value: str | None,
) -> str:
    if not _has_text(
        value
    ):
        return "Not detected"

    return value.strip()


def _normalise(
    value: str | None,
) -> str:
    if not value:
        return ""

    return " ".join(
        value.casefold().split()
    )


def _append_sentence(
    existing: str,
    sentence: str,
) -> str:
    existing = existing.strip()
    sentence = sentence.strip()

    if not existing:
        return sentence

    if not sentence:
        return existing

    return (
        f"{existing} {sentence}"
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


# ============================================================
# EXPLICIT SOURCE ONLY
# ============================================================


def _explicit_source_reference(
    evidence: AttributionEvidence,
) -> str | None:
    """
    Return only source attribution actually extracted from
    the student's webpage.

    evidence.image.src is NEVER used.
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


# ============================================================
# PROMPT
# ============================================================


def _build_prompt(
    evidence: AttributionEvidence,
    intended_use: str,
) -> str:
    source_reference = (
        _explicit_source_reference(
            evidence
        )
    )

    return f"""
You are independently assessing copyright and licence information
for one image in a student webpage.

Use ONLY the supplied webpage evidence.

Do not invent facts.

Assess exactly THREE criteria:

1. {CRITERION_OWNER}
2. {CRITERION_LICENCE}
3. {CRITERION_TERMS}

============================================================
IMPORTANT: TECHNICAL IMAGE URL
============================================================

Technical image URL:

{_display(evidence.image.src)}

This URL identifies which image is being assessed.

It is NOT automatically copyright attribution.

It is NOT automatically a student-supplied source/reference.

It is NOT automatically a licence.

It is NOT automatically a licence-terms URL.

A relative path such as:

<img src="photo.jpg">

may be converted by the crawler into a full URL.

That conversion must NEVER make the copyright criterion pass.

Similarly, an externally hosted image URL alone must not be treated
as attribution merely because it contains a recognisable website name.

Only explicit attribution evidence extracted from the student's
caption, nearby attribution text, hyperlink, or similar information
may count as a source/reference.

============================================================
SUPPLIED EVIDENCE
============================================================

Alt text:
{_display(evidence.image.alt)}

Title:
{_display(evidence.image.title)}

Figure caption:
{_display(evidence.caption)}

Nearby text:
{_display(evidence.nearby_text)}

Detected creator/copyright holder:
{_display(evidence.possible_author)}

Copyright evidence source:
{_display(evidence.author_evidence_source)}

Copyright evidence text:
{_display(evidence.author_evidence_text)}

Explicit source website:
{_display(evidence.source_name)}

Explicit source/reference URL:
{_display(evidence.source_url)}

Explicit source/reference accepted by extractor:
{_display(source_reference)}

Source evidence source:
{_display(evidence.source_evidence_source)}

Source evidence text:
{_display(evidence.source_evidence_text)}

Detected licence/permission:
{_display(evidence.licence_name)}

Licence evidence source:
{_display(evidence.licence_evidence_source)}

Licence evidence text:
{_display(evidence.licence_evidence_text)}

Licence terms URL:
{_display(evidence.licence_url)}

Declared intended use:
{intended_use}

============================================================
CRITERION 1
COPYRIGHT OWNER IDENTIFIED
============================================================

PASS when:

- a creator or copyright holder is explicitly identified; or
- the image is explicitly self-authored; or
- no named creator is supplied but EXPLICIT source attribution was
  provided by the student.

For this coursework assessment, explicitly supplied source attribution
may be accepted as the student's copyright reference.

Do not claim that a source website legally owns copyright unless the
student explicitly states this.

CRITICAL:

If:

Copyright evidence = Not detected

and:

Source evidence = Not detected

then this criterion must FAIL.

The technical image URL must not cause a pass.

============================================================
CRITERION 2
LICENCE OR PERMISSION IDENTIFIED
============================================================

PASS when an explicit:

- licence;
- permission statement;
- self-authorship statement;
- public-domain basis;
- or other clear permission basis

is supplied.

A source/reference alone is NOT a licence.

The image host alone is NOT a licence.

You may interpret a licence even if the deterministic rule engine
does not recognise it, provided the supplied webpage evidence is
sufficient.

============================================================
CRITERION 3
LICENCE TERMS LOCATION PROVIDED
============================================================

For a self-authored image:

PASS.

An external licence-terms URL is not required.

For an externally sourced image:

PASS only when a URL or hyperlink associated with the applicable
licence/permission terms is supplied.

Do not treat:

- image src;
- raw image URL;
- photographer profile;
- source homepage;
- ordinary source reference

as the licence-terms location unless the webpage explicitly associates
it with the licence terms.

============================================================
RATIONALE QUALITY
============================================================

For every criterion provide approximately 2 to 4 useful sentences.

Explain:

- what evidence was found;
- where it was found;
- what the relevant evidence says;
- why it causes Pass or Fail.

Do not return vague responses such as:

"Creator found."

"Source provided."

"Licence missing."

"No URL."

============================================================
MANUAL REVIEW
============================================================

Manual review is required when:

- self-authorship cannot be independently verified;
- the supplied licence is ambiguous;
- the supplied licence cannot be interpreted reliably;
- evidence is contradictory;
- human verification is genuinely necessary.

Do NOT recommend manual review merely because information is missing.

============================================================
OVERALL CLASSIFICATION
============================================================

3 passes:
Fully Compliant

1 or 2 passes:
Partially Compliant

0 passes:
Non-Compliant

Return exactly the three required criteria.

Return JSON only and match the supplied schema.
""".strip()


# ============================================================
# NORMALISATION
# ============================================================


def _criterion_map(
    assessment: LlmImageAssessment,
) -> dict[
    str,
    LlmCriterionAssessment,
]:
    return {
        criterion.criterion: criterion
        for criterion
        in assessment.criteria
    }


def _normalise_criteria(
    assessment: LlmImageAssessment,
) -> LlmImageAssessment:
    existing = (
        _criterion_map(
            assessment
        )
    )

    normalised: list[
        LlmCriterionAssessment
    ] = []

    for name in REQUIRED_CRITERIA:
        criterion = existing.get(
            name
        )

        if criterion is None:
            criterion = (
                LlmCriterionAssessment(
                    criterion=name,
                    passed=False,
                    rationale=(
                        "The AI response did not contain a "
                        "valid assessment for this required "
                        "criterion."
                    ),
                )
            )

        normalised.append(
            criterion
        )

    assessment.criteria = (
        normalised
    )

    return assessment


# ============================================================
# COPYRIGHT CONSISTENCY
# ============================================================


def _owner_consistency(
    evidence: AttributionEvidence,
) -> tuple[
    bool,
    str,
]:
    # ---------------------------------------------------------
    # Named creator
    # ---------------------------------------------------------

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
            rationale = _append_sentence(
                rationale,
                (
                    "The information was found in the "
                    f"{evidence.author_evidence_source.strip()}."
                ),
            )

        if _has_text(
            evidence.author_evidence_text
        ):
            rationale = _append_sentence(
                rationale,
                (
                    "Relevant evidence: "
                    f"'{evidence.author_evidence_text.strip()}'."
                ),
            )

        rationale = _append_sentence(
            rationale,
            (
                "Because this evidence explicitly identifies "
                "the creator or copyright holder associated "
                "with the image, this criterion passes."
            ),
        )

        return (
            True,
            rationale,
        )

    # ---------------------------------------------------------
    # Explicit source attribution
    # ---------------------------------------------------------

    source_reference = (
        _explicit_source_reference(
            evidence
        )
    )

    if source_reference:
        rationale = (
            "No separately named creator or copyright holder "
            "was detected. However, the student explicitly "
            f"supplied '{source_reference}' as the image "
            "source/reference. Under the coursework assessment "
            "policy, this explicit source attribution is "
            "accepted as the student's copyright reference."
        )

        if _has_text(
            evidence.source_evidence_source
        ):
            rationale = _append_sentence(
                rationale,
                (
                    "The source information was found in the "
                    f"{evidence.source_evidence_source.strip()}."
                ),
            )

        if _has_text(
            evidence.source_evidence_text
        ):
            rationale = _append_sentence(
                rationale,
                (
                    "Relevant source evidence: "
                    f"'{evidence.source_evidence_text.strip()}'."
                ),
            )

        rationale = _append_sentence(
            rationale,
            (
                "The criterion passes because explicit source "
                "attribution was supplied; the technical image "
                "URL alone would not be sufficient."
            ),
        )

        return (
            True,
            rationale,
        )

    # ---------------------------------------------------------
    # Nothing supplied
    # ---------------------------------------------------------

    return (
        False,
        (
            "No image creator or copyright holder was identified "
            "in the supplied webpage evidence, and no explicit "
            "source attribution was detected. The technical "
            "image URL only identifies where the image file is "
            "loaded from and is not treated as copyright "
            "attribution. Therefore this criterion fails."
        ),
    )


# ============================================================
# APPLY CONSISTENCY RULES
# ============================================================


def _apply_consistency_rules(
    assessment: LlmImageAssessment,
    evidence: AttributionEvidence,
) -> LlmImageAssessment:
    criteria = (
        _criterion_map(
            assessment
        )
    )

    owner = criteria[
        CRITERION_OWNER
    ]

    licence = criteria[
        CRITERION_LICENCE
    ]

    terms = criteria[
        CRITERION_TERMS
    ]

    self_authored = (
        _is_self_authored(
            evidence
        )
    )

    # ---------------------------------------------------------
    # Owner
    # ---------------------------------------------------------

    (
        owner.passed,
        owner.rationale,
    ) = _owner_consistency(
        evidence
    )

    # ---------------------------------------------------------
    # Self-authored
    # ---------------------------------------------------------

    if self_authored:
        licence.passed = True

        rationale = (
            "The image is explicitly declared as self-authored. "
            "The self-authorship claim is accepted as the "
            "permission basis for automated coursework assessment."
        )

        if _has_text(
            evidence.licence_evidence_source
        ):
            rationale = _append_sentence(
                rationale,
                (
                    "The information was found in the "
                    f"{evidence.licence_evidence_source.strip()}."
                ),
            )

        if _has_text(
            evidence.licence_evidence_text
        ):
            rationale = _append_sentence(
                rationale,
                (
                    "Relevant evidence: "
                    f"'{evidence.licence_evidence_text.strip()}'."
                ),
            )

        licence.rationale = (
            rationale
        )

        terms.passed = True

        terms.rationale = (
            "The image is explicitly declared as self-authored. "
            "A separate external licence-terms URL is therefore "
            "not required for this coursework assessment."
        )

        assessment.manual_review_required = (
            True
        )

        assessment.manual_review_reason = (
            SELF_AUTHORSHIP_REVIEW_REASON
        )

        return assessment

    # ---------------------------------------------------------
    # External image with no licence
    # ---------------------------------------------------------

    if not _has_text(
        evidence.licence_name
    ):
        licence.passed = False

        source_reference = (
            _explicit_source_reference(
                evidence
            )
        )

        if source_reference:
            licence.rationale = (
                "No licence name, licensing statement, "
                "permission statement, or self-authorship claim "
                "was identified. The student supplied "
                f"'{source_reference}' as explicit source "
                "attribution, which identifies where the image "
                "was obtained but does not itself establish "
                "permission to use it. Therefore this criterion "
                "fails."
            )

        else:
            licence.rationale = (
                "No licence name, licensing statement, "
                "permission statement, or self-authorship claim "
                "was identified in the supplied webpage evidence. "
                "Therefore no permission basis has been established "
                "and this criterion fails."
            )

    # ---------------------------------------------------------
    # External image with supplied licence
    # ---------------------------------------------------------

    elif licence.passed:
        licence_name = (
            evidence.licence_name.strip()
        )

        rationale = (
            "The supplied webpage evidence identifies "
            f"'{licence_name}' as the licence or permission "
            "basis for the image."
        )

        if _has_text(
            evidence.licence_evidence_source
        ):
            rationale = _append_sentence(
                rationale,
                (
                    "The information was found in the "
                    f"{evidence.licence_evidence_source.strip()}."
                ),
            )

        if _has_text(
            evidence.licence_evidence_text
        ):
            rationale = _append_sentence(
                rationale,
                (
                    "Relevant evidence: "
                    f"'{evidence.licence_evidence_text.strip()}'."
                ),
            )

        rationale = _append_sentence(
            rationale,
            (
                "The AI considers the supplied evidence "
                "sufficient to establish the licence or "
                "permission basis, so this criterion passes."
            ),
        )

        licence.rationale = (
            rationale
        )

    # ---------------------------------------------------------
    # Licence terms
    # ---------------------------------------------------------

    if not _has_text(
        evidence.licence_url
    ):
        terms.passed = False

        source_reference = (
            _explicit_source_reference(
                evidence
            )
        )

        if source_reference:
            terms.rationale = (
                "No URL or hyperlink explicitly associated with "
                "the applicable licence terms was identified. "
                f"The student supplied '{source_reference}' as "
                "the image source/reference, but this identifies "
                "where the image was obtained rather than where "
                "the applicable licence terms can be found. "
                "Therefore this criterion fails."
            )

        else:
            terms.rationale = (
                "No URL or hyperlink identifying the location "
                "of the applicable licence terms was supplied. "
                "The technical image URL is not a licence-terms "
                "URL, so this criterion fails."
            )

    else:
        terms.passed = True

        terms.rationale = (
            "The webpage supplies a URL for the applicable "
            "licence or permission terms: "
            f"'{evidence.licence_url.strip()}'. Because this "
            "hyperlink identifies the location of the applicable "
            "licence terms, this criterion passes."
        )

    return assessment


# ============================================================
# CLASSIFICATION
# ============================================================


def _apply_classification(
    assessment: LlmImageAssessment,
) -> LlmImageAssessment:
    passed = [
        criterion
        for criterion
        in assessment.criteria
        if criterion.passed
    ]

    failed = [
        criterion
        for criterion
        in assessment.criteria
        if not criterion.passed
    ]

    passed_count = len(
        passed
    )

    if passed_count == 3:
        assessment.overall_label = (
            "Fully Compliant"
        )

        assessment.explanation = (
            "All three required copyright and licence criteria "
            "pass. The supplied evidence provides an acceptable "
            "copyright reference, a licence or permission basis, "
            "and the required licence-terms location where "
            "applicable."
        )

    elif passed_count > 0:
        assessment.overall_label = (
            "Partially Compliant"
        )

        missing = ", ".join(
            criterion.criterion
            for criterion
            in failed
        )

        assessment.explanation = (
            f"{passed_count} of the three required copyright "
            "and licence criteria pass. The remaining failed "
            f"requirement(s) are: {missing}."
        )

    else:
        assessment.overall_label = (
            "Non-Compliant"
        )

        assessment.explanation = (
            "None of the three required copyright and licence "
            "criteria pass. The supplied webpage evidence does "
            "not provide sufficient copyright attribution, "
            "permission information, or licence-terms location."
        )

    return assessment


# ============================================================
# MANUAL REVIEW
# ============================================================


def _apply_manual_review(
    assessment: LlmImageAssessment,
    evidence: AttributionEvidence,
) -> LlmImageAssessment:
    if _is_self_authored(
        evidence
    ):
        assessment.manual_review_required = (
            True
        )

        assessment.manual_review_reason = (
            SELF_AUTHORSHIP_REVIEW_REASON
        )

        return assessment

    if not assessment.manual_review_required:
        assessment.manual_review_reason = (
            None
        )

    elif not _has_text(
        assessment.manual_review_reason
    ):
        assessment.manual_review_reason = (
            "The supplied copyright or licence information "
            "cannot be interpreted reliably through automated "
            "assessment and requires human review."
        )

    return assessment


# ============================================================
# MAIN
# ============================================================


def assess_image_with_llm(
    evidence: AttributionEvidence,
    intended_use: str,
    model: str = DEFAULT_MODEL,
    timeout_seconds: int = 600,
) -> LlmImageAssessment:
    schema = (
        LlmImageAssessment.model_json_schema()
    )

    payload = {
        "model": model,
        "prompt": _build_prompt(
            evidence=evidence,
            intended_use=intended_use,
        ),
        "format": schema,
        "stream": False,
        "keep_alive": "10m",
        "options": {
            "temperature": 0,
            "seed": 42,
            "num_ctx": 4096,
            "num_predict": 750,
        },
    }

    try:
        response = requests.post(
            OLLAMA_GENERATE_URL,
            json=payload,
            timeout=timeout_seconds,
        )

        response.raise_for_status()

    except requests.RequestException as error:
        raise LlmReasoningError(
            "Ollama request failed: "
            f"{error}"
        ) from error

    try:
        response_data = (
            response.json()
        )

        generated_text = (
            response_data["response"]
        )

        generated_json = (
            json.loads(
                generated_text
            )
        )

    except (
        ValueError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
    ) as error:
        raise LlmReasoningError(
            "Ollama returned an invalid JSON response."
        ) from error

    generated_json[
        "image_src"
    ] = evidence.image.src

    try:
        assessment = (
            LlmImageAssessment.model_validate(
                generated_json
            )
        )

    except ValidationError as error:
        raise LlmReasoningError(
            "The LLM response did not match the required schema."
        ) from error

    assessment = (
        _normalise_criteria(
            assessment
        )
    )

    assessment = (
        _apply_consistency_rules(
            assessment,
            evidence,
        )
    )

    assessment = (
        _apply_classification(
            assessment
        )
    )

    assessment = (
        _apply_manual_review(
            assessment,
            evidence,
        )
    )

    return assessment