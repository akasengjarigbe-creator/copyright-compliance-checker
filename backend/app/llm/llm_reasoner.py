import json
import time
from typing import Optional

import requests
from pydantic import ValidationError

from app.models.schemas import (
    AttributionEvidence,
    LlmCriterionAssessment,
    LlmImageAssessment,
)


OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"

# A small local model is used to keep CPU inference practical.
DEFAULT_MODEL = "llama3:8b"

SELF_AUTHORED_LICENCE = "Self-authored claim"

CRITERION_OWNER = "Copyright owner identified"
CRITERION_LICENCE = "Licence identified"
CRITERION_LICENCE_URL = "Licence URL provided"
CRITERION_ATTRIBUTION = "Attribution completeness"

REQUIRED_CRITERIA = (
    CRITERION_OWNER,
    CRITERION_LICENCE,
    CRITERION_LICENCE_URL,
    CRITERION_ATTRIBUTION,
)

HOSTING_PLATFORMS = {
    "wikimedia",
    "wikipedia",
    "wikimedia commons",
    "commons.wikimedia",
    "flickr",
    "unsplash",
    "pixabay",
    "pexels",
    "google images",
    "bing images",
    "facebook",
    "instagram",
    "twitter",
    "x.com",
    "imgur",
    "wordpress",
    "blogspot",
}

SELF_AUTHORSHIP_REVIEW_REASON = (
    "The image is declared as self-authored. The attribution information "
    "is sufficient for automated assessment, but the system cannot "
    "independently verify that the named person created the image or owns "
    "the copyright."
)

MISSING_CRITERIA_REVIEW_REASON = (
    "The AI response did not contain all four required assessment criteria. "
    "Manual review is recommended because the automated AI assessment is "
    "incomplete."
)

DEFAULT_MANUAL_REVIEW_REASON = (
    "The supplied webpage evidence is ambiguous, contradictory, or "
    "insufficiently clear for the AI assessment to be accepted without "
    "human verification."
)


class LlmReasoningError(Exception):
    """
    Raised when Ollama cannot produce a valid structured assessment.
    """


def _has_text(
    value: Optional[str],
) -> bool:
    """
    Return True when a value contains meaningful non-whitespace text.
    """

    return bool(
        value
        and value.strip()
    )


def _normalise_text(
    value: Optional[str],
) -> str:
    """
    Return a case-insensitive, whitespace-normalised representation.
    """

    if not value:
        return ""

    return " ".join(
        value.casefold().split()
    )


def _is_self_authored(
    evidence: AttributionEvidence,
) -> bool:
    """
    Return True when the deterministic extractor detected the recognised
    self-authorship permission basis.
    """

    return (
        _normalise_text(evidence.licence_name)
        == _normalise_text(SELF_AUTHORED_LICENCE)
    )


def _matches_hosting_platform(
    value: Optional[str],
) -> bool:
    """
    Return True when a value is only the name of a known repository,
    search engine, social platform, or image-hosting website.

    The check is intentionally conservative. It does not reject a genuine
    organisation merely because its name appears alongside a platform.
    """

    text = _normalise_text(value)

    if not text:
        return False

    stripped_text = (
        text.replace("https://", "")
        .replace("http://", "")
        .replace("www.", "")
        .strip(" /")
    )

    for platform in HOSTING_PLATFORMS:
        normalised_platform = _normalise_text(platform)

        if stripped_text == normalised_platform:
            return True

        if stripped_text == f"{normalised_platform}.com":
            return True

        if stripped_text == f"{normalised_platform}.org":
            return True

    return False


def _rationale_uses_host_as_owner(
    rationale: Optional[str],
) -> bool:
    """
    Detect clear cases where an AI rationale treats a hosting platform
    itself as the copyright owner.

    This is a fallback check. The extracted possible_author field remains
    the stronger deterministic signal.
    """

    text = _normalise_text(rationale)

    if not text:
        return False

    ownership_phrases = (
        "identified as the owner",
        "identified as copyright owner",
        "is the copyright owner",
        "is identified as the copyright owner",
        "owns the copyright",
        "named as the owner",
        "named as copyright owner",
        "listed as the owner",
        "listed as copyright owner",
    )

    for platform in HOSTING_PLATFORMS:
        normalised_platform = _normalise_text(platform)

        if normalised_platform not in text:
            continue

        if any(
            phrase in text
            for phrase in ownership_phrases
        ):
            return True

    return False


