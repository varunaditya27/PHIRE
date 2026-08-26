"""
Best-effort clinical date extraction from a patient document's own text.

Split out of observations.py (which was pushing past CLAUDE.md's ~150-200
line file-size guideline once this grew day-first/DOB-exclusion handling)
-- shared by observations.py, medications.py, and conditions.py, so it
earns its own module rather than living inside one of its three callers.
"""

import re
from datetime import date, datetime

# Every date shape observed across the eval_data document set plus common
# clinical-document variants: ISO, dd/mm/yyyy or dd-mm-yyyy (day-first --
# see _DATE_FORMATS below for why), and "1 March 2026"/"March 1, 2026".
# A regex-only ISO match was the entire implementation before this pass
# (found via review: silently fell back to today's date for anything
# else, and worse -- picked up the *first* ISO-shaped date in the text
# regardless of what it was, see _LABEL_EXCLUDE_RE below).
_DATE_TOKEN_RE = re.compile(
    r"\b\d{4}-\d{2}-\d{2}\b"
    r"|\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"
    r"|\b\d{1,2}\s+[A-Za-z]{3,9}\.?,?\s+\d{4}\b"
    r"|\b[A-Za-z]{3,9}\.?\s+\d{1,2},?\s+\d{4}\b"
)

# PHIRE's primary audience is Indian users/clinics, where numeric dates
# are conventionally day-first (DD/MM/YYYY) -- the opposite of the US
# MM/DD/YYYY convention. An ambiguous "03/01/2026" is read as 3 January,
# not March 1st. %d-first formats are tried before %m-first ones so a
# genuinely ambiguous token resolves the Indian-convention way; an
# unambiguous token (day > 12, e.g. "14/03/2026") only ever matches one
# of these regardless of order.
_DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y",
    "%d %B %Y", "%d %b %Y", "%d %B, %Y", "%d %b, %Y",
    "%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y",
]

# A date labeled as the patient's date of birth is not this document's
# date -- found live: the eval_data "demographics_vitals" document lists
# "DOB: 1978-04-22" *before* "Visit Date: 2026-03-01" in document order,
# so a first-ISO-match search silently dated that document's vitals to
# the patient's birth year instead of the visit. Matched against the text
# immediately preceding a candidate date, case-insensitively.
_LABEL_EXCLUDE_RE = re.compile(r"(?:DOB|Date of Birth)\s*:?\s*$", re.IGNORECASE)


def _parse_date_token(token: str) -> str | None:
    """Normalize one matched date substring to ISO 'YYYY-MM-DD', or None if no known format fits."""
    token = token.strip().rstrip(".")
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(token, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def find_document_date(text: str) -> str:
    """Best-effort clinical date from the document's own text (e.g. "Date of Service: 01/03/2026").

    Skips a date-of-birth-labeled date (see _LABEL_EXCLUDE_RE) and takes
    the first remaining date in document order that parses under a known
    format (see _DATE_FORMATS, day-first for numeric dates per PHIRE's
    Indian-audience convention). Falls back to today's date if none is
    found or parses — an observation without any date is worse than one
    dated at ingestion time, since the whole point of this graph is
    time-series queries. Shared by medications.py/conditions.py too, not
    just table-derived Observations.
    """
    for match in _DATE_TOKEN_RE.finditer(text):
        preceding = text[max(0, match.start() - 25) : match.start()]
        if _LABEL_EXCLUDE_RE.search(preceding):
            continue
        parsed = _parse_date_token(match.group())
        if parsed:
            return parsed
    return date.today().isoformat()
