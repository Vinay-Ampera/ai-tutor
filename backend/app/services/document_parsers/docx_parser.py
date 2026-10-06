from io import BytesIO
from zipfile import BadZipFile

from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.services.document_parsers.errors import DocumentParsingError
from app.services.document_parsers.markdown import markdown_table


def parse_docx(content: bytes) -> str:
    try:
        document = Document(BytesIO(content))
    except (BadZipFile, OSError, PackageNotFoundError, ValueError) as error:
        raise DocumentParsingError(
            "The DOCX file is corrupt or cannot be read."
        ) from error

    content_blocks: list[str] = []
    table_number = 0
    for child in document.element.body.iterchildren():
        if child.tag.endswith("}p"):
            paragraph = Paragraph(child, document)
            text = paragraph.text.strip()
            if not text:
                continue
            style_name = paragraph.style.name if paragraph.style else ""
            if style_name.lower() == "title":
                content_blocks.append(f"# {text}")
            elif style_name.lower().startswith("heading "):
                level = _heading_level(style_name)
                content_blocks.append(f"{'#' * level} {text}")
            else:
                content_blocks.append(text)
        elif child.tag.endswith("}tbl"):
            table = Table(child, document)
            table_markdown = markdown_table(
                [[cell.text for cell in row.cells] for row in table.rows]
            )
            if table_markdown:
                table_number += 1
                content_blocks.append(f"**Table {table_number}**\n\n{table_markdown}")

    if not content_blocks:
        raise DocumentParsingError("The DOCX file contains no readable content.")
    return "\n\n".join(content_blocks).strip() + "\n"


def _heading_level(style_name: str) -> int:
    try:
        heading_number = style_name.split(maxsplit=1)[1].split(maxsplit=1)[0]
        level = int(heading_number)
    except (IndexError, ValueError):
        return 2
    return min(max(level, 1), 6)
