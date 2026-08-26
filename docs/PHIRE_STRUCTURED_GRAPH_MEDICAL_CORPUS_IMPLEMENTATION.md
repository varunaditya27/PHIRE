# PHIRE: Structured Personal Health Graph + Medical Evidence Corpus
## Implementation Context & Required Architecture Changes

**Purpose:** This document is the implementation context for Claude Code. It consolidates the current PHIRE architecture, the existing graph/RAG implementation, and the design decisions from the latest architecture discussion.

**Primary goal:** Make PHIRE treat patient health records as structured, temporal data and use vector/lexical retrieval primarily for a separate medical knowledge/evidence corpus. The two are combined at reasoning time.

---

# 1. Core Architectural Decision

PHIRE should **not treat all medical documents as ordinary vector-RAG documents**.

Indian clinical/laboratory reports are frequently dominated by:

- tables
- key-value fields
- measurements
- reference ranges
- dates
- medication/dose fields
- structured report sections

For this type of data, semantic embedding retrieval is not the correct primary representation.

Example:

```text
LIPID PROFILE

Test                  Result       Unit       Reference
---------------------------------------------------------
Total Cholesterol     218          mg/dL      <200
Triglycerides         164          mg/dL      <150
HDL                    42           mg/dL      >40
LDL                    149          mg/dL      <100
```

This should become structured patient facts, not merely embedded chunks.

## Design principle

> **Do not embed what can be reliably structured.  
> Do not structure what is naturally textual.  
> Do not ask the LLM to retrieve what an exact database query can answer.**

Therefore PHIRE has two fundamentally different knowledge sources:

### A. Personal Health Knowledge

Answers:

> What happened to this patient?

Representation:

- Neo4j Longitudinal Health Graph
- PostgreSQL/canonical application storage where appropriate
- structured observations/events
- temporal relationships
- provenance

### B. Medical Knowledge / Evidence Corpus

Answers:

> What does established medical knowledge and literature say about this?

Representation:

- Chroma
- BM25
- embeddings
- medical textbooks
- clinical guidelines
- systematic reviews
- research papers
- other curated authoritative evidence

### C. Local LLM Reasoning Layer

Answers:

> What does the medical evidence mean in the context of this patient's actual health data?

The LLM should receive both:

```text
PERSONAL HEALTH FACTS
+
MEDICAL EVIDENCE
+
USER QUESTION / GOAL
```

and produce a grounded response.

---

# 2. Target Architecture

```text
                           USER QUERY
                               |
                               v
                    +----------------------+
                    | Query / Intent       |
                    | Understanding        |
                    +----------+-----------+
                               |
              +----------------+----------------+
              |                |                |
              v                v                v
       PERSONAL GRAPH    MEDICAL CORPUS     EXACT SEARCH
          Neo4j          Chroma + BM25       SQL / BM25
              |                |                |
              +----------------+----------------+
                               |
                               v
                    +----------------------+
                    | Evidence Assembler   |
                    |                      |
                    | patient facts        |
                    | medical evidence     |
                    | provenance           |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    | Local Medical LLM    |
                    | MedGemma / configured |
                    | local model           |
                    +----------+-----------+
                               |
                               v
                    +----------------------+
                    | Claim Extraction &   |
                    | Verification         |
                    +----------+-----------+
                               |
                               v
                  Answer + Evidence + Status
```

There is a separate ingestion/update path:

```text
                    NEW HEALTH REPORT
                           |
                           v
                  OCR / Document Parsing
                           |
              +------------+------------+
              |                         |
              v                         v
     Structured tables            Free text
              |                         |
              v                         v
     Deterministic parser             SLM
              |                         |
              +------------+------------+
                           |
                           v
                  Candidate health facts
                           |
                           v
                Metric / Entity Resolver
                           |
                           v
               Validation + Provenance
                           |
                           v
                    Neo4j MERGE
                           |
                           v
                UPDATED HEALTH GRAPH
```

The SLM is an **extraction and mapping component**, not a component that directly writes arbitrary graph relationships.

---

# 3. Why the Personal Graph Exists

Vector search is similarity-based.

It is good at:

- finding semantically related passages
- paraphrase retrieval
- finding relevant literature
- retrieving explanations
- retrieving guideline sections
- retrieving textual evidence

It is not inherently good at:

- exact numeric lookup
- temporal ordering
- comparing a patient's measurements
- determining whether two records represent the same metric
- following multi-hop relationships
- detecting explicit conflicts between records
- calculating trends
- associating medication changes with subsequent observations

Examples:

> "What was my LDL in August?"

Structured graph lookup.

> "How has my LDL changed over three years?"

Graph/time-series reasoning.

> "How did my LDL change relative to my statin dose changes?"

Graph multi-hop reasoning.

> "Why is LDL clinically important?"

Medical evidence corpus.

> "What dietary changes may help with elevated LDL?"

