import re
from enum import Enum
from typing import Optional

class Intent(str, Enum):
    DATA_LOOKUP = "DATA_LOOKUP"
    TREND_ANALYSIS = "TREND_ANALYSIS"
    HEALTH_INTERPRETATION = "HEALTH_INTERPRETATION"
    DIAGNOSIS_REQUEST = "DIAGNOSIS_REQUEST"
    TREATMENT_REQUEST = "TREATMENT_REQUEST"
    GENERAL_HEALTH = "GENERAL_HEALTH"
    UNSUPPORTED_PERSONAL_QUERY = "UNSUPPORTED_PERSONAL_QUERY"
    EMERGENCY = "EMERGENCY"

_DIAGNOSIS_PATTERNS = [
    r"\\bdo i have\\b",
    r"\\bam i diagnosed with\\b",
    r"\\bis it (possible|likely) that i have\\b",
    r"\\bdiagnose\\b",
]
_TREATMENT_PATTERNS = [
    r"\\bshould i start\\b",
    r"\\bshould i take\\b",
    r"\\bshould i use\\b",
    r"\\bprescribe\\b",
]
_TREND_PATTERNS = [
    r"\\bhas my .* increased\\b",
    r"\\bhow has my .* changed\\b",
    r"\\btrend\\b",
]
_INTERPRETATION_PATTERNS = [
    r"\\bis my .* (high|low|normal)\\b",
    r"\\bwhat does my .* mean\\b",
]
_GENERAL_HEALTH_PATTERNS = [
    r"\\bwhat is\\b",
    r"\\bexplain\\b",
]
_EMERGENCY_PATTERNS = [
    r"\\bchest pain\\b",
    r"\\bshortness of breath\\b",
    r"\\bemergency\\b",
]

def _match_any(patterns, text: str) -> bool:
    return any(re.search(pat, text, flags=re.IGNORECASE) for pat in patterns)

def classify_intent(question: str) -> Intent:
    q = question.strip().lower()
    if _match_any(_EMERGENCY_PATTERNS, q):
        return Intent.EMERGENCY
    if _match_any(_DIAGNOSIS_PATTERNS, q):
        return Intent.DIAGNOSIS_REQUEST
    if _match_any(_TREATMENT_PATTERNS, q):
        return Intent.TREATMENT_REQUEST
    if _match_any(_TREND_PATTERNS, q):
        return Intent.TREND_ANALYSIS
    if _match_any(_INTERPRETATION_PATTERNS, q):
        return Intent.HEALTH_INTERPRETATION
    if _match_any(_GENERAL_HEALTH_PATTERNS, q):
        return Intent.GENERAL_HEALTH
    if re.search(r"latest|last|most recent|current", q) and re.search(r"hb[a]?1c|ldl|glucose|blood pressure|weight|height|temperature", q):
        return Intent.DATA_LOOKUP
    return Intent.UNSUPPORTED_PERSONAL_QUERY
