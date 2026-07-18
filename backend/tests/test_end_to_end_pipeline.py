from app.parser.html_parser import parse_html
from app.detector.image_detector import detect_images
from app.extractor.attribution_extractor import extract_attribution_evidence
from app.rule_engine.rule_checker import assess_images
from app.report.report_generator import build_report


def test_complete_pipeline_generates_compliant_report():
    html = """
    <html>
        <body>
            <figure>
                <img src="cat.jpg" alt="Cat photograph">

                <figcaption>
                    Photo by Jane Smith.
                    Licensed under CC BY 4.0.
                </figcaption>
            </figure>

            <p>
                This licence permits use in educational coursework
                provided that attribution is included.
            </p>

            <a href="https://creativecommons.org/licenses/by/4.0/">
                View licence
            </a>
        </body>
    </html>
    """

    parsed = parse_html(
        html,
        base_url="https://example.com/coursework/page.html"
    )

    images = detect_images(parsed)

    evidence = extract_attribution_evidence(
        parsed,
        images
    )

    assessments = assess_images(
        evidence,
        intended_use="educational coursework"
    )

    report = build_report(assessments)

    assert report.total_images == 1
    assert report.overall_score == 100
    assert report.fully_compliant == 1
    assert report.partially_compliant == 0
    assert report.non_compliant == 0

    assert len(report.image_assessments) == 1

    image_result = report.image_assessments[0]

    assert image_result.image_src == (
        "https://example.com/coursework/cat.jpg"
    )

    assert image_result.label == "Fully Compliant"
    assert image_result.total_score == 100
    assert image_result.recommendations == []