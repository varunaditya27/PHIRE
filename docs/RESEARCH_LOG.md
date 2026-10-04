# PHIRE Research Log: `ml/` correctness pass and live pipeline validation

**Purpose of this doc**: a running, dated record of substantive findings
from working on `ml/` — the reasoning behind non-obvious design decisions,
and concrete evidence from live testing (not synthetic/mocked) — kept in
a form that's directly reusable when drafting a paper later, so this
doesn't need to be re-derived from git history and code inspection from
scratch. Not a changelog of every commit; only entries with a "why" or an
empirical result worth keeping. Append new dated sections; don't rewrite
old ones except to correct an error.

**Audience for the eventual paper**: PHIRE's primary target audience is
Indian users and clinics — several entries below (e.g. §1.2) are
localization decisions made specifically for that audience, not generic
defaults, and should be framed that way in any write-up.

---

## 2026-08-25: `ml/` correctness pass + live end-to-end pipeline validation

### Context

A prior read-only review of `ml/` (see git history around this date)
identified five issues to fix, all addressed and live-tested in this
pass. This section records what was found, why it matters, and — for the
live-testing portion — what a real run of the full pipeline actually
produced, which is the more paper-relevant part: PHIRE's core claim is
"claim-level verified, evidence-attributed answers," and this is the
first time that pipeline was exercised end-to-end against real local
models (not fakes/mocks) with adversarial-ish edge cases, not just the
happy path.

### 1. Correctness fixes, with the empirical evidence behind each

**1.1 Privacy-boundary gap in prose extraction.**
`ml/graph/prose_extraction.py` — the module that sends every patient
document's free-text content (progress notes, radiology reports; the
most PHI-sensitive text in the codebase) to a local LLM for structured
fact extraction — was not enforcing PHIRE's "must resolve to localhost"
network boundary (`ml/local_only.py`), unlike every sibling module that
talks to Ollama/Neo4j. A misconfigured `OLLAMA_HOST` environment variable
would have silently sent clinical note text to a non-local host. Fixed by
adding the same `require_localhost()` check other modules already had;
regression tests confirm both an arbitrary remote host and a
`localhost`-lookalike hostname (`localhost.attacker.example` — the exact
bypass class `require_localhost` itself was built to close) now raise
instead of silently proceeding.

*Relevant if writing about*: privacy-by-construction in a "local-only"
health AI system — this is a concrete example of how such an invariant
can quietly regress in one module even when correctly enforced elsewhere,
and why a single shared enforcement function (found via an earlier review
pass, not this one) matters more than per-file discipline.

**1.2 Document-dating bug, and a localization decision worth documenting explicitly.**
`find_document_date()` (`ml/graph/observations.py`) is the function that
assigns every extracted clinical fact (lab values, medications,
conditions) its effective date, which drives all of PHIRE's time-series/
trend reasoning. Two problems found and fixed:

- It only recognized strict ISO (`YYYY-MM-DD`) dates and took the
  **first** date-shaped substring in the document, in document order —
  with no way to distinguish "date of service" from "date of birth." A
  document listing DOB before its own service date (a realistic layout —
  demographics header, then visit details) got every Observation from
  that document silently misdated to the patient's *birth year* instead
  of the visit date. Confirmed live against the exact document layout
  already present in `ml/rag/ingest/experiments/eval_data/documents.py`'s
  `demographics_vitals` fixture before the fix landed. Fixed by excluding
  any date immediately labeled `DOB`/`Date of Birth` from consideration.

