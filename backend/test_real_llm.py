from app.llm.llm_reasoner import assess_image_with_llm
from app.models.schemas import AttributionEvidence, ImageRecord


evidence = AttributionEvidence(
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


result = assess_image_with_llm(
    evidence,
    intended_use="educational coursework",
)


print(result.model_dump_json(indent=2))