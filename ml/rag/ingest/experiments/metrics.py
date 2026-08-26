"""
Scoring for the OCR model-selection benchmark: character/word error rate
(standard OCR metrics) plus field-level accuracy — whether each clinically
critical value (a lab result, a dosage) actually appears correctly in the
output. Field accuracy matters more for this project's purpose than raw
CER: a transcription that garbles a footer but gets every lab value right
is safe to ingest; one with low overall CER but a flipped digit in "162
mg/dL" is not.

Also scores a markup-normalized CER/WER (see strip_markup) alongside the
raw ones: olmOCR's own prompt instructs it to convert tables to HTML, and
raw CER against plain-text ground truth then penalizes a model for
correctly following that instruction — verified live, where olmOCR-v2
(which reliably emits HTML tables) scored a much worse raw CER than
olmOCR-v1 (which tends to emit compact Markdown tables closer in
character count to plain text) despite both extracting the same content
correctly per field_accuracy. Markup-normalized CER strips both styles
before comparing, so it measures content fidelity, not the model's
literal formatting choice.
"""

import re

_MARKUP_RE = re.compile(r"<[^>]+>|[|]|-{2,}")


def _levenshtein(a: list, b: list) -> int:
    """Standard edit-distance DP, operating on a list of tokens (chars or words)."""
    if not a:
        return len(b)
    if not b:
        return len(a)
    previous = list(range(len(b) + 1))
    for i, a_item in enumerate(a, start=1):
        current = [i] + [0] * len(b)
        for j, b_item in enumerate(b, start=1):
            cost = 0 if a_item == b_item else 1
            current[j] = min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost)
        previous = current
    return previous[-1]


def character_error_rate(hypothesis: str, reference: str) -> float:
    """Edit distance over characters, normalized by reference length."""
    if not reference:
        return 0.0 if not hypothesis else 1.0
    return _levenshtein(list(hypothesis), list(reference)) / len(reference)


def word_error_rate(hypothesis: str, reference: str) -> float:
    """Edit distance over whitespace-split words, normalized by reference word count."""
    ref_words = reference.split()
    if not ref_words:
        return 0.0 if not hypothesis.split() else 1.0
    return _levenshtein(hypothesis.split(), ref_words) / len(ref_words)


def strip_markup(text: str) -> str:
    """Remove HTML tags and Markdown table syntax (pipes, header-separator dashes), collapse whitespace.

    Not a full HTML/Markdown parser — good enough to make "<td>138</td>"
    and "| 138 |" compare fairly against plain-text ground truth without
    needing ground truth authored in either markup style.
    """
    return re.sub(r"\s+", " ", _MARKUP_RE.sub(" ", text)).strip()


def content_character_error_rate(hypothesis: str, reference: str) -> float:
    """CER after stripping HTML/Markdown table markup from both sides — see module docstring."""
    return character_error_rate(strip_markup(hypothesis), strip_markup(reference))


def content_word_error_rate(hypothesis: str, reference: str) -> float:
    """WER after stripping HTML/Markdown table markup from both sides — see module docstring."""
    return word_error_rate(strip_markup(hypothesis), strip_markup(reference))


def field_accuracy(hypothesis: str, key_fields: dict[str, str]) -> float:
    """Fraction of key_fields whose expected value appears near its label in hypothesis.

    Whitespace- and case-normalized substring match, not exact-position — OCR output line breaks/spacing don't always match the source exactly, and that's fine as long as the label and value are both recoverable.
    """
    normalized = re.sub(r"\s+", " ", hypothesis).lower()
    hits = 0
    for label, value in key_fields.items():
        label_norm = label.lower()
        value_norm = re.sub(r"\s+", " ", value).lower()
        if label_norm in normalized and value_norm in normalized:
            hits += 1
    return hits / len(key_fields) if key_fields else 0.0
