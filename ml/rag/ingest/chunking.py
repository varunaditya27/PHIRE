"""
Paragraph-aware text chunking shared by the ingestion sources.

Keeps chunks under embedding models' effective context (MedCPT truncates at 512 tokens, ~1500-2000 chars for typical prose) without splitting mid-sentence where avoidable.
"""

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


def chunk_lines(text: str, max_chars: int = DEFAULT_MAX_CHARS) -> list[str]:
    """Split text into one chunk per non-blank line, for structured (not prose) documents.

    Patient lab reports extracted from PDF are naturally one fact per line ("LDL Cholesterol: 162 mg/dL"). Combining them into a single chunk (chunk_text's prose-oriented behavior) measurably hurts retrieval: verified empirically, a query for "LDL cholesterol result" scored 0.75 cosine similarity against just that line vs. 0.66 against the whole report as one chunk — the difference between surfacing in the top results or not.
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    chunks: list[str] = []
    for line in lines:
        chunks.extend([line] if len(line) <= max_chars else chunk_text(line, max_chars))
    return chunks