Personal graph + medical evidence corpus.

---

# 4. Current PHIRE Graph: Preserve and Extend It

The current implementation already has a useful foundation.

Current live shape:

```text
(:Patient {id: "self"})
      |
      +--[:HAS_OBSERVATION]--> (:Observation)
                                  |
                                  +--[:FROM_DOCUMENT]-->
                                      (:Document)
```

Current implementation characteristics:

- deterministic extraction from OCR'd HTML tables
- table headers act as schema
- 8/8 observations were successfully extracted and typed in the existing live test
- single `Patient` node (`self`) matches the current single-user local-instance model
- idempotent writes using stable IDs / `MERGE`
- typed `Medication` and `Condition` nodes: **done, shipped** (`ml/graph/medications.py`, `ml/graph/conditions.py`), extracted from free text via schema-constrained LLM extraction (`ml/graph/prose_extraction.py`)
- FHIR-inspired field naming: **done, shipped** (`code`/`value`/`effective`/`interpretation` — see `ml/graph/observations.py`)
- read path feeding chat generation and claim verification: **done, shipped** (`ml/graph/patient_context.py` — current-state facts and precomputed trend deltas)

*(Status notes above added 2026-08-26; the rest of this document describes design intent as of when it was written and is otherwise left as-is — see `docs/GRAPH_SCHEMA_ROADMAP.md` for the maintained current-state doc.)*

Do **not** throw this away.

The new architecture should build on it.

---

# 5. Target Initial Graph Schema

Keep the graph intentionally small.

## Core nodes

```text
(:Patient)

(:Document)

(:Observation)

(:Medication)

(:Condition)
```

Do not add a large hospital-scale ontology speculatively.

Potential future nodes:

```text
(:Symptom)
(:Procedure)
(:EvidenceChunk)
(:Claim)
(:ChatTurn)
(:Recommendation)
```

should be added when an actual feature/query requires them.

## Core relationships

```text
(:Patient)-[:HAS_OBSERVATION]->(:Observation)

(:Patient)-[:TAKES_MEDICATION]->(:Medication)

(:Patient)-[:HAS_CONDITION]->(:Condition)

(:Observation)-[:FROM_DOCUMENT]->(:Document)

(:Medication)-[:FROM_DOCUMENT]->(:Document)

(:Condition)-[:FROM_DOCUMENT]->(:Document)
```

*(Implemented as `HAS_MEDICATION`, not `TAKES_MEDICATION` — kept consistent
with `HAS_OBSERVATION`/`HAS_CONDITION` rather than this proposal's original
naming; see `ml/graph/medications.py`.)*

Potential later relationships:

```text
(:Observation)-[:SAME_METRIC_AS]->(:Observation)
(:Observation)-[:CONFLICTS_WITH]->(:Observation)
(:Observation)-[:SUPERSEDES]->(:Observation)

(:ChatTurn)-[:MADE_CLAIM]->(:Claim)

(:Claim)-[:SUPPORTED_BY]->(:Observation)
(:Claim)-[:SUPPORTED_BY]->(:EvidenceChunk)

(:Claim)-[:CONFLICTED_BY]->(:Observation)

(:Observation)-[:SUPPORTS]->(:Recommendation)
(:Observation)-[:CONTRAINDICATES]->(:Recommendation)
```

Do not create every derived relationship immediately. Prefer storing primitive facts and deriving trends/changes at query time.

---

# 6. Observation Schema

Use stable, normalized fields.

Recommended conceptual shape:

```json
{
  "id": "stable-observation-id",
  "patient_id": "self",
  "metric": "LDL-C",
  "display_name": "LDL Cholesterol",
  "value": 149,
  "unit": "mg/dL",
  "reference_range": "<100",
  "interpretation": "HIGH",
  "effective_date": "2026-08-14",
  "recorded_date": "2026-08-17",
  "document_id": "doc-123",
  "page_number": 2,
  "source_span": null,
  "confidence": 0.99
}
```

Important distinction:

- `effective_date`: when the health event/measurement was clinically true
- `recorded_date`: when PHIRE ingested/recorded the fact

Do not silently substitute ingestion date for clinical date when the report contains a reliable clinical date.

Formal date semantics are a separate cleanup pass if not already implemented.

---

# 7. Provenance Is Mandatory

Original documents are immutable evidence artifacts.

Normalized graph facts are derived representations.

Every graph fact should retain a route back to its source.

Conceptually:

```text
Document
   |
   +-- page
   +-- section
   +-- table
   +-- row/cell
   |
   v
Observation / Medication / Condition
```

At minimum, preserve:

```text
document_id
filename / document hash
page number where available
source section/table
source span where available
effective date
ingestion date
extraction method
confidence
```

This is essential for PHIRE's claim-level evidence attribution.

The graph should never become an opaque database of unexplained facts.

---

# 8. SLM-Driven Incremental Graph Updating

## Core decision