def _build_prompt(
    evidence: AttributionEvidence,
    intended_use: str,
) -> str:
    """
    Build the Ollama prompt for the four required copyright criteria.

    The prompt uses the same policy as the deterministic rule engine,
    including the self-authorship exception.
    """

    self_authorship_section = ""

    if _is_self_authored(evidence):
        self_authorship_section = f"""
SPECIAL CASE: SELF-AUTHORED IMAGE

The deterministic evidence extractor identified the licence or permission
basis as "{SELF_AUTHORED_LICENCE}".

Apply these rules:

- Pass "{CRITERION_OWNER}" only when a named possible author is present.
- Pass "{CRITERION_LICENCE}" because an explicit self-authorship statement
  is treated as the permission basis.
- Pass "{CRITERION_LICENCE_URL}" because a separate licence URL is not
  applicable to a declared self-authored image.
- Pass "{CRITERION_ATTRIBUTION}" when the named possible author and the
  self-authorship claim are both present.
- Return "Fully Compliant" when all four criteria pass.
- Set manual_review_required to true.
- Explain in manual_review_reason that ownership cannot be independently
  verified.
- Do not fail the image merely because licence_url is absent.
""".strip()

    return f"""
You are assessing copyright attribution evidence for one image used in a
student HTML webpage.

Use only the supplied webpage evidence.

Do not infer copyright information from:

- the image host;
- the website name;
- the domain name;
- the image URL;
- the image filename;
- general knowledge;
- the declared intended use.

IMPORTANT OWNER RULE

A repository, image host, search engine, or social platform is not the
copyright owner merely because it stores, displays, or links to an image.

The following must not be treated as copyright owners unless the supplied
evidence explicitly states that the organisation itself created the image
or owns the copyright:

- Wikimedia;
- Wikimedia Commons;
- Wikipedia;
- Flickr;
- Unsplash;
- Pixabay;
- Pexels;
- Google Images;
- Bing Images;
- Facebook;
- Instagram;
- X or Twitter;
- Imgur.

Only pass "{CRITERION_OWNER}" when the evidence explicitly identifies a
creator, photographer, illustrator, author, organisation, company,
copyright holder, or equivalent rights owner.

IMPORTANT LICENCE CONSISTENCY RULE

A licence URL cannot pass unless a licence or permission basis has also
been identified.

If "{CRITERION_LICENCE}" fails, then
"{CRITERION_LICENCE_URL}" must also fail.

IMAGE EVIDENCE

Image source:
{evidence.image.src}

Alt text:
{evidence.image.alt or "Not provided"}

Title attribute:
{evidence.image.title or "Not provided"}

Caption:
{evidence.caption or "Not provided"}

Nearby text:
{evidence.nearby_text or "Not provided"}

Detected possible copyright owner:
{evidence.possible_author or "Not detected"}

Detected licence or permission basis:
{evidence.licence_name or "Not detected"}

Detected licence URL:
{evidence.licence_url or "Not detected"}

Declared intended use:
{intended_use}

{self_authorship_section}

ASSESSMENT RULES

Assess exactly these four criteria:

1. {CRITERION_OWNER}

Pass only when the creator, photographer, illustrator, author,
organisation, company, copyright holder, or equivalent rights owner is
explicitly identified in the supplied evidence.

Do not treat an image repository, host, website, search engine, profile,
or social platform as the owner merely because the image appears there.

2. {CRITERION_LICENCE}

Pass only when the supplied evidence contains:

- a licence name;
- an explicit licensing statement;
- a clear permission statement; or
- an explicit self-authorship claim.

Do not infer a licence from the website, host, image URL, domain, filename,
or intended use.

3. {CRITERION_LICENCE_URL}

Normally, pass only when a direct link to the applicable licence terms is
explicitly present.

A link to an image file, image page, website homepage, repository,
search-results page, user profile, or unrelated page is not automatically
a licence URL.

If no licence or permission basis is identified, fail this criterion even
when a URL is present.

Exception:

When the detected licence is "{SELF_AUTHORED_LICENCE}", pass this criterion
because a separate licence URL is not applicable.

4. {CRITERION_ATTRIBUTION}

For a normally licensed image, pass only when all three requirements pass:

- copyright owner identified;
- licence identified;
- licence URL provided.

For a self-authored image, pass when:

- the creator is identified; and
- the self-authorship claim is present.

For a self-authored image, a separate licence URL is not required.

Use these criterion names exactly:

- {CRITERION_OWNER}
- {CRITERION_LICENCE}
- {CRITERION_LICENCE_URL}
- {CRITERION_ATTRIBUTION}

For every criterion return:

- criterion;
- passed as true or false;
- a concise rationale based only on the supplied evidence.

OVERALL CLASSIFICATION

Return exactly one overall label:

- Fully Compliant
- Partially Compliant
- Non-Compliant

Fully Compliant:
All four criteria pass.

Partially Compliant:
At least one criterion passes, but fewer than four criteria pass.

Non-Compliant:
None of the four criteria pass.

MANUAL REVIEW

Set manual_review_required to true when:

- the image is declared as self-authored;
- the evidence is ambiguous;
- the evidence is contradictory;
- it is unclear which attribution belongs to the image;
- a detected URL may not be the applicable licence URL;
- the result cannot be determined reliably;
- any required criterion is missing from the response.

When manual_review_required is true:

- manual_review_reason must contain a specific explanation;
- do not use a vague statement such as "needs checking";
- explain exactly what cannot be verified or resolved.

When manual_review_required is false:

- manual_review_reason must be null.

For a self-authored image, explain that the system cannot independently
verify that the named person created the image or owns the copyright.

The explanation field must briefly explain the overall classification.

Do not return a confidence score.

Return only JSON matching the supplied schema.
""".strip()


