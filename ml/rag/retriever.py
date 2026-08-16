"""
Hybrid retrieval over ingested documents + trusted reference sources.

Retrieval is three-way, not two-way (finalized decision, see
docs/DATASETS_AND_GRAPH_RAG.md):
1. Lexical (BM25, via rank_bm25) — catches exact lab-value/term matches
   that embeddings can miss.
2. Semantic (dense embedding, Chroma in-process vector store) — catches
   paraphrase/similarity matches BM25 misses.
3. Graph traversal (LightRAG over a Neo4j-backed entity/relationship
   graph) — catches multi-hop and relational queries neither of the above
   can answer from similarity alone, e.g. "how did my LDL change relative
   to my statin dose changes" or "which of my records conflict." The
   graph is the natural home for PHIRE's Longitudinal Health Graph
   (Observation/Medication/Condition nodes with temporal + provenance
   edges) already sketched in the architecture docs — a graph edge IS an
   evidence/provenance link, not just a similarity score.

Route by question shape: single-hop lookups -> vector/lexical; trend,
comparison, and contradiction-surfacing questions -> graph traversal,
optionally fused with vector results for supporting passages.

Responsibilities (to implement):
- Combine lexical (BM25) and semantic (dense embedding) search as above.
- Vector backend: Chroma, run in-process (not a Docker container).
- Embeddings via Sentence-Transformers (candidates: allenai-specter,
  pubmedbert, msmarco-distilbert-base-v4).
- Graph backend: LightRAG (Ollama-native local entity/relation
  extraction — keeps PHI on-device) over Neo4j (self-hosted community
  edition) for the third retrieval leg.
- Returns ranked evidence passages consumed by ml/chains/qa_chain.py.
"""
