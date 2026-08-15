"""
POST /api/chat — conversational Q&A endpoint.

Responsibilities (to implement):
- Accept a user question, call into the ML layer (ml/chains/qa_chain.py)
  with retrieved evidence + structured observations as context.
- Stream the LLM response back to the frontend.
- Response must include claim-level evidence attribution (see
  models/claim.py), not just free text — this is PHIRE's core
  differentiator versus a plain chatbot.
"""
