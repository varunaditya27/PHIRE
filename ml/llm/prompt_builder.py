"""
Assembles context + prompt for the local LLM from retrieved evidence and
patient observations.

observations is typed as list[str], not a structured Observation object —
Anika's backend owns the Observation entity's actual schema (PostgreSQL,
per REPO_STRUCTURE.md), which isn't finalized yet. Formatting an
Observation into a description string is the caller's responsibility;
this module only bounds and merges already-formatted text.
"""

from ml.llm.prompts import CHAT_SYSTEM_PROMPT
from ml.rag.retriever import Chunk

# Leaves headroom in medgemma:4b/qwen2:7b's context window for the
# question, system prompt, and the model's own answer.
MAX_CONTEXT_CHARS = 6000


def build_chat_prompt(question: str, evidence: list[Chunk], observations: list[str] | None = None) -> str:
    """Merge retrieved evidence chunks + patient observation strings into a bounded context block."""
    context_parts = [f"[patient record] {obs}" for obs in (observations or [])]
    context_parts += [f"[{chunk.metadata.get('source', 'reference')}] {chunk.text}" for chunk in evidence]

    context = _truncate("\n\n".join(context_parts), MAX_CONTEXT_CHARS)
    return CHAT_SYSTEM_PROMPT.format(context=context or "No relevant evidence found.", question=question)


def _truncate(text: str, max_chars: int) -> str:
    """Cut at a word boundary rather than mid-token if the merged context runs over budget."""
    if len(text) <= max_chars:
        return text
    # Reserve room for the "..." suffix up front, so the result never
    # exceeds max_chars even after it's appended back on.
    return text[: max_chars - 3].rsplit(" ", 1)[0] + "..."
