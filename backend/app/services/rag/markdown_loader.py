import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.services.document_ingestion import MARKDOWN_DIRECTORY


class MarkdownDocumentError(ValueError):
    pass


@dataclass(frozen=True)
class MarkdownSource:
    original_filename: str
    source_format: str
    uploaded_at: datetime
    markdown_filename: str
    markdown_path: str
    content: str


def load_stage10_markdown(markdown_filename: str) -> MarkdownSource:
    if Path(markdown_filename).name != markdown_filename:
        raise MarkdownDocumentError("Provide a Markdown filename, not a file path.")
    if Path(markdown_filename).suffix.lower() != ".md":
        raise MarkdownDocumentError("Only generated Markdown (.md) files can be indexed.")

    markdown_directory = MARKDOWN_DIRECTORY.resolve()
    markdown_file = (markdown_directory / markdown_filename).resolve()
    if markdown_file.parent != markdown_directory:
        raise MarkdownDocumentError("The Markdown file must be in the generated Markdown directory.")
    try:
        text = markdown_file.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise MarkdownDocumentError(
            "The generated Markdown file could not be found."
        ) from error
    except (OSError, UnicodeError) as error:
        raise MarkdownDocumentError(
            "The generated Markdown file could not be read."
        ) from error

    metadata, content = _parse_stage10_frontmatter(text)
    try:
        original_filename = _required_metadata(metadata, "original_filename")
        source_format = _required_metadata(metadata, "file_type").lower()
        timestamp = _required_metadata(metadata, "processed_at")
        saved_filename = _required_metadata(metadata, "markdown_filename")
        markdown_path = _required_metadata(metadata, "markdown_path")
        uploaded_at = datetime.fromisoformat(timestamp)
    except (KeyError, ValueError) as error:
        raise MarkdownDocumentError(
            "The Markdown metadata is missing required Stage 10 fields."
        ) from error

    if saved_filename != markdown_filename:
        raise MarkdownDocumentError(
            "The Markdown filename does not match its Stage 10 metadata."
        )
    if not content.strip():
        raise MarkdownDocumentError("The Markdown file contains no document content.")

    return MarkdownSource(
        original_filename=original_filename,
        source_format=source_format,
        uploaded_at=uploaded_at,
        markdown_filename=saved_filename,
        markdown_path=markdown_path,
        content=content,
    )


def _parse_stage10_frontmatter(text: str) -> tuple[dict[str, object], str]:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise MarkdownDocumentError("The file has no Stage 10 metadata frontmatter.")
    try:
        closing_index = lines.index("---", 1)
    except ValueError as error:
        raise MarkdownDocumentError("The Markdown metadata frontmatter is incomplete.") from error

    metadata: dict[str, object] = {}
    for line in lines[1:closing_index]:
        key, separator, value = line.partition(":")
        if not separator:
            raise MarkdownDocumentError("The Markdown metadata frontmatter is invalid.")
        try:
            metadata[key.strip()] = json.loads(value.strip())
        except json.JSONDecodeError as error:
            raise MarkdownDocumentError(
                "The Markdown metadata frontmatter is invalid."
            ) from error
    return metadata, "\n".join(lines[closing_index + 1:]).lstrip()


def _required_metadata(metadata: dict[str, object], key: str) -> str:
    value = metadata.get(key)
    if not isinstance(value, str) or not value.strip():
        raise KeyError(key)
    return value
