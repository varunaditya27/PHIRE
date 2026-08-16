"""
Scoring for the reranker weight-tuning experiment: does the top-ranked
(and top-3) result come from the expected source type for each query
category? Simple hit-rate, not a graded relevance metric — the question
here is specifically "does authority weighting flip the winner," which a
binary hit/miss answers directly.
"""

EXPECTED_SOURCE_BY_CATEGORY = {
    "patient_fact": "patient_document",
    "general_topic": {"medlineplus", "pubmed"},
}


def _matches_expected(source: str, category: str) -> bool:
    expected = EXPECTED_SOURCE_BY_CATEGORY[category]
    return source in expected if isinstance(expected, set) else source == expected


def hit_at_1(ranked_sources: list[str], category: str) -> bool:
    """Whether the top-ranked chunk's source matches the expected type for this query category."""
    return bool(ranked_sources) and _matches_expected(ranked_sources[0], category)


def hit_at_3(ranked_sources: list[str], category: str) -> bool:
    """Whether any of the top-3 chunks' sources match the expected type for this query category."""
    return any(_matches_expected(source, category) for source in ranked_sources[:3])
