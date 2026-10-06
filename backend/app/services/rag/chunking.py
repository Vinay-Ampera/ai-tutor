import re
from collections.abc import Callable
from dataclasses import dataclass


DEFAULT_MAX_TOKENS = 450
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
PAGE_PATTERN = re.compile(r"^Page\s+(\d+)$", re.IGNORECASE)
SHEET_PATTERN = re.compile(r"^Sheet:\s*(.+)$", re.IGNORECASE)
SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class MarkdownChunk:
    content: str
    heading: str | None
    page_number: int | None
    sheet_name: str | None

    def metadata(self) -> dict[str, str | int | None]:
        return {
            "heading": self.heading,
            "page_number": self.page_number,
            "sheet_name": self.sheet_name,
        }


def chunk_markdown(
    markdown: str,
    *,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    token_counter: Callable[[str], int] | None = None,
) -> list[MarkdownChunk]:
    """Group Markdown blocks by their headings, splitting only oversized blocks."""
    if max_tokens < 1:
        raise ValueError("max_tokens must be a positive integer.")
    count_tokens = token_counter or _estimated_token_count
    chunks: list[MarkdownChunk] = []
    headings: list[tuple[int, str]] = []
    current_blocks: list[str] = []
    page_number: int | None = None
    sheet_name: str | None = None

    def heading_context() -> str | None:
        return " > ".join(text for _, text in headings) or None

    def emit(blocks: list[str]) -> None:
        text = "\n\n".join(blocks).strip()
        if not text:
            return
        context = heading_context()
        content = f"{context}\n\n{text}" if context else text
        chunks.append(
            MarkdownChunk(
                content=content,
                heading=context,
                page_number=page_number,
                sheet_name=sheet_name,
            )
        )

    def flush() -> None:
        nonlocal current_blocks
        if not current_blocks:
            return
        emit(current_blocks)
        current_blocks = []

    for section in _markdown_sections(markdown):
        if section[0] == "heading":
            flush()
            level, title = section[1], section[2]
            headings = [(heading_level, text) for heading_level, text in headings
                        if heading_level < level]
            headings.append((level, title))

            page_match = PAGE_PATTERN.fullmatch(title)
            if page_match:
                page_number = int(page_match.group(1))
                sheet_name = None
            else:
                sheet_match = SHEET_PATTERN.fullmatch(title)
                if sheet_match:
                    sheet_name = sheet_match.group(1).strip()
                    page_number = None
            continue

        for block in _blocks(section[2]):
            context = heading_context()
            prefix = f"{context}\n\n" if context else ""
            if count_tokens(prefix + block) <= max_tokens:
                candidate = [*current_blocks, block]
                if count_tokens(prefix + "\n\n".join(candidate)) <= max_tokens:
                    current_blocks = candidate
                else:
                    flush()
                    current_blocks = [block]
                continue

            flush()
            for fragment in _split_oversized_block(
                block,
                max_tokens=max_tokens,
                token_counter=count_tokens,
                prefix=prefix,
            ):
                emit([fragment])

    flush()
    return chunks


def _markdown_sections(markdown: str) -> list[tuple[str, int | str, str]]:
    sections: list[tuple[str, int | str, str]] = []
    body: list[str] = []
    for line in markdown.splitlines():
        match = HEADING_PATTERN.match(line)
        if match:
            if body:
                sections.append(("body", 0, "\n".join(body).strip()))
                body = []
            sections.append(("heading", len(match.group(1)), match.group(2).strip()))
        else:
            body.append(line)
    if body:
        sections.append(("body", 0, "\n".join(body).strip()))
    return sections


def _blocks(text: str) -> list[str]:
    return [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]


def _split_oversized_block(
    block: str,
    *,
    max_tokens: int,
    token_counter: Callable[[str], int],
    prefix: str,
) -> list[str]:
    lines = block.splitlines()
    if len(lines) >= 2 and lines[0].lstrip().startswith("|"):
        table_chunks = _split_table(
            lines,
            max_tokens=max_tokens,
            token_counter=token_counter,
            prefix=prefix,
        )
        if table_chunks is not None:
            return table_chunks

    sentences = SENTENCE_PATTERN.split(block)
    fragments: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip()
        if token_counter(prefix + candidate) <= max_tokens:
            current = candidate
            continue
        if current:
            fragments.append(current)
            current = ""
        if token_counter(prefix + sentence) <= max_tokens:
            current = sentence
        else:
            fragments.extend(
                _split_long_text(
                    sentence,
                    max_tokens=max_tokens,
                    token_counter=token_counter,
                    prefix=prefix,
                )
            )
    if current:
        fragments.append(current)
    return fragments


def _split_table(
    lines: list[str],
    *,
    max_tokens: int,
    token_counter: Callable[[str], int],
    prefix: str,
) -> list[str] | None:
    if len(lines) < 2 or not re.match(r"^\s*\|?\s*:?-{3,}", lines[1]):
        return None

    header = lines[:2]
    chunks: list[str] = []
    rows: list[str] = []
    for row in lines[2:]:
        candidate = "\n".join([*header, *rows, row])
        if token_counter(prefix + candidate) <= max_tokens:
            rows.append(row)
            continue
        if rows:
            chunks.append("\n".join([*header, *rows]))
            rows = []
        if token_counter(prefix + "\n".join([*header, row])) <= max_tokens:
            rows.append(row)
        else:
            return None
    if rows or not chunks:
        chunks.append("\n".join([*header, *rows]))
    return chunks


def _split_long_text(
    text: str,
    *,
    max_tokens: int,
    token_counter: Callable[[str], int],
    prefix: str,
) -> list[str]:
    fragments: list[str] = []
    words = text.split()
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and token_counter(prefix + candidate) > max_tokens:
            fragments.append(current)
            current = word
        else:
            current = candidate
    if current:
        fragments.append(current)
    return fragments


def _estimated_token_count(text: str) -> int:
    return max(1, len(re.findall(r"\w+|[^\w\s]", text)))
