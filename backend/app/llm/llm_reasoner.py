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

For "Attribution completeness":

- assess whether the creator or copyright owner is identified;
- assess whether the applicable licence is identified;
- assess whether the available attribution contains the required
  creator and licence evidence;
- do not fail this criterion merely because HTML alt text is missing;
- do not fail this criterion merely because an HTML title attribute
  is missing;
- alt text is primarily an accessibility field and is not, by itself,
  copyright attribution evidence;
- an HTML title attribute is not required for attribution completeness;
- only use alt text or title when those fields contain explicit creator,
  source, or licence information.

ASSESSMENT CRITERIA

Assess all six criteria:

1. Copyright owner identified

Pass when the creator, photographer, author, copyright owner,
or equivalent rights holder is explicitly identified.

2. Licence identified

Pass when a recognised licence or clear permission statement
is explicitly identified.

3. Licence URL provided

Pass when a direct licence or source URL is supplied.

4. Attribution completeness

Pass when the supplied attribution evidence identifies the creator
or copyright owner and the applicable licence. Do not require HTML
alt text or an HTML title unless those fields contain relevant
attribution evidence.

5. Licence conditions understood

Pass when the supplied text demonstrates an understanding of the
licence conditions or permitted use.

6. Usage limits checked

Pass when the declared intended use does not conflict with the
detected licence restrictions.

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

Use these general principles:

Fully Compliant:
The available evidence clearly satisfies all important requirements
and no licence-use conflict is detected.

Partially Compliant:
Some requirements are satisfied, but evidence is incomplete,
ambiguous, or requires correction.

Non-Compliant:
Major attribution or licence information is missing, or the
declared use clearly conflicts with the licence.

MANUAL REVIEW

Set manual_review_required to true when:

- the evidence is contradictory;
- an ownership claim cannot be verified;
- the licence is unclear or unsupported;
- the rule cannot be determined reliably from the available text;
- a legal or factual conclusion would require external evidence.

The explanation field must contain a concise overall explanation
of the final classification and must not be empty.

Do not return a confidence score.

Return only JSON matching the supplied schema.
""".strip()


def assess_image_with_llm(
    evidence: AttributionEvidence,
    intended_use: str,
    model: str = DEFAULT_MODEL,
    timeout_seconds: int = 600,
) -> LlmImageAssessment:
    """
    Send evidence to Ollama and validate the structured response.

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
        A validated LlmImageAssessment.

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
        generated_text = response_data["response"]
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

    # The application controls the image source.
    # The model is not allowed to alter or invent it.
    generated_json["image_src"] = (
        evidence.image.src
    )

    try:
        return LlmImageAssessment.model_validate(
            generated_json
        )

    except ValidationError as error:
        raise LlmReasoningError(
            "The LLM response did not match the required schema."
        ) from error