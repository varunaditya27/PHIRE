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

# A local model occasionally emits a malformed \u escape inside its JSON
# output (well-formed-but-double-escaped, or the hex digits dropped
# entirely) -- either breaks json.JSONDecoder outright, silently zeroing
# every claim for an otherwise-fine answer (found live: a patient fact
# sentence containing one flowed straight through generation into this
# parse). Decode well-formed escapes to the real character and strip
# anything malformed as noise, same fix as
# ml/rag/ingest/gemini_extractor.py's _fix_double_escaped_unicode, before
# ever handing the text to the JSON parser.
_DOUBLE_ESCAPED_UNICODE_RE = re.compile(r"\\u([0-9a-fA-F]{4})")
_STRAY_BACKSLASH_U_RE = re.compile(r"\\u")


def _sanitize_unicode_escapes(text: str) -> str:
    fixed = _DOUBLE_ESCAPED_UNICODE_RE.sub(lambda m: chr(int(m.group(1), 16)), text)
    return _STRAY_BACKSLASH_U_RE.sub("", fixed)


class ClaimExtractor:
    """Wraps a local LLM call that decomposes an answer into atomic claims."""

    def __init__(self, client: OllamaClient | None = None) -> None:
        self._client = client or OllamaClient()

    def extract(self, answer: str) -> list[str]:
        """Return the atomic factual claims in answer, or [] if it has none/parsing fails."""
        if not answer.strip():
            return []
        # A JSON list of short claim strings never needs anywhere near the
        # default budget -- tighter cap bounds worst-case latency for this
        # call specifically (see OllamaClient.generate's docstring for why
        # a cap exists at all).
        response = self._client.generate(
            CLAIM_EXTRACTION_PROMPT.format(answer=answer), temperature=0.0, max_tokens=400
        )
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
        response = _sanitize_unicode_escapes(response)
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