Use a small local SLM to identify and semantically map facts from newly ingested free text / ambiguous report fields.

Do **not** let the SLM directly execute arbitrary Neo4j mutations.

The pipeline is:

```text
Report
  |
  v
OCR / document parser (implemented: pypdf for text PDFs, olmOCR-v2 for
scanned/photographed documents -- not Docling; see ml/rag/ingest/)
  |
  +----------------------+
  |                      |
  v                      v
Structured table       Free text
  |                      |
  v                      v
Deterministic parser    SLM extractor
  |                      |
  +----------+-----------+
             |
             v
       Candidate facts
             |
             v
      Entity/metric resolver
             |
             v
       Deterministic validation
             |
             v
       Stable-ID generation
             |
             v
         Neo4j MERGE
```

## Why this split matters

For:

```text
LDL Cholesterol | 149 | mg/dL
```

do not use an LLM to understand the number.

The deterministic parser already knows:

```text
column 1 = metric
column 2 = result
column 3 = unit
```

Use the SLM for messy semantic extraction such as:

> "The patient was started on atorvastatin 20 mg once daily in March."

or:

> "Low density lipoprotein cholesterol was 143."

---

# 9. SLM Output Must Be Constrained

The SLM should return structured candidate facts, not free-form prose.

Example:

```json
{
  "observations": [
    {
      "metric_text": "Low Density Lipoprotein Cholesterol",
      "value": 143,
      "unit": "mg/dL",
      "effective_date": "2026-08-17",
      "source_span": "..."
    }
  ],
  "medications": [],
  "conditions": []
}
```

The SLM output is only a **candidate representation**.

It must pass validation before graph mutation.

---

# 10. Metric / Entity Resolution

Existing graph concepts should be provided as constrained candidates to the resolver.

Example existing concept:

```text
Concept:
LDL-C

Aliases:
- LDL
- LDL Cholesterol
- Low Density Lipoprotein
- Low-density lipoprotein cholesterol

Expected unit:
mg/dL
```

New report:

```text
Low Density Lipoprotein Cholesterol
```

SLM/resolver proposes:

```text
match -> LDL-C
confidence -> 0.99
```

Then deterministic validation checks:

```text
confidence threshold
+
unit compatibility
+
patient scope
+
valid metric type
```

Only then should Neo4j be updated.

If confidence is insufficient:

```text
UNRESOLVED
```

and preserve the original extracted text rather than forcing a bad mapping.

---

# 11. Stable IDs and Idempotent Updates

Graph updates must be safe to repeat.

Use deterministic/stable IDs based on the fact's identity.

Conceptually:

```text
observation_id =
hash(
    patient_id +
    normalized_metric +
    effective_date +
    normalized_value +
    normalized_unit +
    source_identity
)
```

Then:

```cypher
MERGE (o:Observation {id: $observation_id})
SET ...
```

Re-ingesting the same report must not create duplicate observations.

Do not use an LLM-generated arbitrary ID.

---

# 12. Example Incremental Update

Existing graph:

```text
LDL-C
├── 2024-08 → 121 mg/dL
├── 2025-08 → 137 mg/dL
└── 2026-08-14 → 149 mg/dL
```

New report:

```text
2026-08-17
LDL Cholesterol = 143 mg/dL
```

Pipeline:

```text
SLM:
"LDL Cholesterol"
        |
Resolver:
existing concept = LDL-C
        |
Validator:
unit = mg/dL -> compatible
        |
Neo4j:
MERGE Observation
```

Graph becomes:

```text
LDL-C
├── 2024-08 → 121
├── 2025-08 → 137
├── 2026-08-14 → 149
└── 2026-08-17 → 143
```

No graph rebuild is necessary.

Derived reasoning can calculate:

```text
149 -> 143
change = -6 mg/dL
```

at query time.

---

# 13. Medical Evidence Corpus

Create a separate, curated corpus whose purpose is **medical reasoning and evidence**, not storing the patient's personal measurements.

Potential source classes:

```text
Tier 1
- Clinical guidelines
- Official medical standards
- High-quality systematic reviews

Tier 2
- Authoritative medical textbooks
- Reference works

Tier 3
- Peer-reviewed research
- RCTs
- Observational studies

Tier 4
- Other vetted medical resources
```

Every corpus item should have metadata such as:

```text
source_id
title
source_type
domain
publication_date
guideline_version
authority_tier
population
license
document/page/section
```

The existing PHIRE research direction already calls for authority, recency, population relevance, provenance and guideline-version-aware evidence ranking.

Do not simply rank medical evidence by embedding similarity.

---

# 14. What Goes Into Chroma

Use Chroma primarily for the **medical evidence corpus** and naturally textual evidence.

Good candidates:

- textbook sections
- guideline sections
- systematic review passages
- journal article passages
- evidence explanations
- other curated textual medical references

