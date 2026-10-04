"""Unit tests for ml/graph/graph_retrieval.py, conflicts.py and relations.py against a fake graph client."""

from ml.graph.conflicts import find_conflicts
from ml.graph.graph_retrieval import retrieve_graph_context
from ml.graph.relations import medications_in_class, metrics_for_condition, metrics_for_medication


class FakeGraph:
    """Returns canned rows keyed by a fragment of the query text, mirroring the real Cypher shapes."""

    def __init__(self, observations=(), medications=(), conditions=()):
        self.rows = {"HAS_OBSERVATION": list(observations), "HAS_MEDICATION": list(medications), "HAS_CONDITION": list(conditions)}

    def run(self, query, **params):
        return next(rows for key, rows in self.rows.items() if key in query)


def obs(code, raw, effective, filename, value=None, unit=None):
    return {"code": code, "raw_value": raw, "value": value, "unit": unit, "reference_range": None,
            "interpretation": None, "effective": effective, "filename": filename}


def med(code, dosage, effective, filename, status="active", frequency="daily"):
    return {"code": code, "dosage": dosage, "frequency": frequency, "status": status, "effective": effective, "filename": filename}


def cond(code, effective, filename, status="active"):
    return {"code": code, "status": status, "effective": effective, "filename": filename}


LDL = [obs("LDL Cholesterol", "138 mg/dL", "2026-03-12", "march.pdf", 138.0, "mg/dL"),
       obs("LDL Cholesterol", "126 mg/dL", "2026-06-01", "june.pdf", 126.0, "mg/dL"),
       obs("LDL Cholesterol", "112 mg/dL", "2026-09-05", "sept.png", 112.0, "mg/dL")]
HBA1C = [obs("HbA1c", "6.1 %", "2026-03-12", "march.pdf", 6.1, "%"), obs("HbA1c", "5.8 %", "2026-09-05", "sept.png", 5.8, "%")]
STATIN = med("Atorvastatin", "20 mg", "2026-03-12", "march.pdf")


def test_longitudinal_question_returns_full_history_and_overall_change_with_every_source():
    ctx = retrieve_graph_context(FakeGraph(observations=LDL + HBA1C), "How has my LDL changed over time?")

    assert ctx.linked["metrics"] == ["LDL Cholesterol"]            # HbA1c is not dragged in
    assert len(ctx.readings) == 3                                  # all three readings, not just latest-vs-previous
    summary, files = ctx.derived[0]
    assert "3 readings from 2026-03-12 to 2026-09-05" in summary and "a decrease of 26.0 mg/dL" in summary
    assert "lowest 112, highest 138" in summary
    assert files == ["june.pdf", "march.pdf", "sept.png"]


def test_medication_question_hops_to_the_metrics_it_is_followed_through():
    ctx = retrieve_graph_context(FakeGraph(observations=LDL + HBA1C, medications=[STATIN]), "How is my statin working?")

    assert ctx.linked["medications"] == ["Atorvastatin"]
    assert ctx.linked["metrics"] == ["LDL Cholesterol"]            # statin -> lipids; HbA1c untouched
    link, files = next(d for d in ctx.derived if "is followed through" in d[0])
    assert link.startswith("Medication: Atorvastatin 20 mg daily (active), documented 2026-03-12 in march.pdf, is followed through LDL Cholesterol")
    assert "138 mg/dL on 2026-03-12 → 126 mg/dL on 2026-06-01 → 112 mg/dL on 2026-09-05" in link
    assert files == ["june.pdf", "march.pdf", "sept.png"]


def test_metric_question_hops_back_to_the_drug_and_condition_that_follow_it():
    ctx = retrieve_graph_context(
        FakeGraph(observations=LDL, medications=[STATIN], conditions=[cond("Hypercholesterolemia", "2026-03-12", "march.pdf")]),
        "Why is my LDL still high?",
    )

    assert ctx.linked["medications"] == ["Atorvastatin"] and ctx.linked["conditions"] == ["Hypercholesterolemia"]


