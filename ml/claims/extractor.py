"""
LLM-based claim extraction from generated answers.

Decomposes a draft LLM answer into discrete atomic factual claims so each
can be individually verified against evidence — claim-level, not
document-level, provenance is PHIRE's core differentiator (see
docs/FEATURES_ALIGNED.md Feature 7).
"""

import json

from ml.llm.ollama_client import OllamaClient
from ml.llm.prompts import CLAIM_EXTRACTION_PROMPT


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
        """Pull the JSON array out of the model's response, tolerating stray prose around it.

        Uses json.JSONDecoder.raw_decode from the first "[", not a greedy
        regex up to the last "]" — a regex match spanning from the first
        "[" to the *last* "]" in the whole response swallows any trailing
        text that happens to contain a "]" (e.g. "...claims: [...] Let me
        know if you need [more] details.") into the match, breaking JSON
        parsing and silently dropping every claim. raw_decode parses
        exactly one JSON value starting at that position and ignores
        whatever trailing text follows it.
        """
        start = response.find("[")
        if start == -1:
            return []
        try:
            claims, _ = json.JSONDecoder().raw_decode(response, start)
        except json.JSONDecodeError:
            return []
        if not isinstance(claims, list):
            return []
        return [c.strip() for c in claims if isinstance(c, str) and c.strip()]
