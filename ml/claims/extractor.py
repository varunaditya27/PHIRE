"""
LLM-based claim extraction from generated answers.

Decomposes a draft LLM answer into discrete atomic factual claims so each
can be individually verified against evidence — claim-level, not
document-level, provenance is PHIRE's core differentiator (see
docs/FEATURES_ALIGNED.md Feature 7).
"""

import json
import re

from ml.llm.ollama_client import OllamaClient
from ml.llm.prompts import CLAIM_EXTRACTION_PROMPT

_JSON_ARRAY_RE = re.compile(r"\[.*\]", re.DOTALL)


class ClaimExtractor:
    """Wraps a local LLM call that decomposes an answer into atomic claims."""

    def __init__(self, client: OllamaClient | None = None) -> None:
        self._client = client or OllamaClient()

    def extract(self, answer: str) -> list[str]:
        """Return the atomic factual claims in answer, or [] if it has none/parsing fails."""
        if not answer.strip():
            return []
        response = self._client.generate(CLAIM_EXTRACTION_PROMPT.format(answer=answer), temperature=0.0)
        return self._parse_claims(response)

    @staticmethod
    def _parse_claims(response: str) -> list[str]:
        """Pull the JSON array out of the model's response, tolerating stray prose around it."""
        match = _JSON_ARRAY_RE.search(response)
        if not match:
            return []
        try:
            claims = json.loads(match.group(0))
        except json.JSONDecodeError:
            return []
        return [c.strip() for c in claims if isinstance(c, str) and c.strip()]
