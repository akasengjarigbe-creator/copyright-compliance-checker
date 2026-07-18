from app.models.schemas import ImageRecord, AttributionEvidence
from app.rule_engine.rule_checker import assess_images

def test_rule_engine_scores_compliant_image():
    evidence = AttributionEvidence(
        image=ImageRecord(src="cat.jpg", alt="Cat"),
        nearby_text="Photo by Jane Smith. Licensed under CC BY 4.0. This permits educational use.",
        licence_name="CC BY 4.0",
        licence_url="https://creativecommons.org/licenses/by/4.0/",
        possible_author="Jane Smith"
    )

    result = assess_images([evidence])[0]

    assert result.total_score >= 80
    assert result.label == "Fully Compliant"

def test_rule_engine_classifies_missing_attribution_as_non_compliant():
    evidence = AttributionEvidence(
        image=ImageRecord(
            src="cat.jpg",
            alt="Cat photograph"
        ),
        nearby_text="",
        licence_name=None,
        licence_url=None,
        possible_author=None
    )

    result = assess_images([evidence])[0]

    assert result.total_score == 0
    assert result.label == "Non-Compliant"
    assert len(result.recommendations) == 6

def test_rule_engine_classifies_incomplete_evidence_as_partially_compliant():
    evidence = AttributionEvidence(
        image=ImageRecord(
            src="cat.jpg",
            alt="Cat photograph"
        ),
        nearby_text="Photo by Jane Smith. Licensed under CC BY 4.0.",
        licence_name="CC BY 4.0",
        licence_url=None,
        possible_author="Jane Smith"
    )

    result = assess_images([evidence])[0]

    assert result.label == "Partially Compliant"
    assert 50 <= result.total_score < 80

def test_rule_engine_flags_cc_by_nc_for_commercial_use():
    evidence = AttributionEvidence(
        image=ImageRecord(
            src="cat.jpg",
            alt="Cat photograph"
        ),
        nearby_text=(
            "Photo by Jane Smith. Licensed under CC BY-NC 4.0. "
            "The licence requires attribution."
        ),
        licence_name="CC BY-NC 4.0",
        licence_url="https://creativecommons.org/licenses/by-nc/4.0/",
        possible_author="Jane Smith"
    )

    result = assess_images(
        [evidence],
        intended_use="commercial use"
    )[0]

    usage_result = next(
        criterion
        for criterion in result.criteria
        if criterion.criterion == "Usage limits checked"
    )

    assert usage_result.passed is False
    assert usage_result.score == 0
    assert result.label != "Fully Compliant"

def test_rule_engine_allows_cc_by_nc_for_non_commercial_use():
    evidence = AttributionEvidence(
        image=ImageRecord(
            src="cat.jpg",
            alt="Cat photograph"
        ),
        nearby_text=(
            "Photo by Jane Smith. Licensed under CC BY-NC 4.0. "
            "The image is used for non-commercial educational coursework."
        ),
        licence_name="CC BY-NC 4.0",
        licence_url="https://creativecommons.org/licenses/by-nc/4.0/",
        possible_author="Jane Smith"
    )

    result = assess_images(
        [evidence],
        intended_use="non-commercial educational coursework"
    )[0]

    usage_result = next(
        criterion
        for criterion in result.criteria
        if criterion.criterion == "Usage limits checked"
    )

    assert usage_result.passed is True
    assert usage_result.score == 15

def test_rule_engine_flags_cc_by_nd_for_modified_use():
    evidence = AttributionEvidence(
        image=ImageRecord(
            src="cat.jpg",
            alt="Cat photograph"
        ),
        nearby_text=(
            "Photo by Jane Smith. Licensed under CC BY-ND 4.0. "
            "The image has been cropped and modified for the webpage."
        ),
        licence_name="CC BY-ND 4.0",
        licence_url="https://creativecommons.org/licenses/by-nd/4.0/",
        possible_author="Jane Smith"
    )

    result = assess_images(
        [evidence],
        intended_use="modified image used in educational coursework"
    )[0]

    usage_result = next(
        criterion
        for criterion in result.criteria
        if criterion.criterion == "Usage limits checked"
    )

    assert usage_result.passed is False
    assert usage_result.score == 0
    assert result.label != "Fully Compliant"