def _criterion_map(
    assessment: LlmImageAssessment,
) -> dict[str, LlmCriterionAssessment]:
    """
    Index assessment criteria by exact criterion name.

    Duplicate criterion names are reduced to the first occurrence.
    """

    criteria: dict[str, LlmCriterionAssessment] = {}

    for criterion in assessment.criteria:
        if criterion.criterion not in criteria:
            criteria[criterion.criterion] = criterion

    return criteria


def _make_missing_criterion(
    criterion_name: str,
) -> LlmCriterionAssessment:
    """
    Create a failed criterion when the LLM omitted a required result.
    """

    return LlmCriterionAssessment(
        criterion=criterion_name,
        passed=False,
        rationale=(
            "The AI response did not contain a valid assessment for this "
            "required criterion."
        ),
    )


def _normalise_required_criteria(
    assessment: LlmImageAssessment,
) -> tuple[LlmImageAssessment, bool]:
    """
    Ensure that the assessment contains exactly the four required criteria.

    Returns:
        A tuple containing the normalised assessment and a Boolean showing
        whether one or more required criteria were missing.
    """

    criteria = _criterion_map(
        assessment
    )

    missing_criterion = False
    normalised_criteria: list[LlmCriterionAssessment] = []

    for criterion_name in REQUIRED_CRITERIA:
        criterion = criteria.get(
            criterion_name
        )

        if criterion is None:
            missing_criterion = True
            criterion = _make_missing_criterion(
                criterion_name
            )

        normalised_criteria.append(
            criterion
        )

    assessment.criteria = normalised_criteria

    return assessment, missing_criterion


