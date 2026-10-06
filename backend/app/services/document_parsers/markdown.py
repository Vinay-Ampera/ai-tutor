from collections.abc import Iterable


def markdown_table(rows: Iterable[Iterable[object]]) -> str:
    normalized_rows = [
        [escape_table_cell(value) for value in row]
        for row in rows
    ]
    if not normalized_rows:
        return ""

    column_count = max(len(row) for row in normalized_rows)
    normalized_rows = [
        row + [""] * (column_count - len(row))
        for row in normalized_rows
    ]
    header = normalized_rows[0]
    separator = ["---"] * column_count
    body = normalized_rows[1:]

    return "\n".join(
        [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join(separator) + " |",
            *("| " + " | ".join(row) + " |" for row in body),
        ]
    )


def escape_table_cell(value: object) -> str:
    return " ".join(str(value).split()).replace("|", r"\|")
