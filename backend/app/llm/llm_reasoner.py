import json

import requests
from pydantic import ValidationError

from app.models.schemas import (
    AttributionEvidence,
    LlmImageAssessment,
)


OLLAMA_GENERATE_URL = (
    "http://localhost:11434/api/generate"
)

DEFAULT_MODEL = "llama3:8b"


class LlmReasoningError(Exception):
    """
    Raised when the local LLM cannot produce a valid,
    structured assessment.
    """


def _build_prompt(
    evidence: AttributionEvidence,
    intended_use: str,
) -> str:
    """
    Build a constrained prompt for assessing one image.
    """

    return f"""
You are assessing copyright attribution and licence compliance
for an image used in a student webpage.

Evaluate only the evidence supplied below.

Do not invent facts or claim that unavailable information has
been verified.

Do not infer a creator, licence, or permission merely from the
image host, image URL, domain name, filename, or intended use.

If the evidence is incomplete, ambiguous, contradictory, or
insufficient, clearly state this and require manual review where
appropriate.

IMAGE EVIDENCE

Image source:
{evidence.image.src}

Alt text:
{evidence.image.alt or "Not provided"}

Title:
{evidence.image.title or "Not provided"}

Caption:
{evidence.caption or "Not provided"}

Nearby text:
{evidence.nearby_text or "Not provided"}

Detected possible author:
{evidence.possible_author or "Not detected"}

Detected licence:
{evidence.licence_name or "Not detected"}

Detected licence URL:
{evidence.licence_url or "Not detected"}

Declared intended use:
{intended_use}

IMPORTANT INTERPRETATION RULES

EXTERNAL KNOWLEDGE

Do not use general knowledge to fill in missing copyright or
licence information.

For example:

- an image hosted on images.unsplash.com does not mean that the
  webpage has identified the photographer;

- an image hosted on images.unsplash.com does not mean that the
  webpage has identified the Unsplash License;

- an image hosted on images.pexels.com does not mean that the
  webpage has identified the photographer or Pexels License;

- a source-domain reference such as "from unsplash.com" is not
  the same as identifying the creator or applicable licence.

Evaluate only the evidence explicitly supplied by the webpage.

ATTRIBUTION COMPLETENESS

For "Attribution completeness":

- the creator or copyright owner must be identified;
- the applicable licence or permission basis must be identified;
- both requirements must pass before attribution completeness
  can pass;
- a source website alone is not sufficient;
- intended use alone is not sufficient;
- missing alt text or HTML title must not, by itself, cause this
  criterion to fail;
- alt text and title only count when they contain explicit creator,
  source, licence, or permission information.

USAGE LIMITS

For "Usage limits checked":

- an applicable licence or permission basis must first be identified;
- if no applicable licence is identified, this criterion must fail;
- do not assume that educational use is permitted merely because the
  use is non-commercial or academic;
- do not rely on the image host or domain name as proof of permission.

LICENCE CONDITIONS

For "Licence conditions understood":

- an applicable licence must first be identified;
- if no applicable licence is identified, this criterion must fail;
- merely naming a website or source is not enough;
- merely naming a licence is not enough unless the supplied text also
  explains permission, conditions, or why the intended use is allowed.

SELF-AUTHORED IMAGES

If the evidence explicitly indicates that the page author created,
photographed, or owns the image:

- treat the creator as identified;
- do not require a third-party licence;
- treat the ownership claim as the permission basis;
- do not require an external licence URL;
- set manual_review_required to true when the ownership claim cannot
  be independently verified from the supplied evidence.

KNOWN PLATFORM LICENCES

Recognise these as valid licence names when they are explicitly
present in the supplied webpage evidence:

- Pexels License
- Unsplash License
- Pixabay Content License

Do not infer these licences merely from the image URL or host.

ASSESSMENT CRITERIA

Assess all six criteria:

1. Copyright owner identified

Pass only when the creator, photographer, author, copyright owner,
or equivalent rights holder is explicitly identified in the supplied
evidence.

2. Licence identified

Pass only when a recognised licence, ownership claim, permission
statement, or other applicable permission basis is explicitly
identified in the supplied evidence.

3. Licence URL provided

Pass only when a direct licence URL or relevant permission page is
explicitly supplied in the evidence.

For a clearly self-authored image, an external licence URL is not
required.

4. Attribution completeness

Pass only when both:

- the creator or copyright owner is identified; and
- the applicable licence or permission basis is identified.

Do not pass this criterion when either of those two requirements fails.

5. Licence conditions understood

Pass only when the supplied text demonstrates an understanding of
the applicable licence conditions, permission, or permitted use.

Do not pass this criterion when no applicable licence or permission
basis has been identified.

6. Usage limits checked

Pass only when an applicable licence or permission basis has been
identified and the declared intended use does not conflict with it.

Do not pass this criterion when no applicable licence or permission
basis has been identified.

For every criterion, return:

- the criterion name exactly as written below;
- do not add numbers, bullets, prefixes, suffixes, punctuation,
  or alternative wording;
- use the criterion text verbatim;
- return passed as true or false;
- provide a clear rationale based only on the supplied evidence.

The only permitted criterion names are exactly:

Copyright owner identified
Licence identified
Licence URL provided
Attribution completeness
Licence conditions understood
Usage limits checked

If a criterion cannot be assessed, still return the exact criterion
name above, set passed to false, and provide an appropriate rationale.

OVERALL CLASSIFICATION

Classify the image as exactly one of:

- Fully Compliant
- Partially Compliant
- Non-Compliant

Use these principles:

Fully Compliant:
All six criteria pass and no licence-use conflict is detected.

Partially Compliant:
The creator and licence or permission basis are identified, but one
or more non-critical requirements are incomplete or ambiguous.

Non-Compliant:
The creator is not identified, the applicable licence or permission
basis is not identified, or the declared use clearly conflicts with
the applicable restrictions.

MANUAL REVIEW

Set manual_review_required to true when:

- the evidence is contradictory;
- an ownership claim cannot be independently verified;
- the licence is unclear or unsupported;
- the rule cannot be determined reliably from the available text;
- a legal or factual conclusion would require external evidence.

The explanation field must contain a concise overall explanation
of the final classification and must not be empty.

Do not return a confidence score.

Return only JSON matching the supplied schema.
""".strip()


