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


CRITERION_OWNER = "Copyright owner identified"

CRITERION_LICENCE = "Licence or permission identified"

CRITERION_TERMS = "Licence terms location provided"


REQUIRED_CRITERIA = (
    CRITERION_OWNER,
    CRITERION_LICENCE,
    CRITERION_TERMS,
)


SELF_AUTHORED_LICENCE = "Self-authored claim"


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


# ============================================================
# BASIC HELPERS
# ============================================================


def _has_text(
    value: str | None,
) -> bool:
    """
    Return True when a value contains useful non-empty text.
    """

    return bool(
        value
        and value.strip()
    )


def _display(
    value: str | None,
) -> str:
    """
    Convert an optional value into text suitable for the
    LLM prompt.
    """

    if not _has_text(value):
        return "Not detected"

    return value.strip()


def _normalise(
    value: str | None,
) -> str:
    """
    Normalise text for case-insensitive comparisons.
    """

    if not value:
        return ""

    return " ".join(
        value.casefold().split()
    )


def _append_sentence(
    existing: str,
    sentence: str,
) -> str:
    """
    Append one sentence to an existing rationale.
    """

    existing = existing.strip()
    sentence = sentence.strip()

    if not existing:
        return sentence

    if not sentence:
        return existing

    return f"{existing} {sentence}"


# ============================================================
# SELF AUTHORSHIP
# ============================================================


def _is_self_authored(
    evidence: AttributionEvidence,
) -> bool:
    """
    Determine whether the extractor has explicitly classified
    the image as self-authored.
    """

    return (
        _normalise(
            evidence.licence_name
        )
        == _normalise(
            SELF_AUTHORED_LICENCE
        )
    )


# ============================================================
# EXPLICIT SOURCE ATTRIBUTION
# ============================================================


