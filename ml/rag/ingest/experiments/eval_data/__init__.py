"""Flat eval-item list for the OCR benchmark — see documents.py for authoring."""

from .documents import DOCUMENTS, image_pairs

EVAL_ITEMS: list[dict] = image_pairs()
