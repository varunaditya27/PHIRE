"""Unit tests for ml/llm/prompt_builder.py's context-assembly logic."""

from ml.llm.prompt_builder import MAX_CONTEXT_CHARS, build_chat_prompt
from ml.rag.retriever import Chunk


def test_build_chat_prompt_includes_observations_and_evidence():
    evidence = [Chunk(id="a", text="LDL guidance text", metadata={"source": "medlineplus"})]
    prompt = build_chat_prompt("Is my LDL high?", evidence, observations=["LDL: 162 mg/dL on 2026-03-10"])

    assert "LDL: 162 mg/dL on 2026-03-10" in prompt
    assert "LDL guidance text" in prompt
    assert "[medlineplus]" in prompt
    assert "Is my LDL high?" in prompt


def test_build_chat_prompt_handles_no_evidence():
    prompt = build_chat_prompt("Is my LDL high?", evidence=[])
    assert "No relevant evidence found." in prompt


def test_build_chat_prompt_truncates_long_context():
    evidence = [Chunk(id="a", text="word " * 5000, metadata={"source": "pubmed"})]
    prompt = build_chat_prompt("question", evidence)

    context_section = prompt.split("CONTEXT:\n")[1].split("\n\nQUESTION:")[0]
    assert len(context_section) <= MAX_CONTEXT_CHARS
    assert context_section.rstrip().endswith("...")