def _explicit_source_reference(
    evidence: AttributionEvidence,
) -> str | None:
    """
    Return only source/reference information explicitly
    extracted from the student's webpage.

    evidence.image.src is deliberately never used here.
    """

    has_source_evidence = (
        _has_text(
            evidence.source_evidence_source
        )
        or _has_text(
            evidence.source_evidence_text
        )
    )

    if not has_source_evidence:
        return None

    if _has_text(
        evidence.source_url
    ):
        return evidence.source_url.strip()

    if _has_text(
        evidence.source_name
    ):
        return evidence.source_name.strip()

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
    """
    Build the copyright and licence assessment prompt.
    """

    source_reference = (
        _explicit_source_reference(
            evidence
        )
    )

    return f"""
You are independently assessing copyright and licence information
for one image used in a student's webpage.

Use ONLY the supplied webpage evidence.

Do not invent information.

Do not use information that was not extracted from the student's
webpage.

You must assess exactly THREE criteria:

1. {CRITERION_OWNER}
2. {CRITERION_LICENCE}
3. {CRITERION_TERMS}

============================================================
TECHNICAL IMAGE URL
============================================================

Technical image URL:

{_display(evidence.image.src)}

This URL identifies which image is being assessed.

IMPORTANT:

The technical image URL is NOT automatically copyright attribution.

The technical image URL is NOT automatically a student-supplied
source/reference.

The technical image URL is NOT automatically a licence.

The technical image URL is NOT automatically a licence-terms URL.

For example:

    <img src="photo.jpg">

may be resolved by the crawler to:

    https://example.com/student/photo.jpg

The resolved URL merely identifies where the browser loaded the
image.

It must not automatically satisfy any copyright requirement.

Similarly, an externally hosted image URL must not automatically
be treated as copyright attribution merely because the URL contains
a recognisable domain such as Flickr, Wikimedia, Pexels, Unsplash,
or Pixabay.

Only explicit evidence extracted from the student's webpage may
be used as attribution evidence.

============================================================
SUPPLIED WEBPAGE EVIDENCE
============================================================

Alt text:
{_display(evidence.image.alt)}

Title:
{_display(evidence.image.title)}

Figure caption:
{_display(evidence.caption)}

Nearby text:
{_display(evidence.nearby_text)}

Detected creator or copyright holder:
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

Detected licence or permission:
{_display(evidence.licence_name)}

Licence evidence source:
{_display(evidence.licence_evidence_source)}

Licence evidence text:
{_display(evidence.licence_evidence_text)}

Detected licence terms URL:
{_display(evidence.licence_url)}

Declared intended use:
{intended_use}

============================================================
CRITERION 1
COPYRIGHT OWNER IDENTIFIED
============================================================

Criterion name exactly:

{CRITERION_OWNER}

PASS when at least one of the following applies:

1. A creator, photographer, author, copyright holder, or copyright
   owner is explicitly identified.

2. The image is explicitly identified as self-authored.

3. No separately named creator or copyright holder is supplied,
   but the student explicitly provides a source/reference associated
   with the image.

For this coursework assessment, an explicitly supplied source or
reference may be accepted as the student's copyright reference.

This does NOT mean that the source website is necessarily the legal
copyright owner.

Do not state that Flickr, Wikimedia, Pexels, Unsplash, Pixabay,
or another website legally owns copyright unless the supplied
evidence explicitly states that.

FAIL when:

- no creator or copyright holder is identified;
- no self-authorship claim is supplied; and
- no explicit source/reference attribution was extracted.

CRITICAL:

The technical image URL alone must NEVER cause this criterion to pass.

============================================================
CRITERION 2
LICENCE OR PERMISSION IDENTIFIED
============================================================

Criterion name exactly:

{CRITERION_LICENCE}

PASS when the supplied webpage evidence explicitly identifies:

- a licence;
- a permission statement;
- a public-domain basis;
- a self-authorship statement;
- or another clear permission basis.

Examples include:

- Creative Commons;
- CC BY;
- CC BY-SA;
- CC BY-NC;
- CC0;
- Pexels License;
- Unsplash License;
- Pixabay Content License;
- public domain;
- explicit permission;
- self-authorship.

IMPORTANT:

If the supplied evidence explicitly says:

    Licensed under Creative Commons

then this criterion PASSES.

The fact that a specific Creative Commons variant was not supplied
does not mean that no licence was identified.

It may affect whether the terms are sufficiently located or whether
manual review is appropriate, but the licence/permission criterion
itself passes because Creative Commons was explicitly stated.

A source/reference by itself is NOT a licence.

A source website by itself is NOT permission.

An image host by itself is NOT permission.

============================================================
CRITERION 3
LICENCE TERMS LOCATION PROVIDED
============================================================

Criterion name exactly:

{CRITERION_TERMS}

For a self-authored image:

PASS.

A separate external licence-terms URL is not required when the
student explicitly declares the image to be self-authored.

For an externally sourced image:

PASS only when the supplied webpage contains a URL or hyperlink
associated with the applicable licence or permission terms.

Examples include:

- a Creative Commons licence URL;
- the Pexels License page;
- the Unsplash License page;
- the Pixabay licence page;
- another page explicitly identified as containing the applicable
  licence or permission terms.

Do NOT automatically accept:

- the technical image URL;
- the raw image src;
- a photographer profile;
- an image page;
- a Flickr image page;
- a Wikimedia image page;
- a source homepage;
- an ordinary source/reference URL.

Those URLs identify the source or image unless the webpage explicitly
associates them with the applicable licence terms.

============================================================
EXAMPLE
============================================================

Suppose the evidence contains:

Creator:
Maggio7 on Flickr

Caption:
Image by Maggio7 on Flickr. Licensed under Creative Commons.

Licence:
Creative Commons

Licence terms URL:
Not detected

The correct assessment is:

Copyright owner identified:
PASS

Licence or permission identified:
PASS

Licence terms location provided:
FAIL

The licence criterion passes because the student explicitly stated
that the image is licensed under Creative Commons.

The licence-terms criterion fails because no hyperlink to the
applicable Creative Commons licence terms was supplied.

============================================================
RATIONALE QUALITY
============================================================

Every criterion must contain a useful evidence-based rationale.

Each rationale should normally contain approximately 2 to 4
sentences.

Explain:

1. What evidence was found.
2. Where the evidence was found.
3. What the evidence says.
4. Why the evidence causes the criterion to pass or fail.

Do not return vague rationales such as:

"Creator found."

"Source provided."

"Licence missing."

"No URL."

============================================================
MANUAL REVIEW
============================================================

Manual review should be required only when genuinely necessary.

Examples:

- a self-authorship claim cannot be independently verified;
- contradictory evidence exists;
- a supplied licence is too ambiguous to interpret reliably;
- human verification is required.

Do NOT require manual review merely because a criterion fails.

Missing information can simply result in a failed criterion.

============================================================
OVERALL CLASSIFICATION
============================================================

Exactly 3 passes:

Fully Compliant

Exactly 1 or 2 passes:

Partially Compliant

Exactly 0 passes:

Non-Compliant

Return exactly the three required criteria.

Use these exact criterion names:

{CRITERION_OWNER}
{CRITERION_LICENCE}
{CRITERION_TERMS}

Return JSON only.

The JSON must match the supplied schema.
""".strip()


