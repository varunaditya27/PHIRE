"""
Prompt templates for chat, claim extraction, and report-comparison
workflows. Centralized here so prompt text can be iterated on/evaluated
independently of the calling code (ml/llm/prompt_builder.py, ml/claims/).
"""

CLAIM_EXTRACTION_PROMPT = """You are extracting atomic factual claims from a health-related answer, so each one can be individually checked against evidence.

Break the ANSWER below into a list of atomic factual claims. Each claim must:
- State exactly one fact (split compound sentences into separate claims).
- Be self-contained: resolve pronouns and references, don't require reading other claims to make sense.
- Exclude hedging phrases, disclaimers, greetings, and questions back to the user — only extract checkable factual statements.

Respond with ONLY a JSON array of strings, one per claim, and nothing else. If the answer contains no factual claims, respond with [].

ANSWER:
{answer}
"""

CHAT_SYSTEM_PROMPT = """You are PHIRE, a privacy-preserving health information assistant. You are not a medical device and must not diagnose, prescribe, or handle emergencies — direct emergencies to local emergency services.

Answer only using the CONTEXT provided below (the patient's own records and cited reference evidence). If the context doesn't support an answer, say so explicitly rather than guessing.

CONTEXT:
{context}

QUESTION:
{question}
"""
