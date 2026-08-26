"""
PubMed abstract fetching via NCBI E-utilities (esearch + efetch).

Uses abstracts, not full PMC article text: abstracts are uniformly
available and reusable for text mining, whereas full-text license terms
vary per PMC article, which would need per-document license checking
before ingestion. NCBI allows 3 requests/second without an API key
(NCBI_API_KEY env var raises that limit); REQUEST_DELAY_SECONDS throttles
to stay under the unauthenticated limit.
"""

import os
import time
import xml.etree.ElementTree as ElementTree

import requests

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
REQUEST_DELAY_SECONDS = 0.34
_API_KEY = os.environ.get("NCBI_API_KEY")


def _request_params(extra: dict) -> dict:
    """Common query params for every E-utilities call, with the optional API key attached."""
    params = {**extra}
    if _API_KEY:
        params["api_key"] = _API_KEY
    return params


def _esearch(term: str, retmax: int) -> list[str]:
    """Return up to retmax PubMed ids matching term."""
    response = requests.get(
        f"{EUTILS_BASE}/esearch.fcgi",
        params=_request_params({"db": "pubmed", "term": term, "retmax": retmax, "retmode": "json"}),
        timeout=15,
    )
    response.raise_for_status()
    return response.json().get("esearchresult", {}).get("idlist", [])


def _extract_pub_date(article: ElementTree.Element) -> str | None:
    """Best-effort ISO date from PubMed's often-partial PubDate element (year-only is common)."""
    pub_date = article.find(".//Journal/JournalIssue/PubDate")
    if pub_date is None:
        return None
    year = pub_date.findtext("Year")
    if not year:
        return None
    month = (pub_date.findtext("Month") or "01").zfill(2) if pub_date.findtext("Month", "").isdigit() else "01"
    return f"{year}-{month}-01"


def _efetch_abstracts(pmids: list[str]) -> list[dict]:
    """Fetch title/abstract/date for a batch of PubMed ids in one call."""
    if not pmids:
        return []
    response = requests.get(
        f"{EUTILS_BASE}/efetch.fcgi",
        params=_request_params({"db": "pubmed", "id": ",".join(pmids), "rettype": "abstract", "retmode": "xml"}),
        timeout=20,
    )
    response.raise_for_status()
    root = ElementTree.fromstring(response.text)

    articles = []
    for article in root.findall(".//PubmedArticle"):
        pmid = article.findtext(".//PMID")
        title = article.findtext(".//ArticleTitle")
        abstract_parts = [node.text for node in article.findall(".//AbstractText") if node.text]
        if not pmid or not title or not abstract_parts:
            continue
        articles.append({
            "pmid": pmid,
            "title": title,
            "abstract": " ".join(abstract_parts),
            "published_date": _extract_pub_date(article),
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        })
    return articles


def fetch_topic_articles(query: str, max_results: int = 5) -> list[dict]:
    """Search PubMed for query and return up to max_results articles with title/abstract/date/url."""
    pmids = _esearch(query, max_results)
    time.sleep(REQUEST_DELAY_SECONDS)
    articles = _efetch_abstracts(pmids)
    time.sleep(REQUEST_DELAY_SECONDS)
    return articles