# ============================================================
# CRITERION MAP
# ============================================================


def _criterion_map(
    assessment: LlmImageAssessment,
) -> dict[
    str,
    LlmCriterionAssessment,
]:
    """
    Index criteria by their exact criterion names.
    """

    return {
        criterion.criterion: criterion
        for criterion
        in assessment.criteria
    }


# ============================================================
# NORMALISE CRITERIA
# ============================================================


def _normalise_criteria(
    assessment: LlmImageAssessment,
) -> LlmImageAssessment:
    """
    Guarantee exactly the three required criteria.

    If Ollama omits a criterion, create it so the consistency
    layer can evaluate it from the extracted evidence.
    """

    existing = (
        _criterion_map(
            assessment
        )
    )

    normalised: list[
        LlmCriterionAssessment
    ] = []

    for criterion_name in REQUIRED_CRITERIA:
        criterion = existing.get(
            criterion_name
        )

        if criterion is None:
            criterion = (
                LlmCriterionAssessment(
                    criterion=criterion_name,
                    passed=False,
                    rationale=(
                        "The AI response did not contain a "
                        "valid assessment for this required "
                        "criterion. The extracted webpage "
                        "evidence will therefore be used to "
                        "apply the assessment consistency "
                        "rules."
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
# COPYRIGHT OWNER CONSISTENCY
# ============================================================


def _owner_consistency(
    evidence: AttributionEvidence,
) -> tuple[
    bool,
    str,
]:
    """
    Determine the copyright-owner criterion directly from
    the extracted evidence.
    """

    # --------------------------------------------------------
    # Named creator / copyright holder
    # --------------------------------------------------------

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
                "Because the supplied webpage evidence "
                "explicitly identifies the creator or "
                "copyright holder associated with the image, "
                "this criterion passes."
            ),
        )

        return (
            True,
            rationale,
        )

    # --------------------------------------------------------
    # Self-authorship
    # --------------------------------------------------------

    if _is_self_authored(
        evidence
    ):
        rationale = (
            "The supplied webpage evidence explicitly "
            "identifies the image as self-authored."
        )

        if _has_text(
            evidence.licence_evidence_source
        ):
            rationale = _append_sentence(
                rationale,
                (
                    "The self-authorship information was "
                    "found in the "
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
                "The explicit self-authorship claim is "
                "accepted as identifying the student as the "
                "creator for this automated coursework "
                "assessment, so this criterion passes."
            ),
        )

        return (
            True,
            rationale,
        )

    # --------------------------------------------------------
    # Explicit source/reference
    # --------------------------------------------------------

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
                "This acceptance is specific to the "
                "coursework assessment and does not assert "
                "that the referenced website is legally the "
                "copyright owner."
            ),
        )

        return (
            True,
            rationale,
        )

    # --------------------------------------------------------
    # Nothing supplied
    # --------------------------------------------------------

    rationale = (
        "No image creator or copyright holder was identified "
        "in the supplied webpage evidence, and no explicit "
        "source attribution or self-authorship claim was "
        "detected."
    )

    if _has_text(
        evidence.image.src
    ):
        rationale = _append_sentence(
            rationale,
            (
                "The technical image URL only identifies "
                "where the image file is loaded from and is "
                "not treated as copyright attribution."
            ),
        )

    rationale = _append_sentence(
        rationale,
        (
            "Therefore this criterion fails."
        ),
    )

    return (
        False,
        rationale,
    )


# ============================================================
# LICENCE CONSISTENCY
# ============================================================


