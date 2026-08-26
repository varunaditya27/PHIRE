"""
Parses olmOCR's HTML table output (per its own prompt: "Convert equations
to LateX and tables to HTML" — see ml/rag/ingest/ocr.py's OCR_PROMPT) into
structured rows via stdlib HTML parsing, not LLM-based extraction.

This is the single implementation both chunking.py (flattened per-row
text for vector retrieval) and ml/graph's Observation extraction (typed
graph nodes) build on, so a table only ever gets parsed one way — found
necessary live: line-based chunking on raw table HTML produces meaningless
fragments like "<td>5.4 mEq/L</td>" with no label attached.
"""

import re
from html.parser import HTMLParser

_TABLE_RE = re.compile(r"<table>.*?</table>", re.DOTALL)


class _TableRowParser(HTMLParser):
    """Collects <tr> rows (each a list of cell strings) from one table block."""

    def __init__(self) -> None:
        super().__init__()
        self.row_cells: list[list[str]] = []
        self._current_row: list[str] | None = None
        self._current_cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag == "tr":
            self._current_row = []
        elif tag in ("td", "th"):
            self._current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th") and self._current_cell is not None and self._current_row is not None:
            self._current_row.append("".join(self._current_cell).strip())
            self._current_cell = None
        elif tag == "tr" and self._current_row is not None:
            self.row_cells.append(self._current_row)
            self._current_row = None

    def handle_data(self, data: str) -> None:
        if self._current_cell is not None:
            self._current_cell.append(data)


def find_table_blocks(text: str) -> list[str]:
    """Return every <table>...</table> substring in text, in document order."""
    return _TABLE_RE.findall(text)


def parse_table_rows(table_html: str) -> list[dict[str, str]]:
    """Parse one HTML table into a list of header-label -> cell-value dicts.

    Assumes the first <tr> is the header row — true for every table
    olmOCR has produced in this project's benchmark (experiments/results.json),
    since its prompt has it distinguish <th>/<td> consistently. A data row
    with a different cell count than the header row is zipped to the
    shorter length rather than raising — one OCR-dropped cell shouldn't
    crash ingestion of the whole document.
    """
    parser = _TableRowParser()
    parser.feed(table_html)
    if not parser.row_cells:
        return []
    headers, *data_rows = parser.row_cells
    return [dict(zip(headers, row)) for row in data_rows]


def flatten_row(row: dict[str, str]) -> str:
    """Render one parsed table row as a single self-contained retrievable chunk."""
    return ", ".join(f"{label}: {value}" for label, value in row.items() if label and value)
