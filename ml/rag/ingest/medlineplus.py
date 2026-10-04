"""
MedlinePlus consumer-health topic summaries via NLM's public wsearch API.

MedlinePlus summaries are NLM-curated (not per-article peer review like
PubMed), consumer-answer-shaped, and don't carry a per-article publish
date in search results — see reranker.py's neutral-default handling for
metadata that's genuinely absent rather than missing due to a bug.
"""

import html
import re
import time
import xml.etree.ElementTree as ElementTree

import requests

from ml.rag.ingest.text_cleanup import fix_sentence_spacing

WSEARCH_BASE = "https://wsearch.nlm.nih.gov/ws/query"
REQUEST_DELAY_SECONDS = 0.2

_TAG_RE = re.compile(r"<[^>]+>")


# Block-level tags separate sentences/items; inline ones (the <span class=...> search highlights) do not.
_BLOCK_TAG_RE = re.compile(r"</?(?:p|li|ul|ol|br|div|h[1-6])\b[^>]*>", re.IGNORECASE)


def _strip_html(raw: str) -> str:
    """Strip MedlinePlus markup and unescape entities, keeping sentences apart.

    Removing every tag outright glued adjacent paragraphs together ("...disease.What are LDL?"),
    which made 169 of 176 stored passages read as run-on text. Block tags now become a space;
    inline highlight spans are dropped without one so words are not split.
    """
    text = _BLOCK_TAG_RE.sub(" ", raw)
    text = html.unescape(_TAG_RE.sub("", text))
    return fix_sentence_spacing(re.sub(r"\s+", " ", text).strip())


def fetch_topic_summaries(query: str, max_results: int = 2) -> list[dict]:
    """Search MedlinePlus health topics for query, return up to max_results title/url/summary."""
    response = requests.get(
        WSEARCH_BASE,
        params={"db": "healthTopics", "term": query, "retmax": max_results},
        timeout=15,
    )
    response.raise_for_status()
    time.sleep(REQUEST_DELAY_SECONDS)
    root = ElementTree.fromstring(response.text)

    summaries = []
    for document in root.findall(".//document"):
        url = document.get("url", "")
        title_node = document.find("./content[@name='title']")
        summary_node = document.find("./content[@name='FullSummary']")
        if title_node is None or summary_node is None or not title_node.text or not summary_node.text:
            continue
        summaries.append({
            "title": _strip_html(title_node.text),
            "summary": _strip_html(summary_node.text),
            "url": url,
        })
    return summaries
