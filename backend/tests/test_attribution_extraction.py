from app.parser.html_parser import parse_html
from app.detector.image_detector import detect_images
from app.extractor.attribution_extractor import extract_attribution_evidence


def test_extracts_figcaption_for_image():
    html = """
    <html>
        <body>
            <figure>
                <img src="cat.jpg" alt="Cat photograph">
                <figcaption>
                    Photo by Jane Smith. Licensed under CC BY 4.0.
                </figcaption>
            </figure>
        </body>
    </html>
    """

    parsed = parse_html(html)
    images = detect_images(parsed)
    evidence = extract_attribution_evidence(parsed, images)

    assert len(evidence) == 1
    assert evidence[0].caption == (
        "Photo by Jane Smith. Licensed under CC BY 4.0."
    )

def test_extracts_author_from_figcaption():
    html = """
    <html>
        <body>
            <figure>
                <img src="cat.jpg" alt="Cat photograph">
                <figcaption>
                    Photo by Jane Smith. Licensed under CC BY 4.0.
                </figcaption>
            </figure>
        </body>
    </html>
    """

    parsed = parse_html(html)
    images = detect_images(parsed)
    evidence = extract_attribution_evidence(parsed, images)

    assert len(evidence) == 1
    assert evidence[0].possible_author == "Jane Smith"

def test_extracts_licence_name_from_figcaption():
    html = """
    <html>
        <body>
            <figure>
                <img src="cat.jpg" alt="Cat photograph">
                <figcaption>
                    Photo by Jane Smith. Licensed under CC BY 4.0.
                </figcaption>
            </figure>
        </body>
    </html>
    """

    parsed = parse_html(html)
    images = detect_images(parsed)
    evidence = extract_attribution_evidence(parsed, images)

    assert len(evidence) == 1
    assert evidence[0].licence_name == "CC BY 4.0"

def test_extracts_licence_url_near_image():
    html = """
    <html>
        <body>
            <figure>
                <img src="cat.jpg" alt="Cat photograph">
                <figcaption>
                    Photo by Jane Smith. Licensed under CC BY 4.0.
                </figcaption>
            </figure>

            <a href="https://creativecommons.org/licenses/by/4.0/">
                View licence
            </a>
        </body>
    </html>
    """

    parsed = parse_html(html)
    images = detect_images(parsed)
    evidence = extract_attribution_evidence(parsed, images)

    assert len(evidence) == 1
    assert evidence[0].licence_url == (
        "https://creativecommons.org/licenses/by/4.0/"
    )

def test_extracts_separate_captions_for_multiple_images():
    html = """
    <html>
        <body>
            <figure>
                <img src="cat.jpg" alt="Cat photograph">
                <figcaption>
                    Photo by Jane Smith. Licensed under CC BY 4.0.
                </figcaption>
            </figure>

            <figure>
                <img src="dog.jpg" alt="Dog photograph">
                <figcaption>
                    Photo by John Brown. Licensed under CC BY-SA 4.0.
                </figcaption>
            </figure>
        </body>
    </html>
    """

    parsed = parse_html(html)
    images = detect_images(parsed)
    evidence = extract_attribution_evidence(parsed, images)

    assert len(evidence) == 2

    assert evidence[0].image.src == "cat.jpg"
    assert evidence[0].possible_author == "Jane Smith"
    assert evidence[0].licence_name == "CC BY 4.0"

    assert evidence[1].image.src == "dog.jpg"
    assert evidence[1].possible_author == "John Brown"
    assert evidence[1].licence_name == "CC BY-SA 4.0"

def test_extracts_author_and_licence_from_image_attributes():
    html = """
    <html>
        <body>
            <img
                src="cat.jpg"
                alt="Photo by Jane Smith"
                title="Licensed under CC BY 4.0"
            >
        </body>
    </html>
    """

    parsed = parse_html(html)
    images = detect_images(parsed)
    evidence = extract_attribution_evidence(parsed, images)

    assert len(evidence) == 1
    assert evidence[0].possible_author == "Jane Smith"
    assert evidence[0].licence_name == "CC BY 4.0"

def test_extracts_attribution_from_footer():
    html = """
    <html>
        <body>
            <img src="cat.jpg" alt="Cat photograph">

            <footer>
                Image by Jane Smith. Licensed under CC BY 4.0.
            </footer>
        </body>
    </html>
    """

    parsed = parse_html(html)
    images = detect_images(parsed)
    evidence = extract_attribution_evidence(parsed, images)

    assert len(evidence) == 1
    assert evidence[0].possible_author == "Jane Smith"
    assert evidence[0].licence_name == "CC BY 4.0"

