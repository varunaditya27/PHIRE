"""
Graph retrieval: the question-focused third leg beside BM25 and Chroma.

Instead of dumping every stored fact into the prompt, this links the question to graph entities
(metrics, medications, conditions), follows one hop through ml/graph/relations.py (a statin ->
LDL), and returns the facts that answer longitudinal, relational and contradiction questions:

  - the full history of each linked metric, and its overall change (not just latest-vs-previous);
  - medication/condition -> metric links ("Atorvastatin ... is followed through LDL ...");
  - conflicting records (conflicts.py), always for linked entities and for everything when the
    question asks about disagreement.

Deterministic Neo4j traversal rather than an LLM-built entity graph (LightRAG was evaluated and not
adopted -- docs/DATASETS_AND_GRAPH_RAG.md): patient data never leaves the local boundary and every
returned sentence is traceable to stored rows. Returns None when nothing in the question links,
so the caller keeps its existing full-context behavior.
"""

import re
from dataclasses import dataclass, field

from ml.graph.client import GraphClient
from ml.graph.conflicts import find_conflicts
from ml.graph.metric_resolver import phrasings_for, resolve_metric
from ml.graph.observations import DEFAULT_PATIENT_ID
from ml.graph.patient_context import (
    fetch_conditions, fetch_medications, fetch_observations,
    format_medication, format_observation,
)
from ml.graph.relations import medications_in_class, metrics_for_condition, metrics_for_medication

CONFLICT_CUES = ("conflict", "disagree", "inconsisten", "discrepan", "contradict", "mismatch", "differ")
ALL_MEDICATION_CUES = ("medication", "medicine", "drug", "pill", "prescri")
ALL_CONDITION_CUES = ("condition", "diagnos", "disease")
MAX_FACTS = 60
NO_CONFLICTS = "No conflicting records were found: no two documents disagree about the same metric, medication or condition on the same date."
_SHORT_ALIASES_ALLOWED = {"bp", "hr"}

Sourced = tuple[str, list[str]]  # (sentence, source filenames)


@dataclass
class GraphContext:
    """What the graph contributes to one question: readings, graph-derived sentences, and what was linked."""

    readings: list[Sourced] = field(default_factory=list)   # stored facts for the linked entities
    derived: list[Sourced] = field(default_factory=list)    # computed by the graph: series, links, conflicts
    linked: dict[str, list[str]] = field(default_factory=dict)  # {"metrics": [...], "medications": [...], "conditions": [...]}

    def prompt_lines(self) -> list[str]:
        """Every sentence, readings first, for the generation prompt."""
        return [s for s, _ in self.readings] + [s for s, _ in self.derived]


def _mentions(question: str, phrase: str) -> bool:
    """Whole-word (optionally plural) match of `phrase` in the lowercase question.

    Very short aliases ("k", "na", "ca") collide with ordinary words, so only a couple of well-known
    abbreviations ("bp", "hr") are allowed under three characters.
    """
    if len(phrase) < 3 and phrase not in _SHORT_ALIASES_ALLOWED:
        return False
    return re.search(rf"\b{re.escape(phrase)}s?\b", question) is not None


def _base(code: str) -> str:
    """Metric name without a trailing qualifier: "Blood Pressure (Systolic)" -> "Blood Pressure"."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", code)


def _link_metrics(question: str, codes: set[str]) -> set[str]:
    """Graph metric codes the question mentions by name or alias (qualified parts follow their base name)."""
    return {
        code for code in codes
        if any(_mentions(question, p) for p in {_base(code).lower(), *phrasings_for(resolve_metric(_base(code)))})
    }


def _link_rows(question: str, rows: list[dict], all_cues: tuple[str, ...], extra_names: list[str]) -> set[str]:
    """Codes of medication/condition rows the question names (or all of them, if it asks about them in general)."""
    if any(cue in question for cue in all_cues):
        return {r["code"] for r in rows}
    return {r["code"] for r in rows if _mentions(question, r["code"].lower()) or any(n in r["code"].lower() for n in extra_names)}


def _series(rows: list[dict]) -> str:
    """"138 mg/dL on 2026-03-12 → 112 mg/dL on 2026-09-05"."""
    return " → ".join(f"{r['raw_value']} on {r['effective']}" for r in rows)


def _summary(code: str, rows: list[dict]) -> Sourced | None:
    """Overall change across a metric's readings (needs >= 2 numeric ones)."""
    numeric = [r for r in rows if r.get("value") is not None]
    if len(numeric) < 2:
        return None
    first, last = numeric[0], numeric[-1]
    delta = last["value"] - first["value"]
    direction = "an increase" if delta > 0 else "a decrease" if delta < 0 else "no change"
    unit = f" {last['unit']}" if last.get("unit") else ""
    values = [r["value"] for r in numeric]
    text = (f"{code} has {len(numeric)} readings from {first['effective']} to {last['effective']}: {_series(numeric)} "
            f"(overall {direction} of {abs(delta):.1f}{unit}; lowest {min(values):g}, highest {max(values):g}).")
    return text, sorted({r["filename"] for r in numeric if r.get("filename")})


