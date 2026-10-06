from io import BytesIO
from zipfile import BadZipFile

import pandas as pd
from xlrd.biffh import XLRDError

from app.services.document_parsers.errors import DocumentParsingError
from app.services.document_parsers.markdown import markdown_table


def parse_spreadsheet(content: bytes, file_type: str) -> str:
    engine = "xlrd" if file_type == "xls" else "openpyxl"
    try:
        sheets = pd.read_excel(
            BytesIO(content),
            sheet_name=None,
            engine=engine,
        )
    except (BadZipFile, OSError, ValueError, XLRDError) as error:
        raise DocumentParsingError(
            f"The {file_type.upper()} workbook is corrupt or cannot be read."
        ) from error

    if not sheets:
        raise DocumentParsingError("The workbook contains no readable sheets.")

    markdown: list[str] = []
    for sheet_name, frame in sheets.items():
        markdown.append(f"## Sheet: {sheet_name}")
        table = _dataframe_table(frame)
        markdown.append(table or "(No tabular data.)")

    return "\n\n".join(markdown).strip() + "\n"


def _dataframe_table(frame: pd.DataFrame) -> str:
    if frame.empty and len(frame.columns) == 0:
        return ""
    headers = [str(column) for column in frame.columns]
    rows = [
        ["" if pd.isna(value) else value for value in row]
        for row in frame.itertuples(index=False, name=None)
    ]
    return markdown_table([headers, *rows])
