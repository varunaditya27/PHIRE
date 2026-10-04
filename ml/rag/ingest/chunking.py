"""
Text chunking shared by the ingestion sources: chunk_text (paragraph-
aware, for PubMed/MedlinePlus prose) and chunk_ocr_text (table/line/
paragraph-aware, for patient documents).

Keeps chunks under embedding models' effective context (MedCPT truncates
at 512 tokens, ~1500-2000 chars for typical prose) without splitting
mid-sentence where avoidable.
"""

import re
from html.parser import HTMLParser

DEFAULT_MAX_CHARS = 1500

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
    """Parse one HTML table into a list of header-label -> cell-value dicts."""
    parser = _TableRowParser()
    parser.feed(table_html)
    if not parser.row_cells:
        return []
    headers, *data_rows = parser.row_cells
    return [dict(zip(headers, row)) for row in data_rows]


def flatten_row(row: dict[str, str]) -> str:
    """Render one parsed table row as a single self-contained retrievable chunk."""
    return ", ".join(f"{label}: {value}" for label, value in row.items() if label and value)


def chunk_text(text: str, max_chars: int = DEFAULT_MAX_CHARS) -> list[str]:
    """Split text into <=max_chars pieces, breaking on paragraph/sentence boundaries.

    Most ingested texts (PubMed abstracts) are already under max_chars and come back as a single chunk; MedlinePlus summaries are the main case that actually needs splitting.
    """
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(paragraphs) == 1:
        paragraphs = [p.strip() for p in text.split(". ") if p.strip()]

    chunks: list[str] = []
    current = ""
    for piece in paragraphs:
        candidate = f"{current} {piece}".strip() if current else piece
        if len(candidate) > max_chars and current:
            chunks.append(current)
            current = piece
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def chunk_ocr_text(text: str, max_chars: int = DEFAULT_MAX_CHARS) -> list[str]:
    """Chunk patient-document text (PDF-extracted or OCR'd): table rows, label lines, and prose all handled.

    Patient documents mix three content shapes, and a single blanket
    strategy gets at least one wrong:
    - HTML tables (from OCR or HTML document representations)
      — line-splitting these produces meaningless fragments like
      "<td>5.4 mEq/L</td>" with no label attached (verified live). Parsed
      structurally instead and flattened to one
      self-contained chunk per row.
    - Short label:value lines ("LDL Cholesterol: 162 mg/dL") — verified
      empirically that combining these into one chunk hurts retrieval
      (0.66 vs 0.75 cosine similarity for the same fact, chunked vs not),
      so each line becomes its own chunk.
    - Prose paragraphs (progress notes, radiology reports) — visual/OCR
      extractors emit these as one continuous string per paragraph with no
      internal line breaks, so a \n\n-delimited block containing no further \n is
      reliably prose, not a run of short facts, and stays whole.

    The distinguishing signal for the second vs. third case is exactly
    that: within one \n\n-delimited block, multiple \n-separated lines
    means label:value facts; a single line (however long) means prose.
    """
    chunks: list[str] = []
    remaining = text
    for table_html in find_table_blocks(text):
        before, remaining = remaining.split(table_html, 1)
        chunks.extend(_chunk_plain_blocks(before, max_chars))
        chunks.extend(flatten_row(row) for row in parse_table_rows(table_html) if flatten_row(row))
    chunks.extend(_chunk_plain_blocks(remaining, max_chars))
    return chunks


def locate_chunk_offsets(source_text: str, chunks: list[str]) -> list[tuple[int, int] | None]:
    """Find each chunk's (start, end) character offset within source_text, in order.

    Enables citing the exact span a claim's evidence came from (see
    ml/chains/qa_chain.py's VerifiedClaim.source_span) — the same idea as
    LangExtract's grounding (evaluated in ml/graph/experiments/RESULTS.md
    for a different use case), implemented directly rather than adding
    that dependency here.

    Searches forward from the end of the previous match, so repeated text
    (e.g. a duplicated header line) resolves to successive occurrences
    instead of the same one repeatedly. Returns None for a chunk that
    isn't found verbatim — table-row chunks (flatten_row)
    are reformatted ("Label: Value, ..."), not extracted verbatim, so they
    have no single matching span in source_text; documented gap, not a
    silent wrong answer.
    """
    offsets: list[tuple[int, int] | None] = []
    search_from = 0
    for chunk in chunks:
        index = source_text.find(chunk, search_from)
        if index == -1:
            index = source_text.find(chunk)
        if index == -1:
            offsets.append(None)
            continue
        offsets.append((index, index + len(chunk)))
        search_from = index + len(chunk)
    return offsets


def _chunk_plain_blocks(text: str, max_chars: int) -> list[str]:
    """Non-table text: multi-line \\n\\n-blocks are label:value facts (split by line); single-line blocks stay whole."""
    chunks: list[str] = []
    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        if "\n" in block:
            chunks.extend(line.strip() for line in block.split("\n") if line.strip())
        elif len(block) <= max_chars:
            chunks.append(block)
        else:
            chunks.extend(chunk_text(block, max_chars))
    return chunks
