"""
Unit tests for ml/rag/ingest/'s pure-logic pieces: chunking, HTML
stripping, USDA candidate ranking, PubMed date parsing.

No network calls — these test parsing/ranking logic in isolation, not the
live PubMed/MedlinePlus/USDA APIs (which run_ingest.py exercises directly
when actually ingesting).
"""

import xml.etree.ElementTree as ElementTree

from ml.rag.ingest.chunking import chunk_text
from ml.rag.ingest.medlineplus import _strip_html
from ml.rag.ingest.pubmed import _extract_pub_date
from ml.rag.ingest.usda import _closeness_key, _core_term


def test_chunk_text_leaves_short_text_as_one_chunk():
    assert chunk_text("LDL cholesterol was elevated.") == ["LDL cholesterol was elevated."]


def test_chunk_text_returns_empty_list_for_empty_text():
    assert chunk_text("") == []


def test_chunk_text_splits_long_text_on_paragraph_boundaries():
    # Each paragraph (~85 chars) fits under max_chars alone, so the split
    # must come from combining paragraphs, not from breaking one apart.
    paragraphs = ["First paragraph. " * 5, "Second paragraph. " * 5, "Third paragraph. " * 5]
    text = "\n\n".join(paragraphs)

    chunks = chunk_text(text, max_chars=150)

    assert len(chunks) > 1
    assert all(len(c) <= 150 for c in chunks)
    assert "".join(chunks).replace(" ", "") == text.replace("\n\n", " ").replace(" ", "")


def test_strip_html_removes_tags_and_unescapes_entities():
    raw = '<span class="qt0">Cholesterol</span> &amp; triglycerides'
    assert _strip_html(raw) == "Cholesterol & triglycerides"


def test_core_term_takes_text_before_first_comma():
    assert _core_term("Apples, raw, with skin") == "apples"
    assert _core_term("Chicken breast") == "chicken breast"


def test_closeness_key_prefers_exact_singular_plural_match_over_substring_hit():
    # "apple" is a literal substring of "Rose-apples" — a naive substring
    # check would rank it above the correctly pluralized "Apples, raw,
    # with skin" entry, which is the actual bug this ranking fixes.
    query = "apple, raw"
    exact_match = "Apples, raw, with skin"
    substring_trap = "Rose-apples, raw"

    assert _closeness_key(exact_match, query) < _closeness_key(substring_trap, query)


def test_closeness_key_deprioritizes_composite_dishes():
    query = "apple, raw"
    exact_match = "Apples, raw, with skin"
    composite_dish = "Croissants, apple"

    assert _closeness_key(exact_match, query) < _closeness_key(composite_dish, query)


def test_extract_pub_date_from_year_month():
    article = ElementTree.fromstring(
        "<PubmedArticle><Article><Journal><JournalIssue><PubDate>"
        "<Year>2024</Year><Month>03</Month></PubDate>"
        "</JournalIssue></Journal></Article></PubmedArticle>"
    )
    assert _extract_pub_date(article) == "2024-03-01"


def test_extract_pub_date_defaults_month_when_missing_or_named():
    article = ElementTree.fromstring(
        "<PubmedArticle><Article><Journal><JournalIssue><PubDate>"
        "<Year>2024</Year><Month>Nov</Month></PubDate>"
        "</JournalIssue></Journal></Article></PubmedArticle>"
    )
    assert _extract_pub_date(article) == "2024-01-01"


def test_extract_pub_date_returns_none_when_year_missing():
    article = ElementTree.fromstring("<PubmedArticle><Article><Journal><JournalIssue><PubDate/>"
                                      "</JournalIssue></Journal></Article></PubmedArticle>")
    assert _extract_pub_date(article) is None