def _criterion_map(
    assessment: LlmImageAssessment,
) -> dict[str, object]:
    """
    Return the assessment criteria indexed by exact criterion name.
    """

    return {
        criterion.criterion: criterion
        for criterion in assessment.criteria
    }


def _apply_logical_consistency_rules(
    assessment: LlmImageAssessment,
) -> LlmImageAssessment:
    """
    Enforce deterministic consistency between related LLM criteria.

    The model provides contextual reasoning, while these rules prevent
    impossible combinations such as attribution completeness passing
    when the creator or licence was not identified.
    """

    criteria = _criterion_map(
        assessment
    )

    owner = criteria.get(
        "Copyright owner identified"
    )

    licence = criteria.get(
        "Licence identified"
    )

    licence_url = criteria.get(
        "Licence URL provided"
    )

    attribution = criteria.get(
        "Attribution completeness"
    )

    conditions = criteria.get(
        "Licence conditions understood"
    )

    usage = criteria.get(
        "Usage limits checked"
    )

    owner_passed = bool(
        owner is not None
        and owner.passed
    )

    licence_passed = bool(
        licence is not None
        and licence.passed
    )

    licence_url_passed = bool(
        licence_url is not None
        and licence_url.passed
    )

    if attribution is not None:
        attribution.passed = (
            owner_passed
            and licence_passed
        )

        if not attribution.passed:
            attribution.rationale = (
                "Attribution completeness cannot pass because "
                "the supplied evidence does not identify both "
                "the creator or copyright owner and an applicable "
                "licence or permission basis."
            )

    if conditions is not None:
        if not licence_passed:
            conditions.passed = False
            conditions.rationale = (
                "Licence conditions cannot be confirmed because "
                "no applicable licence or permission basis was "
                "identified in the supplied webpage evidence."
            )

    if usage is not None:
        if not licence_passed:
            usage.passed = False
            usage.rationale = (
                "Usage limits cannot be confirmed because no "
                "applicable licence or permission basis was "
                "identified in the supplied webpage evidence."
            )

    passed_count = sum(
        criterion.passed
        for criterion in assessment.criteria
    )

    if (
        not owner_passed
        or not licence_passed
    ):
        assessment.overall_label = (
            "Non-Compliant"
        )

        assessment.explanation = (
            "The image is non-compliant because the supplied "
            "webpage evidence does not identify both the creator "
            "or copyright owner and an applicable licence or "
            "permission basis."
        )

    elif (
        passed_count
        == len(assessment.criteria)
    ):
        assessment.overall_label = (
            "Fully Compliant"
        )

    else:
        assessment.overall_label = (
            "Partially Compliant"
        )

    if (
        not licence_url_passed
        and licence_passed
        and assessment.overall_label
        == "Fully Compliant"
    ):
        assessment.overall_label = (
            "Partially Compliant"
        )

    return assessment


def assess_image_with_llm(
    evidence: AttributionEvidence,
    intended_use: str,
    model: str = DEFAULT_MODEL,
    timeout_seconds: int = 600,
) -> LlmImageAssessment:
    """
    Send image evidence to Ollama and validate the structured result.

    Args:
        evidence:
            Extracted attribution and licence evidence for one image.

        intended_use:
            The declared purpose for which the image is being used.

        model:
            Name of the locally installed Ollama model.

        timeout_seconds:
            Maximum time allowed for the local model to respond.

    Returns:
        A validated and logically consistent LlmImageAssessment.

    Raises:
        LlmReasoningError:
            If Ollama cannot be contacted, returns invalid JSON,
            or returns content that does not match the schema.
    """

    schema = (
        LlmImageAssessment.model_json_schema()
    )

    payload = {
        "model": model,
        "prompt": _build_prompt(
            evidence,
            intended_use,
        ),
        "format": schema,
        "stream": False,
        "keep_alive": "10m",
        "options": {
            "temperature": 0,
            "seed": 42,
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
            f"Ollama request failed: {error}"
        ) from error

    try:
        response_data = response.json()

        generated_text = (
            response_data["response"]
        )

        generated_json = json.loads(
            generated_text
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
            "The LLM response did not match the required schema."
        ) from error

    return _apply_logical_consistency_rules(
        assessment
    )