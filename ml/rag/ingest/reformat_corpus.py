"""
Upgrade stored reference chunks to the current text format, in place and offline.

When ingestion's text rendering improves (USDA key-value lists -> natural-language sentences,
MedlinePlus glued sentences -> spaced), the already-stored corpus keeps the old text until it is
re-ingested -- which needs network and, for USDA, a rate-limited key. This rewrites the stored text
directly from what is already in Chroma (same chunk ids, same metadata) and re-embeds only the
chunks that changed. Idempotent: a chunk already in the new format is left alone.

Run from the repo root, with the backend stopped (it loads the embedding model, and the backend's
in-memory chunk cache would otherwise go stale):

    PYTHONPATH=. ml/.venv/bin/python -m ml.rag.ingest.reformat_corpus [--dry-run]
"""

import argparse

from ml.rag.ingest import usda
from ml.rag.ingest.text_cleanup import fix_sentence_spacing
from ml.rag.retriever import Chunk, HybridRetriever


def reformat_text(source: str | None, text: str) -> str:
    """The text in the current format for a chunk of `source` (unchanged if already current)."""
    if source == "usda":
        food = usda.parse_old_food_text(text)
        return usda.format_food_text(food) if food else text
    if source == "medlineplus":
        return fix_sentence_spacing(text)
    return text


def main() -> None:
    """Rewrite every stored USDA/MedlinePlus chunk whose text is in an outdated format."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="report what would change; write nothing")
    args = parser.parse_args()

    retriever = HybridRetriever()
    changed = [
        Chunk(id=c.id, text=new, metadata=c.metadata)
        for c in retriever.chunks()
        if (new := reformat_text(c.metadata.get("source"), c.text)) != c.text
    ]
    by_source: dict[str, int] = {}
    for c in changed:
        by_source[c.metadata.get("source", "?")] = by_source.get(c.metadata.get("source", "?"), 0) + 1
    print(f"{len(changed)} chunk(s) to update: {by_source}")
    if changed and not args.dry_run:
        retriever.add_documents(changed)  # upsert by id, re-embedded
        print("Done. Restart the backend so its chunk cache is rebuilt.")


if __name__ == "__main__":
    main()