def _licence_consistency(
    evidence: AttributionEvidence,
) -> tuple[
    bool,
    str,
]:
    """
    Determine whether a licence or permission basis exists.

    Explicitly detected licence evidence passes this criterion
    even when Ollama omitted the criterion or returned False.
    """

    # --------------------------------------------------------
    # Self-authored
    # --------------------------------------------------------

    if _is_self_authored(
        evidence
    ):
        rationale = (
            "The image is explicitly declared as "
            "self-authored. The self-authorship claim is "
            "accepted as the permission basis for automated "
            "coursework assessment."
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

        return (
            True,
            rationale,
        )

    # --------------------------------------------------------
    # Explicit licence / permission
    # --------------------------------------------------------

    if _has_text(
        evidence.licence_name
    ):
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
                "Because the supplied webpage evidence "
                "explicitly identifies a licence or permission "
                "basis, this criterion passes."
            ),
        )

        return (
            True,
            rationale,
        )

    # --------------------------------------------------------
    # No licence
    # --------------------------------------------------------

    source_reference = (
        _explicit_source_reference(
            evidence
        )
    )

    if source_reference:
        rationale = (
            "No licence name, licensing statement, permission "
            "statement, public-domain basis, or self-authorship "
            "claim was identified in the supplied webpage "
            "evidence. The student supplied "
            f"'{source_reference}' as explicit source "
            "attribution, which identifies where the image "
            "came from but does not itself establish permission "
            "to use the image. Therefore this criterion fails."
        )

        return (
            False,
            rationale,
        )

    return (
        False,
        (
            "No licence name, licensing statement, permission "
            "statement, public-domain basis, or self-authorship "
            "claim was identified in the supplied webpage "
            "evidence. No permission basis has therefore been "
            "established, so this criterion fails."
        ),
    )


# ============================================================
# LICENCE TERMS CONSISTENCY
# ============================================================


def _terms_consistency(
    evidence: AttributionEvidence,
) -> tuple[
    bool,
    str,
]:
    """
    Determine whether the applicable licence terms location
    has been supplied.
    """

    # --------------------------------------------------------
    # Self-authored
    # --------------------------------------------------------

    if _is_self_authored(
        evidence
    ):
        return (
            True,
            (
                "The image is explicitly declared as "
                "self-authored. A separate external "
                "licence-terms URL is therefore not required "
                "for this coursework assessment. The "
                "criterion passes on the basis of the "
                "self-authorship claim."
            ),
        )

    # --------------------------------------------------------
    # External licence URL
    # --------------------------------------------------------

    if _has_text(
        evidence.licence_url
    ):
        licence_url = (
            evidence.licence_url.strip()
        )

        rationale = (
            "The webpage supplies a URL or hyperlink for the "
            "applicable licence or permission terms: "
            f"'{licence_url}'."
        )

        if _has_text(
            evidence.licence_url_evidence_source
        ):
            rationale = _append_sentence(
                rationale,
                (
                    "The licence-terms link was found in the "
                    f"{evidence.licence_url_evidence_source.strip()}."
                ),
            )

        if _has_text(
            evidence.licence_url_evidence_text
        ):
            rationale = _append_sentence(
                rationale,
                (
                    "Relevant link evidence: "
                    f"'{evidence.licence_url_evidence_text.strip()}'."
                ),
            )

        rationale = _append_sentence(
            rationale,
            (
                "Because the supplied hyperlink identifies "
                "where the applicable licence or permission "
                "terms can be found, this criterion passes."
            ),
        )

        return (
            True,
            rationale,
        )

    # --------------------------------------------------------
    # No licence terms URL
    # --------------------------------------------------------

    source_reference = (
        _explicit_source_reference(
            evidence
        )
    )

    if source_reference:
        return (
            False,
            (
                "No URL or hyperlink explicitly associated "
                "with the applicable licence terms was "
                "identified. The student supplied "
                f"'{source_reference}' as the image "
                "source/reference, but this identifies where "
                "the image was obtained rather than where the "
                "applicable licence terms can be found. "
                "Therefore this criterion fails."
            ),
        )

    return (
        False,
        (
            "No URL or hyperlink identifying the location of "
            "the applicable licence terms was supplied in the "
            "webpage evidence. The technical image URL is not "
            "treated as a licence-terms URL. Therefore this "
            "criterion fails."
        ),
    )


# ============================================================
# APPLY EVIDENCE CONSISTENCY RULES
# ============================================================


def _apply_consistency_rules(
    assessment: LlmImageAssessment,
    evidence: AttributionEvidence,
) -> LlmImageAssessment:
    """
    Apply evidence consistency rules after the LLM response.

    Explicit structured evidence extracted from the webpage
    cannot be lost because Ollama omitted a criterion or
    returned an inconsistent boolean.
    """

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

    # --------------------------------------------------------
    # Copyright owner
    # --------------------------------------------------------

    (
        owner_passed,
        owner_rationale,
    ) = _owner_consistency(
        evidence
    )

    owner.passed = (
        owner_passed
    )

    owner.rationale = (
        owner_rationale
    )

    # --------------------------------------------------------
    # Licence / permission
    # --------------------------------------------------------

    (
        licence_passed,
        licence_rationale,
    ) = _licence_consistency(
        evidence
    )

    licence.passed = (
        licence_passed
    )

    licence.rationale = (
        licence_rationale
    )

    # --------------------------------------------------------
    # Licence terms location
    # --------------------------------------------------------

    (
        terms_passed,
        terms_rationale,
    ) = _terms_consistency(
        evidence
    )

    terms.passed = (
        terms_passed
    )

    terms.rationale = (
        terms_rationale
    )

    # --------------------------------------------------------
    # Self-authorship requires manual review
    # --------------------------------------------------------

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


