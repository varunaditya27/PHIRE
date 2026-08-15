"""
Document ingestion pipeline: raw file -> normalized observations.

Responsibilities (to implement):
- Extract text/tables from PDFs via Docling (primary) or PyMuPDF (fallback);
  run OCR via Tesseract on scanned/image reports when needed.
- Hand extracted values to a normalization step producing Observation
  records.
- Preserve the immutable original artifact alongside the derived
  structured data.
"""
