"""
Combines all domain topic files (labs, medications, vitals_screening,
conditions) into the flat PASSAGES/QUERIES structures run_benchmark.py
consumes. See each domain file for the authored content and
../RESULTS.md for methodology.

A query's relevant set is every passage under its topic (relevance is by
topic-group membership, assigned here, not a subjective per-pair label).
"""

from . import conditions, labs, medications, vitals_screening

_DOMAIN_MODULES = [labs, medications, vitals_screening, conditions]


def _build() -> tuple[list[dict], list[dict]]:
    passages: list[dict] = []
    topic_to_ids: dict[str, list[str]] = {}
    next_id = 1
    for module in _DOMAIN_MODULES:
        for topic, texts in module.TOPICS.items():
            ids = []
            for text in texts:
                passage_id = f"p{next_id:03d}"
                passages.append({"id": passage_id, "text": text})
                ids.append(passage_id)
                next_id += 1
            topic_to_ids[topic] = ids

    queries: list[dict] = []
    for module in _DOMAIN_MODULES:
        for topic, text in module.QUERIES:
            queries.append({"text": text, "relevant_ids": topic_to_ids[topic]})
    return passages, queries


PASSAGES, QUERIES = _build()