def test_rule_engine_allows_cc_by_nd_for_unchanged_use():
    evidence = AttributionEvidence(
        image=ImageRecord(
            src="cat.jpg",
            alt="Cat photograph"
        ),
        nearby_text=(
            "Photo by Jane Smith. Licensed under CC BY-ND 4.0. "
            "The image is displayed unchanged for educational coursework."
        ),
        licence_name="CC BY-ND 4.0",
        licence_url="https://creativecommons.org/licenses/by-nd/4.0/",
        possible_author="Jane Smith"
    )

    result = assess_images(
        [evidence],
        intended_use="unchanged image used in educational coursework"
    )[0]

    usage_result = next(
        criterion
        for criterion in result.criteria
        if criterion.criterion == "Usage limits checked"
    )

    assert usage_result.passed is True
    assert usage_result.score == 15

def test_rule_engine_flags_cc_by_nc_nd_for_commercial_modified_use():
    evidence = AttributionEvidence(
        image=ImageRecord(
            src="cat.jpg",
            alt="Cat photograph"
        ),
        nearby_text=(
            "Photo by Jane Smith. Licensed under CC BY-NC-ND 4.0. "
            "The image has been modified and used commercially."
        ),
        licence_name="CC BY-NC-ND 4.0",
        licence_url="https://creativecommons.org/licenses/by-nc-nd/4.0/",
        possible_author="Jane Smith"
    )

    result = assess_images(
        [evidence],
        intended_use="commercial use of a modified image"
    )[0]

    usage_result = next(
        criterion
        for criterion in result.criteria
        if criterion.criterion == "Usage limits checked"
    )

    assert usage_result.passed is False
    assert usage_result.score == 0
    assert result.label != "Fully Compliant"

def test_rule_engine_flags_cc_by_sa_modified_without_share_alike():
    evidence = AttributionEvidence(
        image=ImageRecord(
            src="cat.jpg",
            alt="Cat photograph"
        ),
        nearby_text=(
            "Photo by Jane Smith. Licensed under CC BY-SA 4.0. "
            "The image has been modified for the webpage."
        ),
        licence_name="CC BY-SA 4.0",
        licence_url="https://creativecommons.org/licenses/by-sa/4.0/",
        possible_author="Jane Smith"
    )

    result = assess_images(
        [evidence],
        intended_use=(
            "modified image distributed without a ShareAlike licence"
        )
    )[0]

    usage_result = next(
        criterion
        for criterion in result.criteria
        if criterion.criterion == "Usage limits checked"
    )

    assert usage_result.passed is False
    assert usage_result.score == 0
    assert result.label != "Fully Compliant"

def test_rule_engine_allows_cc_by_sa_with_share_alike_licence():
    evidence = AttributionEvidence(
        image=ImageRecord(
            src="cat.jpg",
            alt="Cat photograph"
        ),
        nearby_text=(
            "Photo by Jane Smith. Licensed under CC BY-SA 4.0. "
            "The modified version is shared under CC BY-SA 4.0."
        ),
        licence_name="CC BY-SA 4.0",
        licence_url="https://creativecommons.org/licenses/by-sa/4.0/",
        possible_author="Jane Smith"
    )

    result = assess_images(
        [evidence],
        intended_use=(
            "modified image shared under a compatible "
            "CC BY-SA 4.0 licence"
        )
    )[0]

    usage_result = next(
        criterion
        for criterion in result.criteria
        if criterion.criterion == "Usage limits checked"
    )

    assert usage_result.passed is True
    assert usage_result.score == 15

def test_rule_engine_provides_specific_missing_evidence_recommendations():
    evidence = AttributionEvidence(
        image=ImageRecord(
            src="cat.jpg",
            alt="Cat photograph"
        ),
        nearby_text="",
        licence_name=None,
        licence_url=None,
        possible_author=None
    )

    result = assess_images([evidence])[0]

    assert (
        "Identify the image creator, photographer, author, "
        "or copyright holder."
        in result.recommendations
    )

    assert (
        "State the licence name or provide a clear permission "
        "statement for the image."
        in result.recommendations
    )

    assert (
        "Add a direct link to the licence terms or the relevant "
        "source permission page."
        in result.recommendations
    )


def test_rule_engine_reports_specific_commercial_use_conflict():
    evidence = AttributionEvidence(
        image=ImageRecord(
            src="cat.jpg",
            alt="Cat photograph"
        ),
        nearby_text=(
            "Photo by Jane Smith. Licensed under CC BY-NC 4.0. "
            "The licence requires attribution."
        ),
        licence_name="CC BY-NC 4.0",
        licence_url=(
            "https://creativecommons.org/licenses/by-nc/4.0/"
        ),
        possible_author="Jane Smith"
    )

    result = assess_images(
        [evidence],
        intended_use="commercial use"
    )[0]

    assert any(
        "does not permit the declared commercial use"
        in recommendation
        for recommendation in result.recommendations
    )