Use embeddings for semantic retrieval (implemented: MedCPT dual encoder,
via transformers/torch directly, not a Sentence-Transformers model --
chosen after a 215-passage/129-query benchmark against 6 candidates
including Sentence-Transformers-based models, see
`ml/rag/experiments/RESULTS.md`).

Use BM25 alongside embeddings for exact terminology.

Examples where BM25 matters:

```text
LDL
HbA1c
TSH
Vitamin D
142 mg/dL
atorvastatin
```

Vector search handles:

```text
"What does high bad cholesterol mean?"
```

when the source uses different wording.

---

# 15. Patient Documents Are Not Automatically "Vector RAG"

Patient documents should primarily go through:

```text
PDF
  |
  v
OCR / document parser (pypdf + olmOCR-v2, not Docling)
  |
  +--> structured tables --> graph
  |
  +--> textual passages --> optional searchable evidence store
```

A textual passage from a patient's report may still be indexed for exact-source retrieval/citation.

But the **structured measurements themselves should not depend on embeddings for retrieval**.

For example:

```text
"LDL = 149 mg/dL"
```

should be available through the graph/exact structured lookup.

---

# 16. Retrieval Responsibilities

## BM25

Use for:

- exact medical terms
- exact drug names
- exact test names
- exact values
- exact phrases
- structured lexical matching

## Chroma

Use for:

- semantic similarity
- paraphrase retrieval
- medical explanations
- guideline passages
- literature evidence
- textual patient-document evidence where useful

## Neo4j

Use for:

- longitudinal questions
- temporal ordering
- patient-specific facts
- multi-hop relationships
- medication → observation relationships
- trend reconstruction
- contradiction detection
- source/provenance relationships
- structured patient state

---

# 17. Retrieval Routing

Question shape should influence retrieval.

Examples:

### "What was my LDL in August?"

Primary:

```text
Neo4j / structured lookup
```

### "What does LDL mean?"

Primary:

```text
medical corpus
Chroma + BM25
```

### "Show the report where my LDL was 149."

Primary:

```text
Neo4j exact observation
+
document provenance
```

### "How has my LDL changed over the last three years?"

Primary:

```text
Neo4j
```

### "How has my LDL changed relative to my statin dose changes?"

Primary:

```text
Neo4j multi-hop traversal
+
medical corpus if interpretation is requested
```

### "Why might my LDL be high?"

Primary:

```text
patient graph
+
medical corpus
```

### "What dietary changes might help given my current health data?"

Primary:

```text
patient graph
+
medical evidence corpus
```

### "What exercise should I focus on given my current activity and health profile?"

Primary:

```text
patient graph
+
fitness/exercise evidence corpus
```

---

# 18. Nutrition and Fitness Use the Same Medical Corpus

The medical corpus should not be limited to lab-report explanations.

It is the evidence layer for personalized wellness recommendations.

Architecture:

```text
                 PERSONAL HEALTH GRAPH
                          |
             +------------+------------+
             |                         |
             v                         v
         Nutrition                  Fitness
             |                         |
             +------------+------------+
                          |
                          v
                 MEDICAL EVIDENCE CORPUS
                          |
                          v
                  LOCAL LLM REASONING
                          |
                          v
                Evidence-backed advice
```

Examples:

```text
Patient:
LDL = 149
Weight trend = ...
Activity = ...

Medical corpus:
nutrition guidelines
cardiovascular dietary evidence
exercise guidelines
systematic reviews

Result:
personalized recommendation
+
supporting evidence
+
confidence / uncertainty
```

The corpus can also support future:

- nutrition recommendation generation
- exercise recommendations
- calorie/macro interpretation
- exercise safety/form explanations
- wellness alerts
- doctor-preparation summaries

The user's personal data remains the graph/state layer. The corpus remains the medical knowledge layer.

---

# 19. Recommendation Provenance

Recommendations should eventually be attributable too.

Conceptually:

```text
Observation
   |
   +--[:SUPPORTS]------> Recommendation
   |
   +--[:CONTRAINDICATES]-> Recommendation

Recommendation
   |
   +--[:SUPPORTED_BY]--> Medical Evidence
```

Example:

```text
LDL = 149
       |
       +------SUPPORTS------+
                            |
                            v
                 "Consider dietary changes..."
                            |
                            v
                 guideline / evidence passage
```

This reuses PHIRE's existing evidence-attribution philosophy instead of building a separate explainability mechanism for recommendations.

Do not implement `Recommendation` graph nodes unless the recommendation persistence/use case requires them.

---

# 20. Graph RAG / LightRAG Status

**Updated 2026-08-26** — resolved, not an open cross-doc inconsistency
anymore: `docs/OPEN_SOURCE_TOOLS.md`'s earlier "LightRAG + Neo4j finalized"
framing was stale documentation, not a real decision, and has been
corrected. The actual status, consistent across all current docs:

