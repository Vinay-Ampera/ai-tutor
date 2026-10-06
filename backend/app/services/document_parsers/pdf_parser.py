from statistics import median

import pymupdf

from app.services.document_parsers.errors import DocumentParsingError
from app.services.document_parsers.markdown import markdown_table


def parse_pdf(content: bytes) -> str:
    try:
        document = pymupdf.open(stream=content, filetype="pdf")
    except (pymupdf.FileDataError, OSError, RuntimeError, ValueError) as error:
        raise DocumentParsingError(
            "The PDF is corrupt or cannot be read."
        ) from error

    with document:
        if document.needs_pass:
            raise DocumentParsingError("Password-protected PDFs are not supported.")

        pages: list[str] = []
        for page_number, page in enumerate(document, start=1):
            pages.append(f"## Page {page_number}")
            tables = page.find_tables().tables
            table_rectangles = [pymupdf.Rect(table.bbox) for table in tables]
            blocks = page.get_text("dict")["blocks"]
            page_font_sizes = [
                float(span["size"])
                for block in blocks
                if block.get("type") == 0
                for line in block.get("lines", [])
                for span in line.get("spans", [])
                if isinstance(span.get("size"), int | float)
            ]
            body_size = median(page_font_sizes) if page_font_sizes else None
            events: list[tuple[float, float, str]] = []

            for block in blocks:
                if block.get("type") != 0:
                    continue
                text, heading_level = _text_block(block, body_size)
                if not text:
                    continue
                rectangle = pymupdf.Rect(block["bbox"])
                if any(rectangle.intersects(table_rect) for table_rect in table_rectangles):
                    continue
                prefix = "#" * heading_level + " " if heading_level else ""
                events.append((rectangle.y0, rectangle.x0, prefix + text))

            for index, table in enumerate(tables, start=1):
                table_markdown = markdown_table(table.extract())
                if table_markdown:
                    table_rectangle = pymupdf.Rect(table.bbox)
                    events.append(
                        (
                            table_rectangle.y0,
                            table_rectangle.x0,
                            f"**Table {index}**\n\n{table_markdown}",
                        )
                    )

            pages.extend(
                text for _, _, text in sorted(events, key=lambda event: event[:2])
            )

        return "\n\n".join(pages).strip() + "\n"


def _text_block(
    block: dict[str, object],
    body_size: float | None,
) -> tuple[str, int]:
    lines = block.get("lines", [])
    if not isinstance(lines, list):
        return "", 0

    text_lines: list[str] = []
    sizes: list[float] = []
    bold = False
    for line in lines:
        if not isinstance(line, dict):
            continue
        spans = line.get("spans", [])
        if not isinstance(spans, list):
            continue
        line_text = "".join(
            str(span.get("text", ""))
            for span in spans
            if isinstance(span, dict)
        ).strip()
        if line_text:
            text_lines.append(line_text)
        for span in spans:
            if not isinstance(span, dict):
                continue
            size = span.get("size")
            if isinstance(size, int | float):
                sizes.append(float(size))
            bold = bold or "bold" in str(span.get("font", "")).lower()

    text = "\n".join(text_lines).strip()
    if not text or not sizes or body_size is None:
        return text, 0

    largest_size = max(sizes)
    is_heading = (
        len(text) <= 160
        and (
            largest_size >= body_size * 1.35
            or (bold and largest_size >= body_size * 1.08)
        )
    )
    if not is_heading:
        return text, 0

    return text, 3