def _format_missing_requirements(
    missing_items: list[str],
) -> str:
    """
    Convert a list of missing requirements into readable prose.
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
        ", ".join(missing_items[:-1])
        + f", and {missing_items[-1]}"
    )


def _set_overall_classification(
    assessment: LlmImageAssessment,
) -> None:
    """
    Recalculate the overall label from the four normalised criteria.

    The language model's original overall label is not trusted.
    """

    passed_count = sum(
        1
        for criterion in assessment.criteria
        if criterion.passed
    )

    if passed_count == len(REQUIRED_CRITERIA):
        assessment.overall_label = "Fully Compliant"
        assessment.explanation = (
            "All four copyright attribution criteria pass. The supplied "
            "evidence identifies the copyright owner, licence or permission "
            "basis, applicable licence URL, and complete attribution."
        )
        return

    if passed_count > 0:
        assessment.overall_label = "Partially Compliant"
        assessment.explanation = (
            f"{passed_count} of the four required copyright attribution "
            "criteria pass. Some relevant information is present, but the "
            "attribution remains incomplete."
        )
        return

    assessment.overall_label = "Non-Compliant"
    assessment.explanation = (
        "None of the four required copyright attribution criteria pass. "
        "The supplied evidence does not establish a complete or usable "
        "copyright attribution."
    )


def _apply_self_authorship_rules(
    assessment: LlmImageAssessment,
    evidence: AttributionEvidence,
    missing_criterion: bool,
) -> LlmImageAssessment:
    """
    Deterministically enforce the agreed self-authorship policy.

    A separate licence URL is not required for a declared self-authored
    image. Manual review is always required because ownership cannot be
    independently verified.
    """

    criteria = _criterion_map(
        assessment
    )

    owner = criteria[CRITERION_OWNER]
    licence = criteria[CRITERION_LICENCE]
    licence_url = criteria[CRITERION_LICENCE_URL]
    attribution = criteria[CRITERION_ATTRIBUTION]

    owner_identified = (
        _has_text(evidence.possible_author)
        and not _matches_hosting_platform(evidence.possible_author)
    )

    owner.passed = owner_identified

    if owner_identified:
        author = evidence.possible_author.strip()

        owner.rationale = (
            f"The webpage evidence identifies '{author}' as the creator "
            "or copyright owner through an explicit self-authorship claim."
        )
    else:
        owner.rationale = (
            "A self-authorship claim was detected, but no valid named "
            "creator or copyright owner was identified."
        )

    licence.passed = True
    licence.rationale = (
        "An explicit self-authorship claim was detected and is treated as "
        "the permission basis for the image."
    )

    licence_url.passed = True
    licence_url.rationale = (
        "A separate licence URL is not applicable because the image is "
        "declared as self-authored."
    )

    attribution.passed = owner_identified

    if owner_identified:
        attribution.rationale = (
            "The attribution identifies the creator and contains an "
            "explicit self-authorship permission basis. A separate licence "
            "URL is not applicable."
        )
    else:
        attribution.rationale = (
            "The attribution is incomplete because the image is declared "
            "as self-authored but no valid named creator is identified."
        )

    assessment.manual_review_required = True

    if missing_criterion:
        assessment.manual_review_reason = (
            f"{SELF_AUTHORSHIP_REVIEW_REASON} "
            f"{MISSING_CRITERIA_REVIEW_REASON}"
        )
    else:
        assessment.manual_review_reason = (
            SELF_AUTHORSHIP_REVIEW_REASON
        )

    _set_overall_classification(
        assessment
    )

    if owner_identified:
        assessment.explanation = (
            "The evidence identifies the image creator and contains an "
            "explicit self-authorship claim. A separate licence URL is not "
            "applicable, so all four automated criteria pass. Manual review "
            "is still required because authorship and ownership cannot be "
            "independently verified."
        )
    else:
        assessment.explanation = (
            "The evidence contains a self-authorship claim, but no valid "
            "named creator or copyright owner is identified. The attribution "
            "is therefore incomplete and requires manual review."
        )

    return assessment


def _apply_standard_consistency_rules(
    assessment: LlmImageAssessment,
    evidence: AttributionEvidence,
    missing_criterion: bool,
) -> LlmImageAssessment:
    """
    Apply deterministic consistency rules to a normally licensed image.

    These rules prevent a small language model from:

    - treating a repository or host as the copyright owner;
    - passing a licence URL when no licence was identified;
    - passing attribution completeness when a prerequisite failed;
    - returning an overall label inconsistent with the four criteria.
    """

    criteria = _criterion_map(
        assessment
    )

    owner = criteria[CRITERION_OWNER]
    licence = criteria[CRITERION_LICENCE]
    licence_url = criteria[CRITERION_LICENCE_URL]
    attribution = criteria[CRITERION_ATTRIBUTION]

    owner_was_corrected = False
    licence_url_was_corrected = False

    possible_author_is_host = (
        _matches_hosting_platform(
            evidence.possible_author
        )
    )

    rationale_treats_host_as_owner = (
        _rationale_uses_host_as_owner(
            owner.rationale
        )
    )

    if (
        owner.passed
        and (
            possible_author_is_host
            or rationale_treats_host_as_owner
        )
    ):
        owner.passed = False
        owner_was_corrected = True
        owner.rationale = (
            "The supplied evidence identifies only an image repository, "
            "hosting platform, search engine, or website rather than an "
            "explicit creator or copyright owner."
        )

    if not licence.passed:
        if licence_url.passed:
            licence_url_was_corrected = True

        licence_url.passed = False
        licence_url.rationale = (
            "No licence or permission basis was identified, so an "
            "applicable licence URL cannot be confirmed."
        )

    attribution.passed = (
        owner.passed
        and licence.passed
        and licence_url.passed
    )

    if attribution.passed:
        attribution.rationale = (
            "The attribution identifies the copyright owner, licence or "
            "permission basis, and applicable licence URL."
        )
    else:
        missing_requirements: list[str] = []

        if not owner.passed:
            missing_requirements.append(
                "the copyright owner"
            )

        if not licence.passed:
            missing_requirements.append(
                "the licence or permission basis"
            )

        if not licence_url.passed:
            missing_requirements.append(
                "the applicable licence URL"
            )

        missing_text = _format_missing_requirements(
            missing_requirements
        )

        attribution.rationale = (
            "The attribution is incomplete because the supplied evidence "
            f"does not establish {missing_text}."
        )

    _set_overall_classification(
        assessment
    )

    review_reasons: list[str] = []

    if _has_text(assessment.manual_review_reason):
        review_reasons.append(
            assessment.manual_review_reason.strip()
        )

    if missing_criterion:
        review_reasons.append(
            MISSING_CRITERIA_REVIEW_REASON
        )

    if owner_was_corrected:
        review_reasons.append(
            "The AI initially treated an image repository or hosting "
            "platform as the copyright owner. The owner criterion was "
            "corrected because no explicit creator or rights holder was "
            "identified."
        )

    if licence_url_was_corrected:
        review_reasons.append(
            "The AI initially passed the licence URL criterion even though "
            "no licence or permission basis was identified. The criterion "
            "was corrected because a URL cannot be validated as a licence "
            "URL without an identified licence."
        )

    owner_and_licence_conflict = (
        owner.passed != licence.passed
    )

    if owner_and_licence_conflict:
        review_reasons.append(
            "The supplied evidence identifies either a copyright owner or "
            "a licence or permission basis, but not both. The partial "
            "copyright information should be manually reviewed."
        )

    if assessment.manual_review_required and not review_reasons:
        review_reasons.append(
            DEFAULT_MANUAL_REVIEW_REASON
        )

    assessment.manual_review_required = bool(
        review_reasons
    )

    if assessment.manual_review_required:
        assessment.manual_review_reason = " ".join(
            dict.fromkeys(review_reasons)
        )
    else:
        assessment.manual_review_reason = None

    return assessment


def _apply_logical_consistency_rules(
    assessment: LlmImageAssessment,
    evidence: AttributionEvidence,
) -> LlmImageAssessment:
    """
    Normalise the criteria and apply the relevant deterministic policy.
    """

    assessment, missing_criterion = (
        _normalise_required_criteria(
            assessment
        )
    )

    if _is_self_authored(
        evidence
    ):
        return _apply_self_authorship_rules(
            assessment=assessment,
            evidence=evidence,
            missing_criterion=missing_criterion,
        )

    return _apply_standard_consistency_rules(
        assessment=assessment,
        evidence=evidence,
        missing_criterion=missing_criterion,
    )


def _parse_ollama_response(
    response: requests.Response,
) -> tuple[dict, dict]:
    """
    Parse the outer Ollama response and the generated JSON assessment.
    """

    try:
        response_data = response.json()

    except ValueError as error:
        raise LlmReasoningError(
            "Ollama returned a response that was not valid JSON."
        ) from error

    generated_text = response_data.get(
        "response"
    )

    if not isinstance(
        generated_text,
        str,
    ):
        raise LlmReasoningError(
            "Ollama did not return generated assessment text."
        )

    try:
        generated_json = json.loads(
            generated_text
        )

    except json.JSONDecodeError as error:
        raise LlmReasoningError(
            "Ollama generated assessment text that was not valid JSON."
        ) from error

    if not isinstance(
        generated_json,
        dict,
    ):
        raise LlmReasoningError(
            "Ollama generated JSON with an unexpected structure."
        )

    return response_data, generated_json


def _print_timing_information(
    response_data: dict,
    model: str,
    elapsed_seconds: float,
) -> None:
    """
    Print useful Ollama timing information for local development.
    """

    nanoseconds_per_second = 1_000_000_000

    print(
        "Ollama model: "
        f"{response_data.get('model', model)}"
    )

    print(
        "Total HTTP assessment time: "
        f"{elapsed_seconds:.2f} seconds"
    )

    print(
        "Ollama load time: "
        f"{response_data.get('load_duration', 0) / nanoseconds_per_second:.2f} "
        "seconds"
    )

    print(
        "Prompt evaluation time: "
        f"{response_data.get('prompt_eval_duration', 0) / nanoseconds_per_second:.2f} "
        "seconds"
    )

    print(
        "Response generation time: "
        f"{response_data.get('eval_duration', 0) / nanoseconds_per_second:.2f} "
        "seconds"
    )

    print(
        "Generated tokens: "
        f"{response_data.get('eval_count', 0)}"
    )


def assess_image_with_llm(
    evidence: AttributionEvidence,
    intended_use: str,
    model: str = DEFAULT_MODEL,
    timeout_seconds: int = 600,
) -> LlmImageAssessment:
    """
    Send one image's evidence to Ollama and validate the result.

    Args:
        evidence:
            Extracted copyright and licence evidence for one image.

        intended_use:
            The declared purpose for which the image is being used.

        model:
            Name of the locally installed Ollama model.

        timeout_seconds:
            Maximum number of seconds allowed for Ollama to respond.

    Returns:
        A validated and logically consistent AI assessment.

    Raises:
        LlmReasoningError:
            If Ollama cannot be contacted, returns invalid JSON, or returns
            data that does not match the required schema.
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
        "keep_alive": -1,
        "options": {
            "temperature": 0,
            "seed": 42,
            "num_ctx": 4096,
            "num_predict": 650,
        },
    }

    print(
        "Sending copyright assessment to Ollama "
        f"using model: {model}"
    )

    request_started = (
        time.perf_counter()
    )

    try:
        response = requests.post(
            OLLAMA_GENERATE_URL,
            json=payload,
            timeout=timeout_seconds,
        )

        response.raise_for_status()

    except requests.Timeout as error:
        raise LlmReasoningError(
            "The Ollama assessment timed out before a response was received."
        ) from error

    except requests.ConnectionError as error:
        raise LlmReasoningError(
            "The application could not connect to Ollama. Confirm that "
            "Ollama is running and that the configured model is installed."
        ) from error

    except requests.RequestException as error:
        raise LlmReasoningError(
            f"The Ollama request failed: {error}"
        ) from error

    elapsed_seconds = (
        time.perf_counter()
        - request_started
    )

    response_data, generated_json = (
        _parse_ollama_response(
            response
        )
    )

    _print_timing_information(
        response_data=response_data,
        model=model,
        elapsed_seconds=elapsed_seconds,
    )

    # The image source is supplied by the application rather than trusted
    # from the language-model response.
    generated_json["image_src"] = (
        evidence.image.src
    )

    try:
        assessment = (
            LlmImageAssessment.model_validate(
                generated_json
            )
        )

    except ValidationError as error:
        raise LlmReasoningError(
            "The LLM response did not match the required assessment schema."
        ) from error

    return _apply_logical_consistency_rules(
        assessment=assessment,
        evidence=evidence,
    )