# ============================================================
# FINAL CLASSIFICATION
# ============================================================


def _apply_classification(
    assessment: LlmImageAssessment,
) -> LlmImageAssessment:
    """
    Calculate the final AI classification from the corrected
    three criteria.
    """

    passed_criteria = [
        criterion
        for criterion
        in assessment.criteria
        if criterion.passed
    ]

    failed_criteria = [
        criterion
        for criterion
        in assessment.criteria
        if not criterion.passed
    ]

    passed_count = len(
        passed_criteria
    )

    # --------------------------------------------------------
    # Fully compliant
    # --------------------------------------------------------

    if passed_count == 3:
        assessment.overall_label = (
            "Fully Compliant"
        )

        assessment.explanation = (
            "All three required copyright and licence "
            "criteria pass. The supplied webpage evidence "
            "provides an acceptable copyright reference, "
            "a licence or permission basis, and the required "
            "licence-terms location where applicable."
        )

        return assessment

    # --------------------------------------------------------
    # Partially compliant
    # --------------------------------------------------------

    if passed_count > 0:
        assessment.overall_label = (
            "Partially Compliant"
        )

        failed_names = [
            criterion.criterion
            for criterion
            in failed_criteria
        ]

        if len(
            failed_names
        ) == 1:
            assessment.explanation = (
                f"{passed_count} of the three required "
                "copyright and licence criteria pass. "
                "The remaining failed requirement is "
                f"'{failed_names[0]}'."
            )

        else:
            failed_text = ", ".join(
                failed_names
            )

            assessment.explanation = (
                f"{passed_count} of the three required "
                "copyright and licence criteria pass. "
                "The remaining failed requirements are: "
                f"{failed_text}."
            )

        return assessment

    # --------------------------------------------------------
    # Non-compliant
    # --------------------------------------------------------

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
    """
    Keep manual-review behaviour consistent.

    Failed criteria alone do not require manual review.
    """

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

    if (
        assessment.manual_review_required
        and not _has_text(
            assessment.manual_review_reason
        )
    ):
        assessment.manual_review_reason = (
            "The supplied copyright or licence information "
            "cannot be interpreted reliably through automated "
            "assessment and requires human review."
        )

    if not assessment.manual_review_required:
        assessment.manual_review_reason = (
            None
        )

    return assessment


# ============================================================
# MAIN LLM ASSESSMENT
# ============================================================


def assess_image_with_llm(
    evidence: AttributionEvidence,
    intended_use: str,
    model: str = DEFAULT_MODEL,
    timeout_seconds: int = 600,
) -> LlmImageAssessment:
    """
    Send one image's extracted evidence to Ollama and return
    the validated three-criterion AI assessment.
    """

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

    # ========================================================
    # CALL OLLAMA
    # ========================================================

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

    # ========================================================
    # READ OLLAMA RESPONSE
    # ========================================================

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

    # ========================================================
    # FORCE CORRECT IMAGE IDENTIFIER
    # ========================================================

    generated_json[
        "image_src"
    ] = evidence.image.src

    # ========================================================
    # VALIDATE RESPONSE
    # ========================================================

    try:
        assessment = (
            LlmImageAssessment.model_validate(
                generated_json
            )
        )

    except ValidationError as error:
        raise LlmReasoningError(
            "The LLM response did not match the "
            "required schema."
        ) from error

    # ========================================================
    # GUARANTEE EXACTLY THREE CRITERIA
    # ========================================================

    assessment = (
        _normalise_criteria(
            assessment
        )
    )

    # ========================================================
    # APPLY EXTRACTED EVIDENCE
    # ========================================================

    assessment = (
        _apply_consistency_rules(
            assessment=assessment,
            evidence=evidence,
        )
    )

    # ========================================================
    # RECALCULATE CLASSIFICATION
    # ========================================================

    assessment = (
        _apply_classification(
            assessment
        )
    )

    # ========================================================
    # MANUAL REVIEW
    # ========================================================

    assessment = (
        _apply_manual_review(
            assessment=assessment,
            evidence=evidence,
        )
    )

    return assessment