- The deterministic Neo4j graph slice (Observation/Medication/Condition
  nodes, single-patient fact lookup, precomputed trend deltas) is built,
  shipped, and live-tested — see `ml/graph/` and §4 above.
- Neo4j is queried directly via hand-written Cypher, not through LightRAG.
- **Multi-hop graph-RAG retrieval — entity/relationship traversal at query
  time — is NOT YET IMPLEMENTED. This is outstanding work that must be
  built, not an indefinitely-deferred or rejected option.** `README.md`
  and `docs/DATASETS_AND_GRAPH_RAG.md` already describe this as part of
  PHIRE's committed retrieval architecture (the third leg alongside BM25
  and Chroma), so it's not speculative scope.
- `docs/GRAPH_SCHEMA_ROADMAP.md` section 3f is the authoritative
  current-status entry for this — check it, not this document, for the
  latest state.
- Whether LightRAG specifically is the right library for this leg (vs.
  hand-written multi-hop Cypher, vs. another approach) is a separate,
  still-open implementation decision from *whether* this leg gets built.
  It does.

For the immediate architecture change in this document:

**Do not replace the existing deterministic patient graph with an LLM-generated generic graph.**

The patient graph should remain structured and controlled.

Multi-hop graph retrieval should be built around/alongside it — as its
own retrieval leg for relationship-traversal questions the deterministic
lookup can't answer — not as a replacement for the deterministic
patient-health schema.

---

# 21. Do Not Build a Giant Medical Knowledge Graph Yet

Do not initially create a hospital-scale ontology containing:

```text
Gene
Protein
Disease
Drug
Symptom
Procedure
Hospital
Doctor
Guideline
RCT
...
```

just because other medical KG systems do.

PHIRE currently has:

- one local user per instance
- one ingestion pipeline
- primarily structured patient reports

Add node types when a concrete PHIRE query/feature cannot be expressed with the existing schema.

---

# 22. Ontology Normalization

Do not immediately add the full complexity of:

- LOINC
- SNOMED CT
- UMLS
- RxNorm

unless real data demonstrates a normalization problem.

Initial approach:

```text
canonical metric
+
aliases
+
unit validation
+
SLM candidate mapping
+
deterministic validation
```

When real cross-document naming drift becomes a problem, start with the smallest useful terminology layer.

The current roadmap specifically identifies RxNorm as the likely first actionable normalization step for medications and defers larger terminology systems until the need is demonstrated.

---

# 23. Contradiction Handling

The graph should eventually make conflicts explicit.

Example:

```text
Observation A
LDL = 149
date = 2026-08-14
source = Lab Report A

Observation B
LDL = 132
date = 2026-08-14
source = Manual Entry
```

Do not silently merge these.

Possible representation:

```text
Observation A
      |
      +--[:CONFLICTS_WITH]--> Observation B
```

Then retrieval can rank sources by authority.

Example priority:

```text
lab report
>
clinical record
>
wearable
>
manual entry
```

Exact precedence rules should remain configurable.

Temporal precedence also matters.

A later corrected report may supersede an earlier record.

---

# 24. Claim Provenance and Chat History

When persistent chat history is implemented, design claim provenance at the same time.

Target shape:

```text
(:ChatTurn)
      |
      +--[:MADE_CLAIM]-->
             (:Claim)
                  |
                  +--[:SUPPORTED_BY]--> Observation
                  |
                  +--[:SUPPORTED_BY]--> EvidenceChunk
                  |
                  +--[:CONFLICTED_BY]-> Observation
```

This turns evidence attribution from an in-memory response property into persistent provenance.

Do not build this prematurely if chat turns are not yet persisted.

---

# 25. Derived Values vs. Stored Facts

Prefer storing primitive facts.

Example:

Store:

```text
LDL 2025 = 149
LDL 2026 = 143
```

Do not permanently store every derived relationship:

```text
LDL 2026 LOWER_THAN LDL 2025
LDL CHANGE = -6
LDL TREND = DOWN
```

unless there is a strong performance or product reason.

Compute these from observations at query time.

This avoids stale derived graph state.

---

# 26. Medical Corpus Ingestion Pipeline

Target:

```text
Source document
    |
    v
Parse / OCR
    |
    v
clean structured text
    |
    v
section-aware chunking
    |
    v
metadata enrichment
    |
    +--> source type
    +--> authority
    +--> publication date
    +--> guideline version
    +--> domain
    +--> population
    +--> provenance
    |
    +-------------------+
    |                   |
    v                   v
   BM25              embeddings
    |                   |
    +---------+---------+
              |
              v
           Chroma
```

Chunking should preserve:

- document title
- section
- subsection
- table context
- page
- source identity

Avoid arbitrary chunks that destroy clinical context.

---

# 27. Medical Corpus Retrieval Ranking

A future reranker should consider:

```text
final_score =
    semantic relevance
  + lexical relevance
  + authority
  + recency
  + population relevance
  + provenance quality
  + query intent
```

