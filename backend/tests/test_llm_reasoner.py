import json

import pytest
import requests

from app.llm.llm_reasoner import (
    LlmReasoningError,
    assess_image_with_llm,
)
from app.models.schemas import (
    AttributionEvidence,
    ImageRecord,
)


class FakeResponse:
    """
    Fake HTTP response used to test the LLM module without
    calling the real local model.
    """

    def __init__(
        self,
        response_body: dict,
        status_error: Exception | None = None,
    ):
        self.response_body = response_body
        self.status_error = status_error

    def raise_for_status(self):
        if self.status_error:
            raise self.status_error

    def json(self):
        return self.response_body


def _sample_evidence() -> AttributionEvidence:
    """
    Create controlled evidence for LLM unit testing.
    """

    return AttributionEvidence(
        image=ImageRecord(
            src="cat.jpg",
            alt="Cat photograph",
        ),
        nearby_text=(
            "Photo by Jane Smith. "
            "Licensed under CC BY 4.0. "
            "This licence permits educational use "
            "when attribution is provided."
        ),
        caption=(
            "Photo by Jane Smith. "
            "Licensed under CC BY 4.0."
        ),
        licence_name="CC BY 4.0",
        licence_url=(
            "https://creativecommons.org/"
            "licenses/by/4.0/"
        ),
        possible_author="Jane Smith",
    )


def test_llm_reasoner_returns_validated_assessment(
    monkeypatch,
):
    """
    Confirm that a valid structured response is accepted.
    """

    model_output = {
        "image_src": "ignored-by-module",
        "overall_label": "Fully Compliant",
        "criteria": [
            {
                "criterion": (
                    "Copyright owner identified"
                ),
                "passed": True,
                "rationale": (
                    "Jane Smith is explicitly identified "
                    "as the photographer."
                ),
            },
            {
                "criterion": "Licence identified",
                "passed": True,
                "rationale": (
                    "CC BY 4.0 is explicitly stated."
                ),
            },
            {
                "criterion": "Licence URL provided",
                "passed": True,
                "rationale": (
                    "A direct Creative Commons licence "
                    "URL is provided."
                ),
            },
            {
                "criterion": "Attribution completeness",
                "passed": True,
                "rationale": (
                    "The creator and licence are both stated."
                ),
            },
            {
                "criterion": (
                    "Licence conditions understood"
                ),
                "passed": True,
                "rationale": (
                    "The text explains that educational use "
                    "is permitted when attribution is provided."
                ),
            },
            {
                "criterion": "Usage limits checked",
                "passed": True,
                "rationale": (
                    "The educational use does not conflict "
                    "with CC BY 4.0."
                ),
            },
        ],
        "explanation": (
            "The creator, licence, licence URL, and permitted "
            "educational use are clearly stated."
        ),
        "manual_review_required": False,
    }

    def fake_post(*args, **kwargs):
        return FakeResponse(
            {
                "response": json.dumps(
                    model_output
                )
            }
        )

    monkeypatch.setattr(
        requests,
        "post",
        fake_post,
    )

    result = assess_image_with_llm(
        _sample_evidence(),
        intended_use="educational coursework",
    )

    assert result.image_src == "cat.jpg"

    assert result.overall_label == (
        "Fully Compliant"
    )

    assert len(result.criteria) == 6

    assert (
        result.manual_review_required
        is False
    )

    assert result.explanation


def test_llm_reasoner_rejects_invalid_model_json(
    monkeypatch,
):
    """
    Confirm that ordinary text instead of JSON is rejected.
    """

    def fake_post(*args, **kwargs):
        return FakeResponse(
            {
                "response": "This is not JSON"
            }
        )

    monkeypatch.setattr(
        requests,
        "post",
        fake_post,
    )

    with pytest.raises(
        LlmReasoningError,
        match="invalid JSON response",
    ):
        assess_image_with_llm(
            _sample_evidence(),
            intended_use="educational coursework",
        )


def test_llm_reasoner_rejects_empty_explanation(
    monkeypatch,
):
    """
    Confirm that the overall explanation cannot be empty.
    """

    model_output = {
        "image_src": "cat.jpg",
        "overall_label": "Fully Compliant",
        "criteria": [
            {
                "criterion": (
                    "Copyright owner identified"
                ),
                "passed": True,
                "rationale": (
                    "Jane Smith is identified."
                ),
            }
        ],
        "explanation": "",
        "manual_review_required": False,
    }

    def fake_post(*args, **kwargs):
        return FakeResponse(
            {
                "response": json.dumps(
                    model_output
                )
            }
        )

    monkeypatch.setattr(
        requests,
        "post",
        fake_post,
    )

    with pytest.raises(
        LlmReasoningError,
        match="did not match the required schema",
    ):
        assess_image_with_llm(
            _sample_evidence(),
            intended_use="educational coursework",
        )