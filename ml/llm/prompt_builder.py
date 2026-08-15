"""
Assembles context + prompt for the local LLM from retrieved evidence and
structured observations.

Responsibilities (to implement):
- Merge retriever.py results + patient timeline data into a bounded-length
  prompt, respecting the model's context window.
"""
