"""
Combines the domain claim files (labs, medications, vitals_screening,
conditions) with their matching premises from ml/rag/experiments/eval_data
into the flat EVAL_PAIRS list run_benchmark.py consumes. See each domain
file for the authored hypotheses and ../RESULTS.md for methodology.

Each topic's premise is that topic's first passage in
ml/rag/experiments/eval_data — arbitrary but fixed, so results are
reproducible.
"""

from ml.rag.experiments.eval_data import conditions as rag_conditions
from ml.rag.experiments.eval_data import labs as rag_labs
from ml.rag.experiments.eval_data import medications as rag_medications
from ml.rag.experiments.eval_data import vitals_screening as rag_vitals_screening

from . import conditions, labs, medications, vitals_screening

_DOMAIN_PAIRS = [
    (labs, rag_labs), (medications, rag_medications),
    (vitals_screening, rag_vitals_screening), (conditions, rag_conditions),
]


def _build() -> list[dict]:
    pairs = []
    for claims_module, premises_module in _DOMAIN_PAIRS:
        for topic, claims in claims_module.CLAIMS.items():
            premise = premises_module.TOPICS[topic][0]
            for label, hypothesis in claims.items():
                pairs.append({"topic": topic, "premise": premise, "hypothesis": hypothesis, "label": label})
    return pairs


EVAL_PAIRS: list[dict] = _build()