def test_blood_pressure_question_links_the_compound_reading_and_its_components():
    rows = [obs("Blood Pressure", "148/92 mmHg", "2026-03-12", "a.pdf"),
            obs("Blood Pressure (Systolic)", "148 mmHg", "2026-03-12", "a.pdf", 148.0, "mmHg"),
            obs("Blood Pressure (Diastolic)", "92 mmHg", "2026-03-12", "a.pdf", 92.0, "mmHg"), *HBA1C]

    ctx = retrieve_graph_context(FakeGraph(observations=rows), "What is my BP?")  # alias "bp"

    assert set(ctx.linked["metrics"]) == {"Blood Pressure", "Blood Pressure (Systolic)", "Blood Pressure (Diastolic)"}


def test_general_medication_question_links_every_medication():
    ctx = retrieve_graph_context(FakeGraph(medications=[STATIN, med("Metformin", "500 mg", "2026-03-12", "march.pdf")]),
                                 "What medications am I taking?")

    assert ctx.linked["medications"] == ["Atorvastatin", "Metformin"]


def test_unrelated_question_returns_none_so_the_caller_keeps_its_full_context():
    assert retrieve_graph_context(FakeGraph(observations=LDL, medications=[STATIN]), "What should I eat for breakfast?") is None


def test_short_aliases_do_not_collide_with_ordinary_words():
    rows = [obs("Potassium", "4.1 mEq/L", "2026-03-12", "a.pdf", 4.1, "mEq/L")]  # alias "k"

    assert retrieve_graph_context(FakeGraph(observations=rows), "Is it ok to take a walk?") is None


def test_conflict_needs_two_documents_disagreeing_on_the_same_day():
    rows = [obs("LDL Cholesterol", "138 mg/dL", "2026-03-12", "a.pdf"), obs("LDL Cholesterol", "142 mg/dL", "2026-03-12", "b.pdf"),
            obs("HbA1c", "6.1 %", "2026-03-12", "a.pdf"), obs("HbA1c", "5.8 %", "2026-09-05", "b.pdf")]  # later date = trend

    conflicts = find_conflicts(rows, [], [])

    assert len(conflicts) == 1
    assert conflicts[0][0] == "Conflicting records: LDL Cholesterol on 2026-03-12 is recorded as 138 mg/dL in a.pdf but 142 mg/dL in b.pdf."
    assert conflicts[0][1] == ["a.pdf", "b.pdf"]


def test_same_value_in_two_documents_is_not_a_conflict_and_medication_dose_conflicts_are_found():
    same = [obs("LDL Cholesterol", "138 mg/dL", "2026-03-12", "a.pdf"), obs("LDL Cholesterol", "138 mg/dL", "2026-03-12", "b.pdf")]
    meds = [med("Atorvastatin", "20 mg", "2026-03-12", "a.pdf"), med("atorvastatin", "40 mg", "2026-03-12", "b.pdf")]

    assert find_conflicts(same, [], []) == []
    (sentence, files), = find_conflicts([], meds, [])
    assert "medication Atorvastatin on 2026-03-12" in sentence and "20 mg daily in a.pdf" in sentence and files == ["a.pdf", "b.pdf"]


def test_conflict_question_surfaces_every_conflict_even_without_a_named_metric():
    rows = [obs("LDL Cholesterol", "138 mg/dL", "2026-03-12", "a.pdf"), obs("LDL Cholesterol", "142 mg/dL", "2026-03-12", "b.pdf")]

    ctx = retrieve_graph_context(FakeGraph(observations=rows), "Do any of my records disagree?")

    assert ctx is not None and any(d[0].startswith("Conflicting records") for d in ctx.derived)


def test_relations_registry():
    assert metrics_for_medication("Atorvastatin 20 mg")[0] == "LDL Cholesterol"
    assert "HbA1c" in metrics_for_condition("Prediabetes")
    assert metrics_for_medication("Unknownazole") == []
    assert "atorvastatin" in medications_in_class("how are my statins doing")


def test_conflict_question_with_no_conflicts_says_so_explicitly():
    from ml.graph.graph_retrieval import NO_CONFLICTS

    ctx = retrieve_graph_context(FakeGraph(observations=LDL), "Do any of my records contradict each other?")

    assert (NO_CONFLICTS, []) in ctx.derived
