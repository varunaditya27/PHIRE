"""
POST /api/documents/* — document ingestion endpoints.

Responsibilities (to implement):
- Accept uploaded lab reports / PDFs / scanned images.
- Kick off the ingestion pipeline: services.document_processor -> OCR /
  parsing -> normalized observations -> timeline update.
- Return the created document ID and processing status (async job pattern,
  since OCR + parsing can be slow).
"""
