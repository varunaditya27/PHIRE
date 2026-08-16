"""
PHIRE's Longitudinal Health Graph (docs/DATASETS_AND_GRAPH_RAG.md section 3):
Neo4j-backed storage for structured patient facts (Observation nodes),
enabling exact time-series/relational queries ("what was my most recent
LDL", "how has it changed") that vector similarity search can't answer
reliably — see ml/rag/reranker.py's documented limitation on exactly this.

Scope today: deterministic extraction of tabular patient-document data
(ml/rag/ingest/table_parsing.py) into Observation nodes. LightRAG-style
LLM-based entity/relationship extraction for free-text sections and the
broader multi-hop graph-RAG retrieval leg are not implemented yet.
"""
