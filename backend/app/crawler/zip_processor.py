from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile


MAX_ZIP_SIZE_BYTES = 10 * 1024 * 1024
MAX_EXTRACTED_SIZE_BYTES = 50 * 1024 * 1024
MAX_FILE_COUNT = 500

ALLOWED_EXTENSIONS = {
    ".html",
    ".htm",
    ".css",
    ".js",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".webp",
}


class ZipProcessingError(Exception):
    """
    Raised when a ZIP submission is invalid or unsafe.
    """


@dataclass
class ZipHtmlDocument:
    """
    Represents one HTML document read from a ZIP submission.
    """

    relative_path: str
    html: str


def _validate_member_path(member_name: str) -> None:
    """
    Ensure that a ZIP member cannot escape the extraction directory.

    Dangerous paths include:
        ../secret.txt
        /absolute/path/file.html
        C:/Windows/file.html
    """

    normalised_name = member_name.replace("\\", "/")
    member_path = PurePosixPath(normalised_name)

    if member_path.is_absolute():
        raise ZipProcessingError(
            f"Unsafe absolute path detected in ZIP: {member_name}"
        )

    if ".." in member_path.parts:
        raise ZipProcessingError(
            f"Unsafe parent-directory path detected in ZIP: {member_name}"
        )

    if (
        len(member_path.parts) > 0
        and ":" in member_path.parts[0]
    ):
        raise ZipProcessingError(
            f"Unsafe drive path detected in ZIP: {member_name}"
        )


def _validate_extension(member_name: str) -> None:
    """
    Reject files whose extensions are not required by the project.
    """

    suffix = Path(member_name).suffix.lower()

    if suffix and suffix not in ALLOWED_EXTENSIONS:
        raise ZipProcessingError(
            f"Unsupported file type in ZIP: {member_name}"
        )


def read_html_documents_from_zip(
    zip_data: bytes,
) -> list[ZipHtmlDocument]:
    """
    Validate a ZIP submission and return its HTML documents.

    The files are read directly from memory. They are not permanently
    stored on the server.

    Args:
        zip_data:
            Raw bytes from the uploaded ZIP file.

    Returns:
        A list of HTML documents found inside the archive.

    Raises:
        ZipProcessingError:
            If the archive is too large, invalid, unsafe, contains too
            many files, contains unsupported file types, or has no HTML.
    """

    if not zip_data:
        raise ZipProcessingError(
            "The uploaded ZIP file is empty."
        )

    if len(zip_data) > MAX_ZIP_SIZE_BYTES:
        raise ZipProcessingError(
            "The uploaded ZIP file exceeds the 10 MB size limit."
        )

    try:
        archive = ZipFile(BytesIO(zip_data))

    except BadZipFile as error:
        raise ZipProcessingError(
            "The uploaded file is not a valid ZIP archive."
        ) from error

    with archive:
        members = [
            member
            for member in archive.infolist()
            if not member.is_dir()
        ]

        if len(members) > MAX_FILE_COUNT:
            raise ZipProcessingError(
                "The ZIP archive contains too many files."
            )

        extracted_size = sum(
            member.file_size
            for member in members
        )

        if extracted_size > MAX_EXTRACTED_SIZE_BYTES:
            raise ZipProcessingError(
                "The extracted ZIP contents exceed the 50 MB limit."
            )

        html_documents: list[ZipHtmlDocument] = []

        for member in members:
            _validate_member_path(member.filename)
            _validate_extension(member.filename)

            suffix = Path(member.filename).suffix.lower()

            if suffix not in {".html", ".htm"}:
                continue

            try:
                raw_html = archive.read(member)

            except RuntimeError as error:
                raise ZipProcessingError(
                    f"Could not read ZIP member: {member.filename}"
                ) from error

            try:
                html = raw_html.decode("utf-8")

            except UnicodeDecodeError:
                try:
                    html = raw_html.decode("windows-1252")

                except UnicodeDecodeError as error:
                    raise ZipProcessingError(
                        (
                            "The HTML file could not be decoded: "
                            f"{member.filename}"
                        )
                    ) from error

            if not html.strip():
                continue

            normalised_path = member.filename.replace(
                "\\",
                "/",
            )

            html_documents.append(
                ZipHtmlDocument(
                    relative_path=normalised_path,
                    html=html,
                )
            )

    if not html_documents:
        raise ZipProcessingError(
            "The ZIP archive contains no readable HTML files."
        )

    return html_documents