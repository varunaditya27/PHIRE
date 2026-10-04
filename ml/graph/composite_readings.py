"""
Composite clinical readings: one reported value that is really several numbers.

A lab/vitals document writes some readings as a single string -- "148/92
mmHg", "20/40", 5'11" -- which `_split_value` can't turn into one number, so
they were stored text-only and dropped from timelines and trends. This
registry knows the handful that are both common in patient records and
meaningful to chart (picked from LOINC/clinical-practice conventions, not a
generic "a/b" splitter, because ratios and dates also contain a slash):

- Blood pressure "S/D" (optionally with pulse): systolic + diastolic (+ heart rate)
- Visual acuity as a Snellen fraction "20/40": converted to decimal (0.5)
- Height as feet/inches "5'11\"": converted to centimetres

HbA1c "6.1 % (43 mmol/mol)" is deliberately NOT here: it is one quantity in two
units, and the first number (the %) already parses as the observation's value.
Mean arterial pressure is also left out -- it is calculated, not read.

Each handler returns an Expansion, or None when the string isn't that
composite's shape (the observation then stays exactly as before).
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from ml.graph.metric_resolver import resolve_metric

_QUALIFIER_RE = re.compile(r"^(.*?)\s*\(([^()]*)\)\s*$")

CM_PER_INCH = 2.54
INCHES_PER_FOOT = 12

_BP_RE = re.compile(
    r"^\s*(\d{2,3}(?:\.\d+)?)\s*/\s*(\d{2,3}(?:\.\d+)?)\s*(?:mm\s?hg)?\s*"
    r"(?:[,;(]\s*(?:pulse|hr|heart rate|p)?\s*[:=]?\s*(\d{2,3})\s*(?:bpm)?\s*\)?)?\s*$",
    re.IGNORECASE,
)
_SNELLEN_RE = re.compile(r"^\s*(\d{1,2})\s*/\s*(\d{1,3})\s*$")
_HEIGHT_FT_IN_RE = re.compile(
    r"^\s*(\d{1,2})\s*(?:'|ft\.?|feet|foot)\s*(?:(\d{1,2}(?:\.\d+)?)\s*(?:\"|in\.?|inch(?:es)?)?)?\s*$",
    re.IGNORECASE,
)


@dataclass
class Expansion:
    """What a composite reading turns into.

    primary: numeric (value, unit) to store on the observation itself (e.g. height in cm),
             or None to leave its own value alone (blood pressure stays text; its parts carry the numbers).
    extras:  additional observations as (code, value, unit).
    """

    primary: tuple[float, str] | None = None
    extras: list[tuple[str, float, str]] = field(default_factory=list)


def _blood_pressure(value: str, unit: str | None) -> Expansion | None:
    match = _BP_RE.match(value)
    if not match:
        return None
    systolic, diastolic, pulse = match.groups()
    unit = unit if unit and unit.lower().replace(" ", "") == "mmhg" else "mmHg"
    extras = [("Blood Pressure (Systolic)", float(systolic), unit), ("Blood Pressure (Diastolic)", float(diastolic), unit)]
    if pulse:
        extras.append(("Heart Rate", float(pulse), "bpm"))
    return Expansion(extras=extras)


def _snellen(value: str, unit: str | None) -> Expansion | None:
    match = _SNELLEN_RE.match(value)
    if not match or int(match.group(2)) == 0:
        return None
    return Expansion(primary=(round(int(match.group(1)) / int(match.group(2)), 3), "decimal"))


def _height(value: str, unit: str | None) -> Expansion | None:
    match = _HEIGHT_FT_IN_RE.match(value)
    if not match:
        return None
    feet, inches = float(match.group(1)), float(match.group(2) or 0)
    return Expansion(primary=(round((feet * INCHES_PER_FOOT + inches) * CM_PER_INCH, 1), "cm"))


# Keyed by canonical metric name (see metric_resolver.resolve_metric).
_COMPOSITES: dict[str, Callable[[str, str | None], Expansion | None]] = {
    "Blood Pressure": _blood_pressure,
    "Visual Acuity": _snellen,
    "Height": _height,
}


def _qualify(name: str, qualifier: str) -> str:
    """Fold a qualifier into a derived name: "BP (Systolic)" + "sitting" -> "BP (Systolic, sitting)"."""
    return f"{name[:-1]}, {qualifier})" if name.endswith(")") else f"{name} ({qualifier})"


def expand(code: str, value: str, unit: str | None) -> Expansion | None:
    """The Expansion for a metric's raw value, or None if it isn't a known composite shape.

    Matches on the base name, so "Visual acuity (right eye)" and "Blood Pressure (sitting)" find
    their handler; the qualifier is kept on every derived observation so the two eyes (or
    postures) stay separate series instead of overwriting each other.
    """
    qualified = _QUALIFIER_RE.match(code.strip())
    base, qualifier = (qualified.group(1), qualified.group(2).strip()) if qualified else (code, "")
    handler = _COMPOSITES.get(resolve_metric(base))
    expansion = handler(value, unit) if handler else None
    if expansion and qualifier:
        expansion.extras = [(_qualify(name, qualifier), number, u) for name, number, u in expansion.extras]
    return expansion