Do not use raw vector similarity as the final evidence ranking.

For guidelines, guideline/version metadata should be especially important.

For research questions, study design and population relevance matter.

---

# 28. End-to-End Example

User asks:

> "My LDL has been high recently. What can I do about it?"

## Step 1: Query understanding

Identify:

```text
patient-specific metric = LDL
intent = interpretation + recommendation
requires_history = yes
requires_medical_evidence = yes
```

## Step 2: Graph retrieval

Retrieve:

```text
LDL observations over time
current medications
conditions
relevant activity/nutrition observations
```

Example:

```text
2024 -> 121
2025 -> 137
2026 -> 149

Atorvastatin -> 20 mg
```

## Step 3: Medical corpus retrieval

Retrieve:

```text
relevant guideline sections
nutrition recommendations
cardiovascular evidence
relevant systematic reviews
```

## Step 4: Evidence assembly

```text
PATIENT FACTS
LDL increased from 121 -> 137 -> 149

MEDICATION CONTEXT
Atorvastatin 20 mg

MEDICAL EVIDENCE
[Guideline section]
[Systematic review]
[Relevant nutrition evidence]
```

## Step 5: Local LLM

Generate recommendation/explanation.

## Step 6: Claim extraction

Break answer into atomic claims.

## Step 7: Verification

Each claim receives one of (implemented, `ml/claims/verifier.py` +
`ml/chains/qa_chain.py`):

```text
SUPPORTED
DERIVED       (relabel of a SUPPORTED match against a precomputed trend fact)
UNCERTAIN
CONFLICTING
UNSUPPORTED
```

`INFERRED` (multi-hop reasoning beyond direct restatement or arithmetic)
is **not implemented** — no validated signal exists for it yet; a claim
requiring that kind of reasoning currently falls into `UNCERTAIN`.

## Step 8: Response

Show:

- personal measurement source
- medical evidence source
- derived calculations
- uncertainty
- exact source locations where possible

---

# 29. Implementation Changes Required

Claude Code should inspect the existing implementation before modifying anything.

## A. Preserve and improve `ml/graph/`

Inspect:

```text
ml/graph/
```

Keep:

- deterministic table extraction
- typed Observation nodes
- stable IDs
- Neo4j MERGE
- provenance

Add/refine:

- Medication node ingestion
- Condition node ingestion
- FHIR-inspired normalized field names
- effective vs recorded date support
- source metadata
- validation layer
- incremental update APIs
- metric/entity resolution

---

## B. Add an explicit extraction boundary

Recommended conceptual modules:

```text
ml/graph/
    extraction/
        table_extractor.py
        free_text_extractor.py
        schemas.py

    resolution/
        metric_resolver.py
        medication_resolver.py
        condition_resolver.py

    validation/
        fact_validator.py
        unit_validator.py

    persistence/
        neo4j_client.py
        graph_writer.py

    provenance/
        source_mapping.py
```

Do not blindly create these filenames if the current codebase has equivalent modules. Adapt to existing structure.

---

## C. SLM extraction

Implement an abstraction around the local SLM.

Responsibilities:

```text
extract free-text observations
extract medications
extract conditions
extract dates
extract dose/frequency/route
return constrained JSON
```

The model must not directly mutate the graph.

Use the configured local inference stack rather than introducing a cloud API.

---

## D. Metric resolution

Create a resolver that:

1. retrieves candidate existing metrics
2. provides candidates to the SLM or matching layer
3. obtains a proposed match + confidence
4. validates unit compatibility
5. validates type
6. accepts/rejects/marks unresolved
7. records original source text

Prefer deterministic/lexical matching first where possible, then SLM semantic mapping.

---

## E. Incremental graph update

Implement something conceptually equivalent to:

```text
ingest_report(report)
    -> parse_report()
    -> extract_facts()
    -> normalize_facts()
    -> resolve_entities()
    -> validate_facts()
    -> attach_provenance()
    -> persist_with_merge()
```

It must be idempotent.

---

# 30. RAG Changes

Inspect:

```text
ml/rag/retriever.py
```

The target architecture is:

```text
BM25
+
Chroma
+
Neo4j structured/graph retrieval
```

but retrieval should be routed by question type rather than blindly running all three for every query.

The medical corpus should become the primary semantic evidence source.

Patient structured facts should come from the graph.

Patient textual evidence may remain searchable for exact source retrieval.

---

# 31. Corpus Changes

Create a clean distinction in Chroma metadata between:

```text
source_scope = "medical_corpus"
```

and:

```text
source_scope = "patient_document"
```

Medical corpus examples:

```text
guideline
textbook
systematic_review
research_paper
```

Patient-document examples:

```text
lab_report
prescription
diagnostic_report
user_document
```

This prevents accidental mixing of patient evidence and general medical evidence during retrieval.

---

# 32. Query Context Object

Create a common internal representation before LLM generation.

Conceptually:

