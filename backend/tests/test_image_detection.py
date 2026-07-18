from app.parser.html_parser import parse_html
from app.detector.image_detector import detect_images


def test_detect_images_finds_img_src():
    html = '<html><body><img src="cat.jpg" alt="Cat photo"></body></html>'

    parsed = parse_html(html)
    images = detect_images(parsed)

    assert len(images) == 1
    assert images[0].src == "cat.jpg"
    assert images[0].alt == "Cat photo"


def test_detect_images_finds_multiple_images():
    html = """
    <html>
        <body>
            <img src="cat.jpg" alt="Cat photo">
            <img src="dog.jpg" alt="Dog photo">
            <img src="bird.jpg" alt="Bird photo">
        </body>
    </html>
    """

    parsed = parse_html(html)
    images = detect_images(parsed)

    assert len(images) == 3
    assert images[0].src == "cat.jpg"
    assert images[1].src == "dog.jpg"
    assert images[2].src == "bird.jpg"


def test_detect_images_ignores_img_without_src():
    html = """
    <html>
        <body>
            <img alt="Missing source">
            <img src="valid.jpg" alt="Valid image">
        </body>
    </html>
    """

    parsed = parse_html(html)
    images = detect_images(parsed)

    assert len(images) == 1
    assert images[0].src == "valid.jpg"

def test_detect_images_ignores_whitespace_only_src():
    html = """
    <html>
        <body>
            <img src="   " alt="Empty source">
            <img src="valid.jpg" alt="Valid image">
        </body>
    </html>
    """

    parsed = parse_html(html)
    images = detect_images(parsed)

    assert len(images) == 1
    assert images[0].src == "valid.jpg"

def test_detect_images_strips_whitespace_from_src():
    html = """
    <html>
        <body>
            <img src="   cat.jpg   " alt="Cat photo">
        </body>
    </html>
    """

    parsed = parse_html(html)
    images = detect_images(parsed)

    assert len(images) == 1
    assert images[0].src == "cat.jpg"

def test_detect_images_resolves_relative_src_with_base_url():
    html = """
    <html>
        <body>
            <img src="/images/cat.jpg" alt="Cat photo">
        </body>
    </html>
    """

    parsed = parse_html(html, base_url="https://example.com/coursework/page.html")
    images = detect_images(parsed)

    assert len(images) == 1
    assert images[0].src == "https://example.com/images/cat.jpg"    

def test_detect_images_keeps_absolute_src_unchanged():
    html = """
    <html>
        <body>
            <img src="https://cdn.example.com/images/cat.jpg" alt="Cat photo">
        </body>
    </html>
    """

    parsed = parse_html(html, base_url="https://example.com/coursework/page.html")
    images = detect_images(parsed)

    assert len(images) == 1
    assert images[0].src == "https://cdn.example.com/images/cat.jpg"

def test_detect_images_handles_malformed_html():
    html = """
    <html>
        <body>
            <img src="cat.jpg" alt="Cat photo"
            <p>Some text without properly closed tags
        </body>
    </html>
    """

    parsed = parse_html(html)
    images = detect_images(parsed)

    assert len(images) == 1
    assert images[0].src == "cat.jpg"

def test_detect_images_preserves_duplicate_image_references():
    html = """
    <html>
        <body>
            <img src="cat.jpg" alt="Cat image in header">
            <p>Some page content</p>
            <img src="cat.jpg" alt="Cat image in gallery">
        </body>
    </html>
    """

    parsed = parse_html(html)
    images = detect_images(parsed)

    assert len(images) == 2
    assert images[0].src == "cat.jpg"
    assert images[0].alt == "Cat image in header"
    assert images[1].src == "cat.jpg"
    assert images[1].alt == "Cat image in gallery"

def test_detect_images_ignores_one_by_one_tracking_pixel():
    html = """
    <html>
        <body>
            <img
                src="tracking.gif"
                width="1"
                height="1"
                alt=""
            >

            <img
                src="coursework-image.jpg"
                width="800"
                height="600"
                alt="Coursework image"
            >
        </body>
    </html>
    """

    parsed = parse_html(html)
    images = detect_images(parsed)

    assert len(images) == 1
    assert images[0].src == "coursework-image.jpg"


def test_detect_images_ignores_clear_tracking_filename():
    html = """
    <html>
        <body>
            <img
                src="/assets/tracking-pixel.gif"
                alt=""
            >

            <img
                src="/images/cat.jpg"
                alt="Cat photograph"
            >
        </body>
    </html>
    """

    parsed = parse_html(
        html,
        base_url="https://example.com/page.html",
    )

    images = detect_images(parsed)

    assert len(images) == 1
    assert images[0].src == (
        "https://example.com/images/cat.jpg"
    )


def test_detect_images_ignores_hidden_image():
    html = """
    <html>
        <body>
            <img
                src="hidden-image.jpg"
                style="display: none"
                alt="Hidden image"
            >

            <img
                src="visible-image.jpg"
                alt="Visible image"
            >
        </body>
    </html>
    """

    parsed = parse_html(html)
    images = detect_images(parsed)

    assert len(images) == 1
    assert images[0].src == "visible-image.jpg"


def test_detect_images_keeps_normal_icon_or_logo():
    html = """
    <html>
        <body>
            <img
                src="organisation-logo.svg"
                width="200"
                height="100"
                alt="Organisation logo"
            >
        </body>
    </html>
    """

    parsed = parse_html(html)
    images = detect_images(parsed)

    assert len(images) == 1
    assert images[0].src == "organisation-logo.svg"