"""Small text repairs shared by reference-corpus ingestion and the corpus reformat tool."""

import re

# A sentence terminator glued to the next sentence ("disease.What are LDL?LDL and HDL"): punctuation after
# a letter/digit/paren and straight into a capital. Skipped when the punctuation follows a lone capital
# ("U.S.Army" abbreviations); decimals and dates ("6.1", "12.03.2026") never match because a digit follows.
_GLUED_SENTENCE_RE = re.compile(r"(?<=[A-Za-z0-9)])(?<!\b[A-Z])([.?!:])(?=[A-Z])")


def fix_sentence_spacing(text: str) -> str:
    """Insert the missing space after a sentence terminator that runs straight into the next sentence."""
    return _GLUED_SENTENCE_RE.sub(r"\1 ", text)
