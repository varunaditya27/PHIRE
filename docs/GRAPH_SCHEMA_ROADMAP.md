# PHIRE Longitudinal Health Graph: current state & roadmap

**Status**: Working document, not a finalized decision (contrast with
`docs/DATASETS_AND_GRAPH_RAG.md`, which is finalized). This tracks what's
actually built, what's cheap to add now, and what's deliberately deferred
— with the condition that would justify building each deferred piece,
so nothing gets built speculatively.

**Context**: Varun researched (via a separate ChatGPT deep-research pass)
how hospital-scale and MIMIC-IV-research-scale clinical knowledge graphs
are built (MediGRAF, MedGraphRAG, FHIR-Ontop-OMOP, Inselspital, patient-
centric KG literature). Claude independently verified the citations are
real (not hallucinated — checked via GitHub API, arXiv, and cross-search
against the actual publisher). The research is sound. The scope is not
PHIRE's scope, for reasons laid out below — this doc is the result of
reconciling "what's actually good" against "what PHIRE actually is."

---

## 1. Why this needed reconciling, in one sentence

Every system studied (MediGRAF/MedGraphRAG on MIMIC-IV, Inselspital's 1M-
patient/10-year hospital deployment, FHIR-Ontop-OMOP's institutional data
warehouses) solves the problem of **reconciling data that disagrees with
itself across many sources** — dozens of hospital systems each naming
"blood pressure" differently, thousands of patients, years of drift.
**PHIRE has exactly one ingestion pipeline and (today) one patient.**
There is no cross-source naming drift to reconcile yet, because there's
only one source. Building the machinery that solves that problem before
the problem exists means designing against imagined queries instead of
real ones — the exact trap the research itself warns against ("don't
throw documents at an LLM and ask it to invent a graph").

---

## 2. What's actually built and working right now

**Updated 2026-10-05** — everything in this section is shipped and
live-tested (`ml/graph/`, `ml/rag/ingest/lift_schema.py`, `ml/rag/ingest/lift_extractor.py`):

```
(:Patient {id: "self"})
      ├─[:HAS_OBSERVATION]→ (:Observation {id, code, raw_value, value, unit, reference_range, interpretation, effective})
      │                             │
      │                             └─[:FROM_DOCUMENT]→ (:Document {id, filename})
      ├─[:HAS_MEDICATION]→  (:Medication  {id, code, dosage, frequency, status, effective})
      │                             └─[:FROM_DOCUMENT]→ (:Document)
      └─[:HAS_CONDITION]→   (:Condition   {id, code, status, effective})
                                    └─[:FROM_DOCUMENT]→ (:Document)
```

FHIR-inspired field names (`code`/`value`/`effective`/`interpretation`)
are in place — this is the schema `ml/graph/observations.py`,
`medications.py`, and `conditions.py` write.

- **Unified Schema-Guided Extraction via `datalab-to/lift`**:
  Replaces previous fragile regex HTML table parsing and secondary prose LLM passes.
  `LiftExtractor` extracts `observations` (including `reference_range` and `interpretation`),
  `medications` (with `dosage`, `frequency`, `status`), and `conditions` (with `status`)
  directly from document pages in a single pass according to `CLINICAL_DOCUMENT_SCHEMA`.
- **Entity node generation**: `build_lift_observations`, `build_medications`, and
  `build_conditions` normalize metrics via `resolve_metric` and clinical dates via
  `find_document_date`, writing stable-ID nodes to Neo4j via Cypher `MERGE`.
- **Read path**: `ml/graph/patient_context.py` turns the graph's current
  state into plain-text facts fed to chat generation
  (`get_patient_facts`), a deduplicated "latest value per metric" view
  for claim verification (`get_current_patient_facts`), and precomputed
  trend deltas (`get_trend_facts`) that `ml/chains/qa_chain.py` uses to
  label a matching claim `DERIVED` rather than asking NLI to do the
  arithmetic itself. All wired into the live chat pipeline, not standalone.
- **Graph retrieval** (§3f): `ml/graph/graph_retrieval.py` links a question to metrics, medications and
  conditions, follows one hop between them, and returns histories, change summaries and conflicting records.
- **Composite readings**: `ml/graph/composite_readings.py` splits blood pressure (+ pulse) and converts Snellen
  acuity and feet-inches height into numeric observations.
- Single well-known `Patient` node (`"self"`) — matches PHIRE's actual
  single-user-per-local-instance model, not a multi-tenant assumption.
- Idempotent writes (`MERGE` on a stable id) — re-ingesting a document
  updates its Observations/Medications/Conditions rather than duplicating them.

---

## 3. Dissecting the research: what each idea actually is, and its cost

Plain-language breakdown of the concepts from Varun's research, each
rated by **what it would cost to build** vs. **what problem it actually
solves**, and the concrete signal that would mean it's time to build it.

### 3a. Event/temporal separation — *cheap, worth adopting now*

**What it is**: A fact has (at least) two dates — when it was true
clinically ("measured at"), and when the system learned about it
("recorded at"). A lab drawn on Monday but uploaded Friday has two
different dates, and conflating them corrupts trend analysis.

**Where we already do this informally**: `ml/graph/observations.py`
tries to parse a clinical date out of the document text, falling back to
"today" only if none is found — that's already the right instinct, just
not yet a formally named/consistent field across node types.

**Date handling today**: when no clinical date can be extracted, the backend no longer silently uses "today":
it stores a provisional date, flags the document `needs_date`, and the UI asks the user for the real one
(`PUT /api/documents/{id}/date` rebuilds the document's facts at that date). The formal clinical-vs-recorded
field split described below is still a separate pass.

**Cost to formalize**: trivial — rename/confirm `effective_date` (clinical)
vs. `recorded_date` (ingestion) consistently across Observation/
Medication/Condition.

**Decided 2026-08-16**: kept as its own separate pass, not bundled into
the current Medication/Condition + FHIR-naming work — revisit once
there's more real ingested data to check the date semantics against.

### 3b. Claim→evidence provenance as real graph edges — *defer, trigger-based*

**What it is**: Right now, `ml/claims/verifier.py` already tracks which
evidence chunk supports which claim — but only as an in-memory Python
object (`ClaimVerification.evidence`) that exists for the duration of one
chat response, then disappears. The research proposes persisting that
relationship as actual graph edges (`Claim -[:SUPPORTED_BY]-> Observation`)
so it survives and becomes queryable later.

**Why defer**: nothing today needs to ask "which past claims relied on
this fact" — there's no history to query yet, since claims aren't
persisted at all currently (each chat response is stateless). Building
graph persistence for claims before there's a chat history to persist
would be solving a problem that doesn't exist yet.

**Trigger to build it**: the first time a real product need shows up —
e.g., "this lab value was corrected, which past answers relied on the
wrong one?" — or when chat history itself becomes a persisted feature.

**Update 2026-08-16**: persisted chat history is confirmed coming soon
(independent decision, not yet designed). That materially changes this
item's timeline — it's no longer indefinitely deferred, it's the *next*
trigger in line. **When chat-history persistence gets designed, design
claim→evidence graph edges together with it, not as an afterthought** —
the natural persisted shape for a chat turn is arguably already
`(:ChatTurn)-[:MADE_CLAIM]->(:Claim)-[:SUPPORTED_BY]->(:Observation)`,
which only makes sense once both pieces exist. Don't design chat-history
storage first and bolt claim provenance on after.

### 3c. Ontology alignment (LOINC/SNOMED/RxNorm) — *defer, trigger-based*

**What it is**: Standardized codes so "LDL Cholesterol," "LDL-C," and
"low-density lipoprotein cholesterol" all resolve to the same underlying
concept, instead of being three different strings that don't match each
other in search or graph queries.

**Why it's real but premature**: this problem only bites when the *same*
fact appears under *different* names across *multiple* documents/sources.
Right now PHIRE ingests one document at a time from one pipeline (OCR +
one table format) — there's no naming drift to reconcile yet. Also a real
friction cost: RxNorm is free/low-friction (NLM bulk download, no
license), but SNOMED CT/UMLS require a free account and are a much larger
terminology than current scope needs.

**Trigger to build it**: the same test/medication starts appearing under
different names across multiple ingested documents, and it's causing
real, observed mismatches (e.g., a Medication node for "Lisinopril" and
another for "lisinopril 20mg" that should be the same drug don't dedupe
correctly). Start with RxNorm specifically (free, actionable) before ever
touching SNOMED/UMLS.

### 3d. Three-layer graph (personal / clinical evidence / external knowledge) — *already have it, just not as one graph*

**What it is**: MedGraphRAG's architecture separates a patient's private
data, medical literature, and terminology into three connected layers.

**Why this is already true for PHIRE, just not literally one Neo4j
instance**: `ml/graph/` (personal facts) + `ml/rag/` (evidence retrieval
over both public reference material *and* patient documents, tagged by
`source` and `authority` in Chroma's metadata) already *is* this
separation, implemented as two complementary retrieval legs rather than
one unified graph. Collapsing them into a single graph isn't obviously
better — it's a different implementation of an idea we already have,
not a missing capability.

**Recommendation**: no action. Revisit only if a specific query genuinely
can't be answered by either leg alone and needs true graph traversal
*across* both (e.g. "connect my rising LDL trend to the specific
guideline passage that explains the risk" as one traversal, not two
separate lookups) — that's a real multi-hop use case, but not one we
have evidence is needed yet.

### 3e. Additional node types (Symptom, Procedure, ExternalEvidence, Provenance) — *defer, trigger-based*

**What it is**: The research proposes 8-12 distinct node types where we
currently have (or are about to have) 5 (Patient, Document, Observation,
Medication, Condition).

**Why defer**: every one of these should earn its place by a query the
current schema literally cannot express — not by "hospital-scale systems
have this type, so we might need it too." A `Symptom` node is genuinely
different work (subjective, patient-reported, no table to parse from) —
build it when there's a real symptom-tracking feature to attach it to.

**Trigger to build each**: a specific, real query or feature request that
the current schema can't satisfy. Add node types one at a time, driven by
that need, not as a batch.

### 3f. Graph retrieval (multi-hop, longitudinal, contradiction-aware) — **implemented (2026-10-05), deterministic traversal**

**What it is**: the third retrieval leg described in `ml/rag/retriever.py`'s docstring and
`docs/DATASETS_AND_GRAPH_RAG.md`, beside BM25 and Chroma. `ml/graph/graph_retrieval.py` replaces
"dump every stored fact into the prompt" with a question-focused traversal of the Neo4j graph:

1. **Entity linking** — whole-word match of the question against metric names/aliases (via
   `metric_resolver.phrasings_for`; qualified parts such as "Blood Pressure (Systolic)" follow their base
   name), medication names and drug-class words ("statin"), and condition names. Very short aliases ("k",
   "na") are ignored so they cannot collide with ordinary words; general cues ("my medications", "my
   conditions") link all of that kind.
2. **One hop** — `ml/graph/relations.py` is a small curated "followed through" table (statin → lipid panel,
   diabetes → HbA1c/glucose, antihypertensive → blood pressure, ...): a linked drug or condition pulls in the
   metrics it is monitored through, and a linked metric pulls in the drugs/conditions that follow it ("why is
   my LDL high?" → the statin and hypercholesterolemia). These are retrieval-routing hints, **not** medical
   assertions — every claim is still verified against the stored records.
3. **Longitudinal facts** — the full history of each linked metric (not just latest-vs-previous), an overall
   change summary across all readings ("3 readings from … to …: … (overall a decrease of … ; lowest …,
   highest …)"), and "<medication/condition> … is followed through <metric> (<series>)" link sentences.
4. **Contradiction detection** (`ml/graph/conflicts.py`) — two *different documents* asserting different values
   for the same metric / medication dose / condition status on the **same clinical date**. A later value is a
   trend, not a conflict. Always computed for linked entities, and for everything when the question asks
   about disagreement; if there are none, the context says so explicitly ("No conflicting records were found…")
   so the model has something truthful to cite.

Every returned sentence carries the list of source files it rests on, and `QAChain` puts them in the
verification pool as `patient_record` / `patient_derived` chunks, so a claim built on them is cited to **all**
the documents involved (a trend lists both readings' files). When nothing in the question links, the function
returns `None` and chat keeps the previous full-context behavior. Verified live on real data: "How is my
statin working?" linked Atorvastatin → the four lipid metrics (HbA1c untouched) and answered with trend claims
citing both source documents.

**Why not LightRAG**: unchanged from `docs/DATASETS_AND_GRAPH_RAG.md` — an LLM-built entity graph would add a
dependency and an extra place for patient text to be re-interpreted by a model; the relationships needed here
(dates, values, documents, a drug-to-metric table) are already structured, so traversal is exact and every
output is traceable to stored rows.

**Not done / known limits**: the link table is small and hand-curated (add an entry when a real question needs
it); there is still no single traversal that joins the patient graph to a *guideline passage* in Chroma (the two
legs are combined in the prompt, not walked as one path — the "multi-hop across both layers" case noted in §3d);
the conflict rule only catches same-date disagreements; medications carry the document's date, not a start
date, so "relative to my medication" is a co-located timeline, not a before/after dosing analysis.

---

## 4. Summary table

| Idea | Verdict | Why |
|---|---|---|
| FHIR-ish field naming | **Done** | Shipped — see §2 |
| Typed Medication/Condition nodes | **Done** | Shipped, live-tested — see §2 |
| Graph retrieval: multi-hop / longitudinal / contradiction (deterministic traversal, no LightRAG) | **Done** (2026-10-05) | `ml/graph/graph_retrieval.py`, `relations.py`, `conflicts.py`; see §3f for scope and limits |
| Effective vs. recorded date, formalized | **Separate pass, later** (decided 2026-08-16) | Not bundled into current work; revisit with more real ingested data |
| Claim→evidence as graph edges | **Next trigger in line** (updated 2026-08-16) | Persisted chat history confirmed coming soon — design both together |
| RxNorm medication normalization | **Defer** | No cross-document naming drift observed yet; cheap when needed |
| SNOMED/UMLS condition normalization | **Defer, lower priority than RxNorm** | Heavier terminology, same "no drift yet" reasoning |
| Three-layer unified graph | **No action** | Already achieved via ml/graph + ml/rag as separate legs |
| Additional node types (Symptom, Procedure, etc.) | **Defer, one at a time** | Build per real feature need, not speculatively |
| Multi-LLM validation, research-comparison framing | **Out of scope for MVP** | Appropriate for a paper, not for shipping a feature this week |

**2026-08-16 decisions** (confirmed with Varun): date formalization stays
a separate later pass; persisted chat history is coming soon, which
promotes claim-provenance-as-graph-edges from "defer" to "design
alongside chat history when that work starts"; nothing else pulled
forward — all other deferrals keep their trigger conditions as written
above.

---

## 5. Resolved (2026-08-16)

1. Effective/recorded date formalization: **separate pass, later** — not
   bundled into the current Medication/Condition + FHIR-naming work.
2. Persisted chat history: **confirmed coming soon**, as an independent
   decision. This promotes claim→evidence graph edges from "defer
   indefinitely" to "design together when chat-history persistence is
   designed" — see the updated section 3b above.
3. Nothing pulled forward from the defer list — RxNorm/SNOMED, additional
   node types, and everything else keep their stated trigger conditions.

**Next open question, once chat-history persistence design actually
starts**: what does a persisted chat turn look like, and does claim
provenance attach to it as `(:ChatTurn)-[:MADE_CLAIM]->(:Claim)`, or does
`Claim` need its own identity independent of any specific turn (e.g. if
the same claim gets re-asserted across multiple conversations)? Not
answerable yet — surface it when that design work begins.
