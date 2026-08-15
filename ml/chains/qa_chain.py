"""
End-to-end QA pipeline: question -> retrieve -> rerank -> generate ->
extract claims -> verify -> confidence-score -> abstain-if-unsupported ->
response.

Responsibilities (to implement):
- Orchestrate ml/rag, ml/llm, and ml/claims into the single pipeline
  backing POST /api/chat. This is the "reverse RAG" flow described in the
  project docs — every claim in the response must be traceable to
  evidence or explicit calculation.
"""
