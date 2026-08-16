"""
Text chunking shared by the ingestion sources: chunk_text (paragraph-
aware, for PubMed/MedlinePlus prose) and chunk_ocr_text (table/line/
paragraph-aware, for patient documents).

Keeps chunks under embedding models' effective context (MedCPT truncates
at 512 tokens, ~1500-2000 chars for typical prose) without splitting
mid-sentence where avoidable.
"""

from ml.rag.ingest.table_parsing import find_table_blocks, flatten_row, parse_table_rows

DEFAULT_MAX_CHARS = 1500


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
    - HTML tables (olmOCR's own prompt asks it to convert tables to HTML)
      — line-splitting these produces meaningless fragments like
      "<td>5.4 mEq/L</td>" with no label attached (verified live). Parsed
      structurally instead (table_parsing.py) and flattened to one
      self-contained chunk per row.
    - Short label:value lines ("LDL Cholesterol: 162 mg/dL") — verified
      empirically that combining these into one chunk hurts retrieval
      (0.66 vs 0.75 cosine similarity for the same fact, chunked vs not),
      so each line becomes its own chunk.
    - Prose paragraphs (progress notes, radiology reports) — olmOCR emits
      these as one continuous string per paragraph with no internal line
      breaks, so a \\n\\n-delimited block containing no further \\n is
      reliably prose, not a run of short facts, and stays whole.

    The distinguishing signal for the second vs. third case is exactly
    that: within one \\n\\n-delimited block, multiple \\n-separated lines
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
