from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from app.crawler.zip_processor import (
    ZipProcessingError,
    read_html_documents_from_zip,
)


def _build_zip(
    files: dict[str, str],
) -> bytes:
    """
    Create an in-memory ZIP archive for testing.
    """

    buffer = BytesIO()

    with ZipFile(
        buffer,
        mode="w",
        compression=ZIP_DEFLATED,
    ) as archive:
        for filename, content in files.items():
            archive.writestr(
                filename,
                content,
            )

    return buffer.getvalue()


def test_reads_single_html_document_from_zip():
    zip_data = _build_zip(
        {
            "index.html": (
                "<html><body><h1>Coursework</h1></body></html>"
            )
        }
    )

    documents = read_html_documents_from_zip(
        zip_data
    )

    assert len(documents) == 1
    assert documents[0].relative_path == "index.html"
    assert "Coursework" in documents[0].html


def test_reads_multiple_html_documents_from_zip():
    zip_data = _build_zip(
        {
            "index.html": "<html>Home page</html>",
            "pages/about.html": "<html>About page</html>",
            "styles/site.css": "body { margin: 0; }",
            "images/cat.jpg": "fake-image-data",
        }
    )

    documents = read_html_documents_from_zip(
        zip_data
    )

    assert len(documents) == 2

    paths = {
        document.relative_path
        for document in documents
    }

    assert paths == {
        "index.html",
        "pages/about.html",
    }


def test_rejects_invalid_zip_data():
    with pytest.raises(
        ZipProcessingError,
        match="not a valid ZIP archive",
    ):
        read_html_documents_from_zip(
            b"This is not a ZIP file."
        )


def test_rejects_zip_path_traversal():
    zip_data = _build_zip(
        {
            "../outside.html": (
                "<html>Unsafe file</html>"
            )
        }
    )

    with pytest.raises(
        ZipProcessingError,
        match="Unsafe parent-directory path",
    ):
        read_html_documents_from_zip(
            zip_data
        )


def test_rejects_zip_without_html_files():
    zip_data = _build_zip(
        {
            "styles/site.css": (
                "body { background: white; }"
            ),
            "scripts/app.js": (
                "console.log('Hello');"
            ),
        }
    )

    with pytest.raises(
        ZipProcessingError,
        match="contains no readable HTML files",
    ):
        read_html_documents_from_zip(
            zip_data
        )


def test_rejects_unsupported_file_type():
    zip_data = _build_zip(
        {
            "index.html": "<html>Coursework</html>",
            "malware.exe": "not-really-an-executable",
        }
    )

    with pytest.raises(
        ZipProcessingError,
        match="Unsupported file type",
    ):
        read_html_documents_from_zip(
            zip_data
        )