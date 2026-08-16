"""
Eval queries for reranker weight tuning: "patient-fact" queries (the
correct top result is the patient's own ingested document, authority
1.0) vs. "general-topic" queries (the correct top result is public
reference material, authority 0.7-0.9) over the same real corpus.

Grounded in what's actually ingested this session (see
ml/rag/ingest/experiments/eval_data for the source documents, and
ml/rag/ingest/run_ingest.py's CLINICAL_TOPICS for the reference corpus
topics) rather than invented queries — verified live that both sides of
each pair have real matching content in the corpus before authoring this.
"""

QUERIES = [
    # Patient-fact: the patient's own record should rank first.
    {"query": "What is my potassium level?", "category": "patient_fact"},
    {"query": "What is my creatinine level?", "category": "patient_fact"},
    {"query": "Am I currently taking lisinopril?", "category": "patient_fact"},
    {"query": "what was my LDL cholesterol result?", "category": "patient_fact"},
    # General-topic: public reference material should rank first --
    # nothing in the patient's own record answers "why"/"what causes"
    # questions, only their own values.
    {"query": "What causes chronic kidney disease?", "category": "general_topic"},
    {"query": "Why is LDL cholesterol considered bad for you?", "category": "general_topic"},
    {"query": "What medicines treat high blood pressure?", "category": "general_topic"},
    {"query": "How can I lower my cholesterol through diet?", "category": "general_topic"},
]

# Round 1 (floor=False throughout): found that no weight config fixes
# the patient-fact miss without hurting general-topic accuracy — see
# RESULTS.md. Round 2 adds the structural fix (Reranker's
# enable_patient_floor) on top of the current weights, tested against the
# same weight-only baseline to isolate its effect.
WEIGHT_CONFIGS = [
    {"name": "current (0.6/0.25/0.15), floor off", "relevance": 0.6, "authority": 0.25, "recency": 0.15, "floor": False},
    {"name": "authority_boost_moderate (0.5/0.35/0.15), floor off", "relevance": 0.5, "authority": 0.35, "recency": 0.15, "floor": False},
    {"name": "authority_boost_strong (0.45/0.40/0.15), floor off", "relevance": 0.45, "authority": 0.40, "recency": 0.15, "floor": False},
    {"name": "relevance_only (0.85/0.0/0.15), floor off", "relevance": 0.85, "authority": 0.0, "recency": 0.15, "floor": False},
    {"name": "current (0.6/0.25/0.15), floor ON", "relevance": 0.6, "authority": 0.25, "recency": 0.15, "floor": True},
]