def _link_sentence(label: str, row: dict, metrics: list[str], by_code: dict[str, list[dict]]) -> Sourced | None:
    """"<med/condition> ... is followed through <metric> (<series>)": the hop that joins two kinds of node."""
    present = [m for m in metrics if by_code.get(m)]
    if not present:
        return None
    followed = "; ".join(f"{m} ({_series(by_code[m])})" for m in present)
    where = f", documented {row['effective']} in {row['filename']}," if row.get("filename") and row.get("effective") else ""
    files = {row["filename"]} if row.get("filename") else set()
    files |= {r["filename"] for m in present for r in by_code[m] if r.get("filename")}
    return f"{label}{where} is followed through {followed}.", sorted(files)


def retrieve_graph_context(
    client: GraphClient, question: str, patient_id: str = DEFAULT_PATIENT_ID,
) -> GraphContext | None:
    """The graph facts relevant to `question`, or None when nothing in it links to the patient's records."""
    q = question.lower()
    observations = fetch_observations(client, patient_id)
    medications, conditions = fetch_medications(client, patient_id), fetch_conditions(client, patient_id)
    by_code: dict[str, list[dict]] = {}
    for row in observations:
        by_code.setdefault(row["code"], []).append(row)

    metrics = _link_metrics(q, set(by_code))
    meds = _link_rows(q, medications, ALL_MEDICATION_CUES, medications_in_class(q))
    conds = _link_rows(q, conditions, ALL_CONDITION_CUES, [])
    wants_conflicts = any(cue in q for cue in CONFLICT_CUES)
    if not (metrics or meds or conds or wants_conflicts):
        return None

    # One hop: a linked drug/condition pulls in the metrics it is followed through, and a linked metric
    # pulls in the drugs/conditions that follow it ("why is my LDL high?" -> statin, hypercholesterolemia).
    hop = {m for r in medications if r["code"] in meds for m in metrics_for_medication(r["code"])}
    hop |= {m for r in conditions if r["code"] in conds for m in metrics_for_condition(r["code"])}
    metrics |= {code for code in by_code if code in hop or _base(code) in hop}
    followed = metrics | {_base(m) for m in metrics}
    meds |= {r["code"] for r in medications if followed & set(metrics_for_medication(r["code"]))}
    conds |= {r["code"] for r in conditions if followed & set(metrics_for_condition(r["code"]))}

    context = GraphContext(linked={"metrics": sorted(metrics), "medications": sorted(meds), "conditions": sorted(conds)})
    for code in sorted(metrics):
        rows = by_code[code]
        context.readings += [(format_observation(r), [r["filename"]] if r.get("filename") else []) for r in rows]
        if summary := _summary(code, rows):
            context.derived.append(summary)
    for rows, codes, fmt, kind in ((medications, meds, format_medication, "Medication"), (conditions, conds, None, "Condition")):
        for row in rows:
            if row["code"] not in codes:
                continue
            sentence = fmt(row) if fmt else f"Condition: {row['code']} ({row['status']})."
            context.readings.append((sentence, [row["filename"]] if row.get("filename") else []))
            related = metrics_for_medication(row["code"]) if kind == "Medication" else metrics_for_condition(row["code"])
            if link := _link_sentence(sentence.removesuffix("."), row, related, by_code):
                context.derived.append(link)

    focus = None if wants_conflicts else {c.lower() for c in metrics | meds | conds}
    conflicts = find_conflicts(observations, medications, conditions, focus)
    context.derived += conflicts
    if wants_conflicts and not conflicts:
        # Without this the model has nothing to cite for "no", and tends to just list unrelated facts.
        context.derived.append((NO_CONFLICTS, []))
    context.readings, context.derived = context.readings[:MAX_FACTS], context.derived[:MAX_FACTS]
    return context