```json
{
  "query": "...",

  "patient_facts": [
    {
      "type": "Observation",
      "metric": "LDL-C",
      "value": 149,
      "unit": "mg/dL",
      "effective_date": "2026-08-14",
      "source": "..."
    }
  ],

  "graph_context": [],

  "medical_evidence": [
    {
      "source_id": "...",
      "title": "...",
      "section": "...",
      "text": "...",
      "authority_tier": 1
    }
  ],

  "patient_document_evidence": [],

  "derived_calculations": [],

  "conflicts": []
}
```

The LLM should reason over this assembled context instead of directly querying databases.

---

# 33. Evidence Types Must Remain Distinct

PHIRE should distinguish:

```text
DIRECT FACT
    |
    +-- extracted directly from patient source

DERIVED
    |
    +-- calculated from patient facts

MEDICAL EVIDENCE
    |
    +-- retrieved from trusted corpus

INFERENCE
    |
    +-- model interpretation

UNCERTAIN
    |
    +-- insufficient evidence

CONFLICTING
    |
    +-- sources disagree
```

Do not present model inference as a directly observed patient fact.

---

# 34. Nutrition/Fitness Architecture

Future nutrition and fitness modules should consume:

```text
Personal Health Graph
+
Medical Evidence Corpus
+
Domain-specific models/data
```

Examples:

## Nutrition

```text
patient labs
+
weight trend
+
diet logs
+
nutrition evidence
+
USDA FoodData Central
```

## Fitness

```text
activity history
+
health observations
+
exercise/fitness evidence
+
MediaPipe pose outputs
+
HAR model outputs
```

The same evidence attribution infrastructure should be reused.

---

# 35. What Not To Do

Do NOT:

- embed every lab value and depend on vector search for numerical lookup
- rebuild the entire graph whenever a new report arrives
- let an SLM directly execute arbitrary Cypher
- let an SLM invent node/relationship types
- silently merge conflicting observations
- overwrite old measurements with new ones
- treat ingestion date as clinical date
- make every document chunk a graph node
- build a giant medical ontology before actual requirements appear
- introduce SNOMED/UMLS/LOINC/RxNorm solely because they are available
- make LightRAG replace the deterministic patient-health graph
- rank medical evidence solely by embedding similarity
- treat research papers as interchangeable with clinical guidelines
- store derived trends as authoritative facts without provenance

---

# 36. Immediate Implementation Priority

**Status added 2026-08-26.** Checkboxes below reflect actual current
implementation state, cross-checked against `ml/`. Where only part of an
item is done, the note says what's missing.

## Priority 1: Patient graph correctness

- [x] Inspect current `ml/graph/`
- [x] Preserve deterministic table extraction
- [x] Confirm Observation schema
- [x] Confirm stable IDs
- [x] Confirm idempotent `MERGE`
- [x] Add/refine Medication and Condition
- [x] Add provenance fields (`document_id`, `filename`, `FROM_DOCUMENT`; exact char spans for document chunks)
- [ ] Ensure effective/recorded date semantics — `effective` date is implemented (`ml/graph/document_dates.py`); a separate `recorded_date` (ingestion date, distinct from clinical date) is explicitly deferred, see `docs/GRAPH_SCHEMA_ROADMAP.md` §3a

## Priority 2: Incremental SLM ingestion