- **Localization decision**: numeric dates (`DD/MM/YYYY` vs. `MM/DD/YYYY`)
  are ambiguous without a locale convention. PHIRE's primary audience is
  Indian users and clinics, where day-first (`DD/MM/YYYY`) is the
  standard convention — the opposite of the US `MM/DD/YYYY` convention a
  default implementation would likely assume. `find_document_date` now
  parses day-first explicitly, with the rationale recorded inline in
  `ml/graph/observations.py` (`_DATE_FORMATS`'s comment) so it isn't lost
  as an unexplained-looking choice later. Extended to also parse
  dash-separated numeric dates and written-out month names (`"1 March
  2026"`, `"March 1, 2026"`), since OCR'd real-world clinical documents
  won't reliably use ISO format.

*Relevant if writing about*: locale-aware design as a first-class
decision (not an afterthought) in a system explicitly targeting a
non-US-default audience; also a good concrete example of a "silent
correctness bug" — one that produces a plausible-looking wrong answer
(a birth date is a valid date) rather than a crash, which is the more
dangerous failure mode in a clinical-adjacent system.

**1.3 Untested newest code (graph write/read paths).**
`ml/graph/conditions.py`, `medications.py`, and `patient_context.py` —
all added in the two commits immediately preceding this pass — had zero
dedicated unit tests; their only coverage was a live-Neo4j integration
test file with no availability guard, so it *errored* (not skipped) in
any environment without Neo4j running, which reads as unrelated
infrastructure noise rather than "this code has no safety net." Fixed by
(a) adding a `pytest.skip` guard keyed on `neo4j.exceptions.
ServiceUnavailable`, verified to actually skip (confirmed against a
deliberately-wrong port) and to still pass against the real local
instance, and (b) adding 24 new unit tests across three new test files
using an in-memory fake `GraphClient`, covering the pure build logic and
the Cypher/parameter-passing contract without requiring a live database.

**1.4 Unbounded claim-verification cost.**
`ClaimVerifier.verify()` (`ml/claims/verifier.py`) runs one BART-large-
MNLI forward pass per (claim, evidence-chunk) pair. The verification pool
`QAChain` builds per question included the patient's *entire* current
fact set and *entire* trend-fact set with no size limit — fine at
today's few-fact scale, but with no backstop against becoming
`O(claims × entire patient history)` once real longitudinal data
accumulates. Added a defensive cap (`MAX_FACT_EVIDENCE = 50`, applied
independently to patient facts and trend facts so one list can't crowd
out the other), verified via unit tests that construct a 75-fact list and
confirm exactly 50 chunks make it into the pool.

**1.5 Backend integration contract undocumented.**
`QAChain()`'s constructor loads 4 GPU models and opens a Neo4j
connection — expensive, and only safe to do once per process, not per
request. This was stated in `docs/ML_HANDOFF_FOR_ANIKA.md` already for
the model-loading cost, but predated the graph integration and didn't
mention the added Neo4j dependency, the per-`answer()`-call Neo4j read
pattern (3 reads unless `observations=` is passed explicitly), or the new
`MAX_FACT_EVIDENCE` cap. Updated in place (see that doc's 2026-08-25
addendum) rather than duplicated here.

### 2. Live end-to-end pipeline validation

All prior coverage of the "retrieve → rerank → generate → extract claims
→ verify → confidence-score → abstain" pipeline was either unit-level
with every subsystem faked, or covered individual stages in isolation.
This pass added the first test exercising the real, unmodified pipeline
against real local infrastructure: the actual ~620-document Chroma/BM25
reference corpus, real MedCPT embedding + reranking, real Ollama
generation (`medgemma:4b`), real BART-large-MNLI verification, and a real
Neo4j instance seeded with an isolated test patient (never the
production `"self"` patient — see `docs/GRAPH_SCHEMA_ROADMAP.md`/
`ml/graph/observations.py` on why there's exactly one).

**Result across 3 independent live runs (18 total test executions) after
the fix below**: 6/6 tests passing every time — direct patient-fact
recall, trend-claim `DERIVED` labeling, abstention on an out-of-domain
question ("deworming schedule for a pet iguana" — chosen specifically to
have no support in either the patient record or the medical reference
corpus), and confidence-score bounds across a free-form summary question.
`ml/tests/test_qa_chain_live_e2e.py`.

**A real bug this live run found, not anticipated by design or by
inspection**: the actual `data/chroma` reference store (not a test
fixture — the real corpus this repo's retrieval runs against) contained
21 chunks left over from earlier OCR-benchmark ingestion, tagged
`source: patient_document, authority: 1.0` — a synthetic "R. Thompson"
patient, same authority tier as genuine patient data. Two concrete
failure modes this caused, both observed directly (not inferred):

1. A naive test assertion ("does the seeded test patient's exact lab
   value appear in the final answer text") passed *even when the
   patient's own data played no role*, because a decoy document
   coincidentally shared the same numeric value — a methodological
   trap worth naming explicitly: **evaluating a RAG/verification
   pipeline by string-matching the final answer against an expected
   value is not sufficient evidence the value came from the intended
   source**, especially once multiple same-topic documents exist at
   equal authority. The fix used instead — checking that the verifying
   evidence chunk carries no `source_url`/`source_filename` (i.e. it's a
   structured graph fact, not any ingested document) — is a more
   rigorous evaluation pattern and is now the standard this test file
   uses throughout.
2. More seriously: `ClaimVerifier.verify()` selects, among all pool
   chunks, whichever has the single strongest entailment-or-contradiction
   signal for a claim — and when a same-topic decoy document with a
   *different* value for the same metric (patient: potassium 7.9 mEq/L
   "Critical High"; decoy: potassium 5.4 mEq/L "High") was in the pool,
   the verifier sometimes selected the decoy as "most informative" and
   labeled a **true, correctly-recorded patient claim as `CONFLICTING`**
   — observed directly across repeated live runs before the corpus was
   cleaned, not a hypothetical. This is a real failure mode of "pick the
   single strongest-signal chunk" evidence selection when the pool can
   contain multiple same-authority, same-topic-different-value documents
   — worth a deeper look (e.g. preferring `patient_record`/
   `patient_derived`-sourced evidence when present and topically
   relevant, rather than treating all authority-1.0 chunks as
   interchangeable) if PHIRE's evidence pool composition ever becomes
   more complex than "one patient's own data + public reference
   literature." Immediate fix applied: removed the 21 contaminating
   chunks from the live store (backed up first); the underlying
   verifier-selection behavior was left as-is, since fixing it is a
   design decision (how should same-authority conflicting evidence be
   arbitrated?) rather than an unambiguous bug fix, and is worth deciding
   deliberately rather than as a side effect of a testing pass.

*Relevant if writing about*: this is a genuinely reusable case study for
an evaluation-methodology section — it demonstrates concretely why
substring/exact-match evaluation of a generative pipeline's *output text*
is insufficient, and why evaluating *evidence provenance* (which source
was actually cited, structurally) is the more rigorous standard for a
system whose core contribution is claim-level attribution in the first
place.

### 3. Test suite state after this pass

157 → 198 tests passing (41 new: 8 privacy-boundary + date-parsing
regression tests, 24 new graph unit tests, 3 verification-pool cap tests,
6 live end-to-end pipeline tests). All passing against the real local
stack (Ollama with `medgemma:4b`/`qwen3.5:9b`, Neo4j 5-community, the
production Chroma corpus post-cleanup) at the time of writing, run
repeatedly (3+ consecutive full live passes) to rule out flakiness before
concluding.

---

## 2026-09-09: Unified visual document extraction with `datalab-to/lift` VLM & Option A chunk synthesis

### Context

Prior to this milestone, patient document ingestion was fragmented across three disparate tools:
1. `pypdf` for digital PDFs (failed completely on scanned documents without text layers).
2. `olmOCR-2-7B` via Ollama for images and scanned documents.
3. Regex-based HTML table parsing (`table_parsing.py`) and a secondary LLM prose extraction pass (`qwen3.5:9b` via Ollama in `prose_extraction.py`).

This multi-stage pipeline introduced severe VRAM contention on 8GB GPUs (competing with MedCPT embeddings and BART-large-MNLI claim verification) and had inconsistent document type coverage.

### Key Decisions & Findings

1. **Unified Schema-Guided Visual Document Extraction (`datalab-to/lift`):**
   - Adopted `datalab-to/lift` (~9.7B parameters), loaded in-process via Hugging Face Transformers.
   - Designed a single unified extraction schema (`CLINICAL_DOCUMENT_SCHEMA` in `ml/rag/ingest/lift_schema.py`) extracting `observations` (with values, units, reference ranges, and interpretations), `medications` (with dosages, frequencies, and statuses), `conditions` (with clinical statuses), and narrative sections.
   - **Schema Design Constraint**: Strictly avoided JSON Schema `enum`, `anyOf`, `oneOf`, `$ref`, and `additionalProperties` keywords. Rich natural language `description` fields guide the VLM during constrained decoding, and validation/normalization occurs deterministically in Python via `validate_lift_payload()`.

2. **Option A RAG Chunk Synthesis for NLI Entailment:**
   - Rather than indexing raw disjoint table cells or brittle string snippets, `synthesize_patient_chunks` (`ml/rag/ingest/chunk_synthesizer.py`) converts structured extraction entities into fluent, declarative clinical sentences:
     - Observations: `"On {doc_date}, {name} was {val}{unit}{ref}{interp}. Source: {filename}."`
     - Medications: `"{name} ({dosage}, {freq}) - Status: {status}. Documented in {filename} on {doc_date}."`
     - Conditions: `"Condition: {name} (Status: {status}). Documented in {filename} on {doc_date}."`
   - These declarative sentences significantly improve NLI entailment scoring (`facebook/bart-large-mnli`) by eliminating syntactic ambiguity.

3. **In-Process Quantization & CPU / Non-CUDA Safety:**
   - On CUDA GPUs: loaded with 4-bit NormalFloat4 (`BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16, bnb_4bit_quant_type="nf4")`), fitting in ~5.5GB VRAM.
   - On CPU (non-CUDA laptops): `BitsAndBytesConfig` is strictly omitted to prevent `ValueError`, loading in standard `torch.float32` on `device="cpu"`.
   - Fast deterministic offline testing is supported via `PHIRE_MOCK_LIFT=true` or `LiftExtractor(mock=True)`.

4. **Component Retirement:**
   - Retired `ml/rag/ingest/ocr.py`, `ml/rag/ingest/table_parsing.py`, and `ml/graph/prose_extraction.py`.
   - Cleaned up backend singletons (`get_lift_extractor()`) and wrapped processing in `GPU_LOCK`.
   - Test suite expanded to 217 total tests (200 unit tests passing offline with 0 failures).
