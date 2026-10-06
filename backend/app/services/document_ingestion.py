import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.services.document_parsers.docx_parser import parse_docx
from app.services.document_parsers.errors import DocumentParsingError
from app.services.document_parsers.pdf_parser import parse_pdf
from app.services.document_parsers.spreadsheet_parser import parse_spreadsheet

BACKEND_ROOT = Path(__file__).resolve().parents[2]
MARKDOWN_DIRECTORY = BACKEND_ROOT / "data" / "markdown"
SUPPORTED_FORMATS = {"pdf", "docx", "xls", "xlsx"}


class DocumentIngestionError(ValueError):
    pass


class UnsupportedDocumentFormatError(DocumentIngestionError):
    pass


class DocumentStorageError(RuntimeError):
    pass


@dataclass(frozen=True)
class DocumentIngestionResult:
    original_filename: str
    file_type: str
    processed_at: str
    markdown_filename: str
    markdown_path: str


def ingest_document(original_filename: str, content: bytes) -> DocumentIngestionResult:
    input_basename = _basename(original_filename)
    file_type = Path(input_basename).suffix.lower().lstrip(".")
    if file_type not in SUPPORTED_FORMATS:
        raise UnsupportedDocumentFormatError(
            "Unsupported file format. Upload a PDF, DOCX, XLS, or XLSX file."
        )
    if not content:
        raise DocumentIngestionError("The uploaded file is empty.")

    try:
        markdown = _parse_document(content, file_type)
    except DocumentParsingError as error:
        raise DocumentIngestionError(str(error)) from error

    stem = _safe_stem(Path(input_basename).stem)
    try:
        MARKDOWN_DIRECTORY.mkdir(parents=True, exist_ok=True)
        while True:
            processed_at = datetime.now(UTC)
            timestamp = processed_at.strftime("%Y%m%d_%H%M%S_%f")
            markdown_filename = f"{stem}_{timestamp}.md"
            markdown_file = MARKDOWN_DIRECTORY / markdown_filename
            markdown_path = markdown_file.relative_to(BACKEND_ROOT).as_posix()
            full_markdown = _add_metadata_frontmatter(
                markdown,
                original_filename,
                file_type,
                processed_at.isoformat(),
                markdown_filename,
                markdown_path,
            )
            try:
                with markdown_file.open("x", encoding="utf-8", newline="\n") as output:
                    output.write(full_markdown)
                break
            except FileExistsError:
                continue
    except OSError as error:
        raise DocumentStorageError(
            "The processed Markdown could not be saved."
        ) from error

    return DocumentIngestionResult(
        original_filename=original_filename,
        file_type=file_type,
        processed_at=processed_at.isoformat(),
        markdown_filename=markdown_filename,
        markdown_path=markdown_path,
    )


def _parse_document(content: bytes, file_type: str) -> str:
    if file_type == "pdf":
        return parse_pdf(content)
    if file_type == "docx":
        return parse_docx(content)
    return parse_spreadsheet(content, file_type)


def _basename(filename: str) -> str:
    return Path(filename.replace("\\", "/")).name


def _safe_stem(stem: str) -> str:
    safe_stem = re.sub(r"[^\w.-]+", "_", stem, flags=re.UNICODE).strip("._")
    return safe_stem or "document"


def _add_metadata_frontmatter(
    markdown: str,
    original_filename: str,
    file_type: str,
    processed_at: str,
    markdown_filename: str,
    markdown_path: str,
) -> str:
    metadata = {
        "original_filename": original_filename,
        "file_type": file_type,
        "processed_at": processed_at,
        "markdown_filename": markdown_filename,
        "markdown_path": markdown_path,
    }
    frontmatter = "\n".join(
        f"{key}: {json.dumps(value, ensure_ascii=False)}"
        for key, value in metadata.items()
    )
    return f"---\n{frontmatter}\n---\n\n{markdown}"