- [x] Define constrained extraction schema (`ml/graph/prose_extraction.py`'s `EXTRACTION_SCHEMA`)
- [x] Add local SLM extraction interface (`extract_facts`)
- [x] Add metric/entity candidate resolution (`ml/graph/metric_resolver.py` — deterministic lexical matching only, by design, not SLM-based; see that module's own docstring)
- [ ] Add deterministic validation — basic value-parsing safety exists (rejects unparseable/compound values rather than guessing), but not the fuller confidence-threshold + unit-compatibility + patient-scope validation layer described in §10
- [ ] Add unresolved-fact path — an unmatched metric name currently passes through as-is (not remapped), not marked `UNRESOLVED` as a distinct tracked state
- [x] Connect validated facts to Neo4j MERGE
- [x] Add ingestion tests with repeated reports (`test_reingesting_same_document_updates_not_duplicates`)

## Priority 3: Medical evidence corpus

- [x] Define corpus directory/data model (`data/chroma`, `Chunk` + metadata)
- [x] Add source metadata (`source`, `authority`, `url`, `published_date`)
- [ ] Add section-aware chunking — paragraph-aware (`chunk_text`), not full document-section/subsection-aware as described in §26
- [x] Add BM25 index
- [x] Add Chroma embeddings
- [x] Separate medical-corpus metadata from patient-document metadata (`source` field: `pubmed`/`medlineplus`/`usda` vs. `patient_document`)
- [x] Add authority/recency metadata

## Priority 4: Hybrid retrieval

- [x] Add graph retrieval interface (`ml/graph/patient_context.py`)
- [ ] Add query routing — **not implemented.** `ml/chains/qa_chain.py` always runs BM25+Chroma retrieval *and* always fetches graph facts for every question; there's no question-shape-based routing (§17) that skips legs a question doesn't need. Related to, but distinct from, the multi-hop retrieval gap (§20) — this is about routing between existing legs, not adding a new one.
- [x] Retrieve patient facts structurally
- [x] Retrieve medical evidence semantically/lexically
- [x] Assemble unified context (`ml/llm/prompt_builder.py`'s `build_chat_prompt`)
- [x] Preserve provenance throughout (`VerifiedClaim.source_url`/`source_filename`/`source_span`)

## Priority 5: Generation/verification integration

- [x] Feed structured patient facts + medical evidence to LLM
- [ ] Preserve direct/derived/inferred distinction — direct (`SUPPORTED`) and derived (`DERIVED`) are implemented; `INFERRED` (multi-hop reasoning) is **not implemented**, see the Step 7 note above
- [x] Keep NLI-based claim verification layer (`ml/claims/verifier.py`, BART-large-MNLI — not MedRAGChecker, which isn't installable)
- [x] Return evidence links
- [x] Preserve exact source locations where available

## Priority 6: Evaluation — not started (see `docs/AGGRESSIVE_ROADMAP.md`; ArchEHR-QA evaluation is Shashwati's scope)

Add ablations:

```text
A: Dense RAG
B: BM25 + Dense RAG
C: Structured patient graph + Dense medical corpus
D: Structured graph + BM25 + Dense corpus
E: Full system + claim verification
```

Evaluate separately:

- exact factual lookup
- numerical accuracy
- longitudinal QA
- multi-hop QA
- contradiction detection
- retrieval quality
- evidence attribution
- unsupported claim rate
- recommendation grounding

---

# 37. Research Positioning

The important research contribution is **not**:

> "PHIRE uses Neo4j."

The research question is closer to:

> Does separating structured longitudinal personal health state from textual medical evidence improve healthcare question answering compared with conventional dense RAG?

Possible experimental framing:

```text
Traditional dense RAG
        vs.
Hybrid structured + semantic retrieval
        vs.
Hybrid structured + semantic + graph retrieval
```

Relevant evaluation dimensions:

- retrieval recall
- longitudinal reasoning accuracy
- calculation accuracy
- contradiction detection
- claim attribution
- hallucination/unsupported claim rate
- evidence quality
- human verification time
- latency
- local resource usage

---

# 38. Final PHIRE Mental Model

PHIRE should be understood as:

```text
                    PHIRE
                      |
        +-------------+-------------+
        |                           |
        v                           v
 PERSONAL HEALTH              MEDICAL KNOWLEDGE
    MEMORY                       / EVIDENCE
        |                           |
        v                           v
     Neo4j                    Chroma + BM25
        |                           |
        |                           |
        +-------------+-------------+
                      |
                      v
              Evidence Assembly
                      |
                      v
                Local Medical LLM
                      |
                      v
             Claim Verification
                      |
                      v
          Evidence-Attributed Answer
```

And for ingestion:

```text
New Report
    |
    v
OCR / Parsing
    |
    +----------------------+
    |                      |
Structured table        Free text
    |                      |
Deterministic parser       SLM
    |                      |
    +----------+-----------+
               |
               v
        Candidate facts
               |
               v
      Entity / Metric mapping
               |
               v
      Validation + provenance
               |
               v
          Neo4j MERGE
               |
               v
      Living Health Graph
```

The core principle is:

> **The patient's health history is a structured, temporal state. Medical knowledge is a textual evidence corpus. The LLM is the reasoning layer that connects the two.**

---

# 39. Source Context

This implementation plan is based on the current PHIRE project documents, especially:

- `docs/DATASETS_AND_GRAPH_RAG.md`
- `docs/GRAPH_SCHEMA_ROADMAP.md`
- `docs/FEATURES_ALIGNED.md`
- `docs/OPEN_SOURCE_TOOLS.md`
- `docs/AGGRESSIVE_ROADMAP.md`
- the NLP-06 research proposal

The existing project documents establish:

- BM25 + Chroma as the existing retrieval foundation
- Neo4j as the graph store for the longitudinal health graph
- deterministic table extraction as an already-working graph-ingestion component
- typed Observation/Medication/Condition representations
- provenance as a core requirement
- hybrid structured + semantic + graph retrieval as a research direction
- evidence attribution and longitudinal reasoning as core PHIRE contributions
- nutrition/fitness recommendations as evidence-backed extensions

This document adds the architectural refinement reached in the latest design discussion:

**patient reports should primarily become structured graph facts; the vector/lexical corpus should primarily serve general medical knowledge/evidence; an SLM should incrementally extract and map ambiguous new facts into the existing graph under deterministic validation; and the reasoning layer should combine patient state with medical evidence.**
