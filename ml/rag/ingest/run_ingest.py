"""
Reference-evidence ingestion entry point.

Fetches PubMed abstracts + MedlinePlus summaries for every topic in
topics.CLINICAL_TOPICS, and USDA nutrient data for every query in
topics.FOOD_QUERIES, chunks/wraps them as retriever.Chunk, and indexes them
into the same Chroma + BM25 store retriever.py searches at query time. Run
from the repo root:

    ml/.venv/bin/python -m ml.rag.ingest.run_ingest

Network calls only ever touch public reference APIs (PubMed, MedlinePlus,
USDA) — never patient data, so this doesn't cross PHIRE's local-only PHI
boundary. A per-topic failure (timeout, rate limit) is logged and skipped
rather than aborting the whole run; manifest.json records what succeeded,
what failed, and when, for reproducibility/audit.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from ml.rag.ingest import medlineplus, pubmed, usda
from ml.rag.ingest.chunking import chunk_text
from ml.rag.ingest.topics import CLINICAL_TOPICS, FOOD_QUERIES
from ml.rag.retriever import Chunk, HybridRetriever

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = REPO_ROOT / "data" / "ingest_manifest.json"

PUBMED_AUTHORITY = 0.7
MEDLINEPLUS_AUTHORITY = 0.9
USDA_AUTHORITY = 0.95
PUBMED_RESULTS_PER_TOPIC = 5
MEDLINEPLUS_RESULTS_PER_TOPIC = 2
USDA_RESULTS_PER_QUERY = 2


def _pubmed_chunks(topic_id: str, query: str) -> list[Chunk]:
    """Fetch and wrap PubMed abstracts for one topic."""
    chunks = []
    for article in pubmed.fetch_topic_articles(query, PUBMED_RESULTS_PER_TOPIC):
        text = f"{article['title']}. {article['abstract']}"
        for i, piece in enumerate(chunk_text(text)):
            chunks.append(Chunk(
                id=f"pubmed_{article['pmid']}_{i}",
                text=piece,
                metadata={
                    "source": "pubmed",
                    "topic": topic_id,
                    "url": article["url"],
                    "authority": PUBMED_AUTHORITY,
                    **({"published_date": article["published_date"]} if article["published_date"] else {}),
                },
            ))
    return chunks


def _medlineplus_chunks(topic_id: str, query: str) -> list[Chunk]:
    """Fetch and wrap MedlinePlus summaries for one topic."""
    chunks = []
    for summary in medlineplus.fetch_topic_summaries(query, MEDLINEPLUS_RESULTS_PER_TOPIC):
        slug = summary["url"].rstrip("/").rsplit("/", 1)[-1].removesuffix(".html")
        for i, piece in enumerate(chunk_text(summary["summary"])):
            chunks.append(Chunk(
                id=f"medlineplus_{slug}_{i}",
                text=piece,
                metadata={
                    "source": "medlineplus", "topic": topic_id,
                    "url": summary["url"], "authority": MEDLINEPLUS_AUTHORITY,
                },
            ))
    return chunks


def _usda_chunks(food_query: str) -> list[Chunk]:
    """Fetch and wrap USDA nutrient data for one food query."""
    chunks = []
    for food in usda.search_foods(food_query, USDA_RESULTS_PER_QUERY):
        chunks.append(Chunk(
            id=f"usda_{food['fdc_id']}",
            text=usda.format_food_text(food),
            metadata={
                "source": "usda", "authority": USDA_AUTHORITY,
                **({"published_date": food["published_date"]} if food.get("published_date") else {}),
            },
        ))
    return chunks


def main() -> None:
    retriever = HybridRetriever()
    manifest = {"started_at": datetime.now(timezone.utc).isoformat(), "topics": {}, "foods": {}, "failures": []}

    for topic_id, query in CLINICAL_TOPICS.items():
        print(f"--- {topic_id} ({query}) ---")
        chunks: list[Chunk] = []
        for fetch, label in ((_pubmed_chunks, "pubmed"), (_medlineplus_chunks, "medlineplus")):
            try:
                chunks.extend(fetch(topic_id, query))
            except Exception as exc:  # noqa: BLE001 - one bad topic shouldn't abort the run
                print(f"  [{label} FAILED] {exc}")
                manifest["failures"].append({"topic": topic_id, "source": label, "error": str(exc)})
        retriever.add_documents(chunks)
        manifest["topics"][topic_id] = len(chunks)
        print(f"  indexed {len(chunks)} chunks")

    for food_query in FOOD_QUERIES:
        try:
            chunks = _usda_chunks(food_query)
        except Exception as exc:  # noqa: BLE001
            print(f"--- {food_query} [usda FAILED] {exc} ---")
            manifest["failures"].append({"topic": food_query, "source": "usda", "error": str(exc)})
            continue
        retriever.add_documents(chunks)
        manifest["foods"][food_query] = len(chunks)
        print(f"--- {food_query}: indexed {len(chunks)} chunks ---")

    manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
    manifest["total_chunks"] = sum(manifest["topics"].values()) + sum(manifest["foods"].values())
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))
    print(f"\nIngested {manifest['total_chunks']} chunks, {len(manifest['failures'])} failures.")
    print(f"Manifest written to {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
