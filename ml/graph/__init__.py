"""
PHIRE's Longitudinal Health Graph (docs/DATASETS_AND_GRAPH_RAG.md section 3):
Neo4j-backed storage for structured patient facts (Observation nodes),
enabling exact time-series/relational queries ("what was my most recent
LDL", "how has it changed") that vector similarity search can't answer
reliably — see ml/rag/reranker.py's documented limitation on exactly this.

Scope today: schema-guided visual extraction of patient-document data
(datalab-to/lift 9.7B VLM via ml/rag/ingest/lift_extractor.py and
ml/rag/ingest/lift_schema.py) into Observation, Medication, and Condition
nodes. Wired into ingestion (ml/rag/ingest/ingest_patient_document.py
and backend/app/services/document_processor.py) and read back into chat
answers (ml/graph/patient_context.py, via ml/chains/qa_chain.py). Not yet
implemented: LightRAG-style multi-hop graph-RAG retrieval (traversing
relationships between entities at query time, beyond the single-patient
fact lookups patient_context.py does today).
"""
