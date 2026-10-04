"""
Contradiction detection over the patient graph: records that disagree about the same thing.

A conflict needs two *different documents* asserting different values for the same fact at the same
clinical date (same metric on the same day, same medication on the same day, same condition on the same
day). A changed value on a later date is a trend, not a conflict, and is never reported here. Pure
functions over graph rows, so they are unit-testable without Neo4j.
"""

from collections import defaultdict


def _group(rows: list[dict], key: tuple[str, ...], value_of) -> dict[tuple, dict[str, str]]:
    """Group rows by `key` fields -> {source filename: value}; rows without a filename or date are skipped."""
    groups: dict[tuple, dict[str, str]] = defaultdict(dict)
    for row in rows:
        if not row.get("filename") or not row.get("effective"):
            continue
        groups[tuple(str(row[k]).lower() if k == "code" else row[k] for k in key)][row["filename"]] = value_of(row)
    return groups


def _sentence(subject: str, date: str, by_file: dict[str, str]) -> tuple[str, list[str]]:
    """The conflict sentence plus the files involved."""
    parts = " but ".join(f"{value} in {name}" for name, value in sorted(by_file.items()))
    return f"Conflicting records: {subject} on {date} is recorded as {parts}.", sorted(by_file)


def find_conflicts(
    observations: list[dict], medications: list[dict], conditions: list[dict], codes: set[str] | None = None,
) -> list[tuple[str, list[str]]]:
    """(sentence, source filenames) per conflict; `codes` (lowercase) restricts it to those metrics/drugs/conditions."""
    found: list[tuple[str, list[str]]] = []
    spec = [
        (observations, lambda r: r["raw_value"], lambda c, d: f"{c}"),
        (medications, lambda r: " ".join(filter(None, [r.get("dosage"), r.get("frequency")])) or "no dose recorded",
         lambda c, d: f"medication {c}"),
        (conditions, lambda r: str(r.get("status")), lambda c, d: f"the status of {c}"),
    ]
    for rows, value_of, describe in spec:
        names: dict[str, str] = {}
        for r in rows:
            names.setdefault(str(r["code"]).lower(), r["code"])  # first-seen casing for display
        for (code, date), by_file in _group(rows, ("code", "effective"), value_of).items():
            if codes is not None and code not in codes:
                continue
            if len(by_file) > 1 and len(set(by_file.values())) > 1:
                found.append(_sentence(describe(names[code], date), date, by_file))
    return found
