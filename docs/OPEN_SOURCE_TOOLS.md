# PHIRE: Open-Source Tools & Integration Guide

**Status**: Historical record of every tool evaluated for PHIRE — adopted
and rejected alike — kept intact rather than pruned, so the reasoning
behind each choice survives for methods/related-work writing later.
**Date**: August 2026, corrected 2026-08-26
**Research Basis**: 2024-2026 active projects and papers
**Note**: Dataset/model choices in this doc are finalized in
[docs/DATASETS_AND_GRAPH_RAG.md](DATASETS_AND_GRAPH_RAG.md), which also
corrects one factual error (item 29, "HumanAI 3.6M") found during dataset
validation. That doc is authoritative where the two disagree.

**2026-08-26 correction pass**: several `ml/`-relevant entries below
described early tool choices that were later superseded by what was
actually built and benchmarked — this pass corrected them in place
(marked **Not adopted** where applicable) rather than deleting them, and
added the concrete benchmark/reason behind each swap. See
`ml/*/experiments/RESULTS.md` for full methodology on every ml/-side
choice. Backend/frontend/CV-extension entries this pass couldn't verify
against shipped code are left as originally written.

---

## Overview

PHIRE integrates 30+ open-source tools across RAG, computer vision, medical LLMs, and evaluation. This document lists each tool with GitHub links, licensing, maturity, and PHIRE integration strategy — **Adopted**/**Not adopted**/**Superseded** status added 2026-08-26 for entries with a confirmed current build status.

---

## TIER 1: CORE TOOLS (implemented in ml/)

### A. Local LLM Serving

**1. Ollama**
- **GitHub**: [ollama/ollama](https://github.com/ollama/ollama)
- **License**: MIT
- **Functionality**: Local LLM server (no API calls)
- **Maturity**: Production-ready (2024 stable)
- **PHIRE Role**: Primary LLM serving infrastructure
- **Integration**: localhost:11434, no changes needed
- **Hardware**: 8GB RAM minimum, GPU optional
- **Why PHIRE**: Privacy-first, Docker-containerizable, 1-2 sec startup

**2. MedGemma 4B** — *Adopted, corrected 2026-08-26*
- **Source**: Google DeepMind (open-weight via Ollama)
- **License**: Gemma License (commercial use allowed with attribution)
- **Functionality**: Medical foundation model
- **Correction**: "MedGemma 1.5 8B" never existed — Google ships MedGemma
  only as 4B and 27B. PHIRE runs **`medgemma:4b`** for chat generation
  (`ml/llm/ollama_client.py`). Not independently re-benchmarked against
  Meditron-7B or other alternatives — adopted as the project's original
  base-model pick and kept.
- **Integration**: `ollama pull medgemma:4b` (~2.5GB quantized)
- **PHIRE Role**: Primary clinical LLM for chat generation and claim extraction (`ml/claims/extractor.py`)
- **Also in use**: `qwen3.5:9b` for prose fact extraction (medications/conditions/observations from free text) — chosen over `medgemma:4b` after a head-to-head benchmark, see item 8a below

**3. Llama 2 / Llama 3.1**
- **GitHub**: [meta-llama/llama](https://github.com/meta-llama/llama)
- **License**: Meta's Llama License (free for research/commercial)
- **Functionality**: Foundation model (fallback if MedGemma issues)
- **Maturity**: Production-ready
- **PHIRE Role**: Fallback LLM
- **Why PHIRE**: Well-tested, reliable, easy fine-tuning

---

### B. Vector Database & Embeddings

**4. Chroma**
- **GitHub**: [chroma-core/chroma](https://github.com/chroma-core/chroma)
- **License**: Apache 2.0
- **Functionality**: In-process vector DB (no Docker needed)
- **Maturity**: Production-ready (2024 stable)
- **PHIRE Role**: Clinical documents + evidence embeddings
- **Integration**: Native Python, ~500MB persistent DB
- **Why PHIRE**: Simple, fast, privacy-preserving (all local)
- **Migration Path**: Qdrant (Month 6+) for scale

**5. MedCPT (dual encoder)** — *Adopted, corrected 2026-08-26*
- **Source**: NCBI (`ncbi/MedCPT-Query-Encoder` + `ncbi/MedCPT-Article-Encoder`, via `transformers`/`torch` directly, not Sentence-Transformers)
- **License**: Apache 2.0 (models on Hugging Face)
- **Functionality**: True dual encoder — separate query/article models — for dense embeddings, retrieval-specific
- **Correction**: none of the originally-listed candidates (`allenai-specter`, `pubmedbert`, `msmarco-distilbert-base-v4`) are what's actually running. A 7-candidate, 215-passage/129-query benchmark (`ml/rag/experiments/RESULTS.md`) compared 3 medical-specialized and 4 general-purpose embedding models; **MedCPT won on Recall@5 (0.7721) and Recall@10 (0.9194)**, tied-best on Recall@3, beating both general-purpose SOTA models (BGE, e5, mxbai) and the other medical candidates (PubMedBERT, BioLORD).
- **PHIRE Role**: Document + query encoding (`ml/rag/embeddings.py`)
- **Why PHIRE**: Best empirical retrieval accuracy on PHIRE's own clinical eval set, not assumed from general medical-domain reputation

**5a. MedCPT-Cross-Encoder (reranker)** — *Adopted, missing from earlier tool lists*
- **Source**: NCBI (`ncbi/MedCPT-Cross-Encoder`)
- **License**: Apache 2.0
- **Functionality**: Relevance reranking on top of fused BM25+Chroma candidates, combined with authority/recency scoring
- **PHIRE Role**: `ml/rag/reranker.py` — chosen for consistency with the MedCPT embedding decision (third model in the same family) rather than introducing an unrelated cross-encoder
- **Known limitation, addressed**: saturates relevance near 1.0 for any topically-relevant chunk, which could bury a patient's own record behind generic reference prose — a weight-tuning sweep confirmed re-weighting doesn't fix this (no reasonable authority weight outvotes that many simultaneous ties); fixed structurally instead with a "patient-document floor" that promotes a close-scoring patient chunk into the result set regardless of weighted rank. See `ml/rag/reranker_experiments/RESULTS.md` for the full investigation.

**6. BM25 / Rank-BM25**
- **GitHub**: [dorianbrown/rank_bm25](https://github.com/dorianbrown/rank_bm25)
- **License**: Apache 2.0
- **Functionality**: Lexical (exact term) matching
- **PHIRE Role**: Lab value queries ("LDL", "glucose")
- **Why PHIRE**: Critical for structured lab data where semantic fuzzing fails

---

### C. RAG & Evidence Attribution

**7. LangChain** — *Evaluated, NOT adopted (corrected 2026-08-26)*
- **GitHub**: [langchain-ai/langchain](https://github.com/langchain-ai/langchain)
- **License**: MIT
- **Functionality**: Orchestration (RAG chains, memory, tools)
- **Rejected because**: the actual QA pipeline (`ml/chains/qa_chain.py`) —
  retrieve → rerank → generate → extract claims → verify → confidence-score
  → abstain — turned out simple enough as a linear sequence of typed
  function calls that LangChain's abstraction layer added indirection
  without buying capability PHIRE needed. `langchain==1.3.15` sat unused
  in `ml/requirements.txt` for a while as a leftover from this original
  plan; removed 2026-08-26 once confirmed nothing imports it.
- **If reconsidered**: revisit specifically if/when multi-step agentic
  tool-calling (not just a linear chain) becomes a real requirement —
  that's the capability gap a hand-written chain doesn't cover.

**8. MedRAGChecker** — *Evaluated, NOT adopted (corrected 2026-08-26)*
- **GitHub**: [chufangao/MedRAGChecker](https://github.com/chufangao/MedRAGChecker) [2025 paper]
- **License**: Apache 2.0 (paper claims this; see below)
- **Functionality**: Claim-level verification for biomedical RAG
- **Paper**: "MedRAGChecker: Claim-Level Verification for Biomedical Retrieval-Augmented Generation" (2025)
- **Rejected because**: **not a pip-installable library** — confirmed
  directly (`ml/claims/experiments/candidates.py`'s own docstring records
  this finding), despite being the paper originally cited for PHIRE's
  evidence-attribution approach. There is no package to integrate.
- **What was built instead**: PHIRE's own NLI-based verifier
  (`ml/claims/verifier.py`) does the same conceptual job — entailment/
  contradiction scoring of a claim against evidence — using a real,
  benchmarked model. A 129-pair, 6-candidate benchmark (medical
  MedNLI-finetuned vs. general-purpose MNLI models) found
  **`facebook/bart-large-mnli` winning on all four metrics** (accuracy
  0.969, entailment F1 0.977, neutral F1 0.966, contradiction F1 0.964),
  beating both medical-specialized candidates — a general model winning a
  medical task was surprising enough to be spot-checked, not just
  accepted: the medical models were found to over-predict
  entailment/contradiction on genuinely neutral pairs, a systematic
  miscalibration BART-large-MNLI didn't share. Full methodology:
  `ml/claims/experiments/RESULTS.md`.
- **Status taxonomy actually implemented**: SUPPORTED / CONFLICTING /
  UNCERTAIN / UNSUPPORTED (`ml/claims/verifier.py`), plus DERIVED as a
  relabel applied one layer up (`ml/chains/qa_chain.py`) for a claim that
  matches a precomputed trend fact rather than a raw evidence sentence —
  not MedRAGChecker's own SUPPORTED/REFUTED/UNDETERMINED scheme.
  INFERRED (multi-hop reasoning claims) is explicitly not implemented —
  no validated signal exists for it yet.

**8a. Prose fact extraction: hand-rolled vs. Google LangExtract** — *benchmark, hand-rolled adopted*
- **LangExtract**: [google/langextract](https://github.com/google/langextract),
  Apache 2.0, verified real (38k+ stars, actively maintained). Source-grounds
  every extraction to its exact character span — genuinely valuable, but its
  Ollama integration was verified (by reading its provider source) to only
  support loose JSON mode, not real schema constraints.
- **Hand-rolled**: direct Ollama call with full JSON Schema constraint
  (grammar-constrained decoding) — the same pattern already used for OCR.
- **Result**: a 6-candidate benchmark (2 methods × 3 models, 3 real
  OCR'd documents, fact-level metrics) found hand-rolled beating
  LangExtract specifically on medication-status accuracy (1.0 vs.
  0.667-0.833) — consistently across all three paired models, pointing at
  the method (loose JSON vs. real schema constraints) rather than any one
  model. **`qwen3.5:9b` matched `qwen3.5:27b` exactly while running ~13x
  faster** (24.8s vs. 322.8s) on a third of the VRAM footprint — adopted
  as the production model. Full results: `ml/graph/experiments/RESULTS.md`.
- **PHIRE Role**: `ml/graph/prose_extraction.py` — extracts medications/
  conditions/observations from free-text document sections into the
  Longitudinal Health Graph.

**9. Medical Graph RAG**
- **Paper**: [ACL 2025](https://aclanthology.org/2025.acl-long.1381.pdf)
- **Functionality**: Graph-based RAG with entity linking
- **PHIRE Role**: Conceptual basis for PHIRE's third retrieval leg — see
  items 9a/9b and [docs/DATASETS_AND_GRAPH_RAG.md](DATASETS_AND_GRAPH_RAG.md)
  §3 / [docs/GRAPH_SCHEMA_ROADMAP.md](GRAPH_SCHEMA_ROADMAP.md) §3f for the
  current build status.
- **Approach**: Triple-graph construction (subject-predicate-object)
- **Why PHIRE**: Vector/lexical retrieval is similarity-based and cannot
  answer multi-hop or relational questions ("how did my LDL change
  relative to my statin dose changes"); a graph makes those chains
  traversable instead of hoping embedding similarity surfaces them.

**9a. LightRAG** — *Evaluated as the graph-RAG library, NOT adopted; the capability itself is still needed (corrected 2026-08-26)*
- **GitHub**: [HKUDS/LightRAG](https://github.com/HKUDS/LightRAG) · **Paper**: EMNLP 2025
- **License**: MIT
- **Functionality**: Graph-based RAG with local entity/relationship
  extraction and retrieval
- **Status**: evaluated as the candidate implementation for PHIRE's
  multi-hop graph-RAG leg — natively supports Ollama for entity/
  relationship extraction (PHI never leaves the local boundary during
  graph construction), the deciding factor over Microsoft's GraphRAG in
  the original comparison. **Not adopted as a dependency**; PHIRE's graph
  layer (`ml/graph/`) queries Neo4j directly via hand-written Cypher
  instead — deterministic table extraction plus schema-constrained LLM
  extraction from free text, both of which don't need a general-purpose
  graph-RAG library.
- **Important distinction, corrected 2026-08-26**: "LightRAG not adopted"
  is a decision about *which library*, not about *whether multi-hop
  graph-RAG retrieval gets built*. It doesn't exist yet in any form —
  `ml/graph/` today is single-patient fact *lookup* (current value per
  metric, latest-vs-previous trend delta via
  `ml/graph/patient_context.py`), not traversal of relationships
  *between* entities at query time. This is **outstanding, committed
  work**, not a dismissed option — see
  [docs/GRAPH_SCHEMA_ROADMAP.md](GRAPH_SCHEMA_ROADMAP.md) §3f for the
  detailed status. Revisit LightRAG itself (or an alternative) when that
  work actually starts; `lightrag-hku` is commented out, not deleted, in
  `ml/requirements.txt` with this exact framing.

**9b. Neo4j (graph store)** — *Adopted*
- **GitHub**: [neo4j/neo4j](https://github.com/neo4j/neo4j)
- **License**: GPLv3 (Community Edition, self-hosted)
- **Functionality**: Graph database
- **PHIRE Role**: Storage for the Longitudinal Health Graph — Patient/
  Observation/Medication/Condition/Document nodes, queried via
  hand-written Cypher (`ml/graph/client.py`), not via LightRAG or any
  graph-RAG framework. Enforces the same "must resolve to localhost"
  boundary as Ollama (`ml/local_only.py`).
- **Why PHIRE**: Self-hosted keeps it inside the local privacy boundary;
  chosen ahead of the original Month 2-3 timeline once patient documents
  needed structured fact storage regardless of when the broader graph-RAG
  leg (9a) lands.

**10. MEGA-RAG**
- **Paper**: Frontiers in Public Health 2025
- **Functionality**: Multi-evidence guided answer refinement
- **PHIRE Role**: Optional enhancement for hallucination reduction
- **Approach**: Multiple evidence sources ranked by authority
- **Why PHIRE**: Directly addresses "only answer when evidence supports"

**11. VISA (Visual Source Attribution)**
- **Paper**: [VISA arXiv 2024](https://arxiv.org/pdf/2412.14457)
- **Functionality**: Bounding boxes around source evidence in documents
- **PHIRE Role**: Future enhancement (Month 4+)
- **Why PHIRE**: Visual highlight of exact evidence location (better UX)

---

### D. Document Processing

**12. Docling** — *Evaluated, NOT adopted (corrected 2026-08-26)*
- **GitHub**: [DS4SD/docling](https://github.com/DS4SD/docling)
- **License**: MIT
- **Functionality**: PDF → structured text + tables + figures
- **Rejected because**: not needed — `pypdf` handles text-based PDFs
  directly (`ml/rag/ingest/patient_documents.py`'s `PDFTextExtractor`),
  and table structure comes from olmOCR-v2 emitting HTML tables in its
  transcription (parsed by `ml/rag/ingest/table_parsing.py`), not from a
  dedicated layout-extraction library. No benchmark was run against
  Docling specifically — the pypdf+olmOCR combination simply covered both
  needs (text extraction, table structure) without adding a third
  dependency.
- **PHIRE Role (actual)**: text-based PDF lab report extraction — pypdf

**13. PyMuPDF (fitz)** — *Not adopted*
- **License**: AGPL (proprietary option available)
- **Functionality**: PDF extraction fallback
- **Status**: not needed — pypdf covers the text-based-PDF case; a
  scanned PDF with no text layer is a known, documented gap (see
  `docs/PDF_INGESTION_ROADMAP.md`), not something PyMuPDF would solve
  differently.
- **Why PHIRE**: Fast, lightweight — kept here as a fallback option if pypdf's extraction quality is ever found lacking on a real document

**14. Tesseract OCR** — *superseded, see below*
- **GitHub**: [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
- **License**: Apache 2.0
- **Functionality**: Text extraction from image-based PDFs
- **PHIRE Role**: Originally proposed for scanned medical documents;
  **superseded by olmOCR-v2** (below) — a benchmark
  (`ml/rag/ingest/experiments/RESULTS.md`) found it substantially more
  accurate on structured clinical documents (tables, mixed layouts) than
  classic character-recognition OCR, while remaining fully local via
  Ollama. Kept here for reference, not the active choice.
- **Integration**: Docker container or system package
- **Why PHIRE**: Common for older medical reports; character-recognition-only, no layout/table understanding

**14a. olmOCR-v2 (Allen AI)** — *Adopted*
- **HuggingFace**: [allenai/olmOCR-2-7B-1025](https://huggingface.co/allenai/olmOCR-2-7B-1025)
- **License**: Apache 2.0
- **Functionality**: Vision-language model fine-tuned for document-to-text
  conversion — understands page layout, tables (converts to HTML), and
  mixed prose/list content, not just character recognition
- **PHIRE Role**: OCR extractor for `ml/rag/ingest/patient_documents.py`
  (scanned/photographed patient documents PDFTextExtractor can't handle)
- **Deployment**: Runs locally via Ollama (Q4_K_M quantization,
  `bartowski`'s GGUF build, ~6GB), consistent with PHIRE's existing
  Ollama-based local-LLM pattern
- **Why PHIRE**: Benchmarked against olmOCR-v1 and Q8_0 quantization
  across 4 candidates, 12 test images (grid tables, two-column layout,
  narrative prose, clean + simulated phone-photo variants) —
  content-normalized CER 0.012 (vs v1's 0.11-0.14) and perfect field-level
  accuracy on all clinically critical values. See
  `ml/rag/ingest/experiments/RESULTS.md` for full methodology and results.

---

### E. Medical Knowledge Bases

**15. UMLS (Unified Medical Language System)**
- **Source**: NLM (free registration)
- **License**: Open access with terms
- **Functionality**: Biomedical vocabulary (2.2M concepts, 12M relationships)
- **PHIRE Role**: Concept normalization + linking
- **Alternative**: Wikidata medical subset
- **Why PHIRE**: Gold standard for medical entity linking

**16. PubMed Central Dataset**
- **Source**: NIH (open access)
- **License**: CC0 / CC-BY (most articles)
- **Functionality**: 3.7M+ full-text biomedical articles
- **PHIRE Role**: Evidence corpus for RAG
- **Integration**: Download via API or bulk data
- **Size**: ~1TB for full dataset
- **Why PHIRE**: Authoritative medical evidence source

---

### F. Claim Extraction & Verification

**17. Spacy + Transformer NER**
- **GitHub**: [explosion/spacy](https://github.com/explosion/spacy)
- **License**: MIT
- **Functionality**: Named entity recognition (medical entities)
- **PHIRE Role**: Extract medical concepts (conditions, meds, labs)
- **Models**: `en_core_sci_md` (biomedical NER)
- **Why PHIRE**: Fast, accurate, low latency

**18. SciBERT / PubMedBERT**
- **Source**: AllenAI / Microsoft
- **License**: MIT / Apache 2.0
- **Functionality**: Biomedical-specialized transformers
- **PHIRE Role**: Claim classification ("this is a recommendation vs. a fact")
- **Why PHIRE**: Better than general BERT on medical text

---

## TIER 2: COMPUTER VISION TOOLS (not yet started)

### A. Food Recognition & Calorie Estimation

**19. YOLOv8**
- **GitHub**: [ultralytics/yolov8](https://github.com/ultralytics/yolov8)
- **License**: AGPL (enterprise license available)
- **Functionality**: Real-time food detection in images
- **Maturity**: Production-ready (2024)
- **PHIRE Role**: Food item localization
- **Datasets**: Fine-tune on Food-101, UECFood100
- **Why PHIRE**: 50x faster than Faster R-CNN, mobile-compatible

**20. EfficientNet-B0**
- **Source**: Google TensorFlow / Hugging Face
- **License**: Apache 2.0
- **Functionality**: Food classification (101 categories)
- **Maturity**: Production-ready
- **PHIRE Role**: Food type classification
- **Dataset**: Pre-trained on Food-101
- **Why PHIRE**: Lightweight (5.3M params), ~90% accuracy on Food-101

**21. Food-101 Dataset**
- **Source**: ETH Zurich; images sourced via Foodspotting (own terms, not CC-licensed by ETH)
- **License**: Research/fair-use; not freely redistributable
- **Size**: 101 food categories, 101K images
- **PHIRE Role**: **Pretraining/classification backbone only** ("what dish is
  this") — finalized as secondary to Nutrition5k (item 23). Category
  labels carry no macro/portion data, so this dataset alone cannot answer
  a nutrition question; it must feed a join to Nutrition5k or USDA
  FoodData Central (item 24) to produce one.
- **Link**: [food-101.ethz.ch](http://food-101.ethz.ch/)
- **Why PHIRE**: Standard benchmark, large N, good classification backbone

**22. Recipe1M+ Dataset**
- **Source**: MIT CSAIL (request-gated access)
- **License**: Non-commercial research/education only
- **Size**: 1M+ recipes + 13M+ images + partial nutritional labels
- **PHIRE Role**: Recipe-to-nutrition linking, meal plan generation
- **Features**: Ingredients + instructions + macros — **but nutrition
  fields exist only for the subset of recipes where unit and quantity
  were both successfully parsed.** Filter explicitly on non-null
  nutrition before treating a recipe as a macro source; the rest have no
  nutrition row, not a zero.
- **Why PHIRE**: First recipe dataset with nutrition at scale, once filtered

**23. Nutrition5k Dataset (finalized: primary CV nutrition dataset)**
- **Source**: Google Research (`google-research-datasets/Nutrition5k`)
- **License**: CC BY 4.0 — commercial use permitted, attribution required
- **Size**: ~5K dishes, 4 rotating videos + top-down RGB-D per dish, weighed
  (not estimated) ground truth
- **Schema**: `dish_id, total_calories, total_mass, total_fat, total_carb,
  total_protein, num_ingrs`, repeated per-ingredient
  (`ingr_N_grams, ingr_N_calories, ...`)
- **PHIRE Role**: Primary training set for calorie/macro estimation —
  promoted ahead of Food-101/Recipe1M+ after dataset validation because it
  is the only CV nutrition dataset with unrestricted licensing, clean
  columns, and directly-usable ground truth requiring no external join
- **Why PHIRE**: Best accuracy for vision-based calorie estimation, and the
  only one of the three CV nutrition datasets safe for eventual commercial
  use without renegotiation

**24. USDA FoodData Central**
- **Source**: USDA (open access)
- **License**: Public domain
- **Functionality**: 350K foods + complete nutrition profiles
- **API**: RESTful API available
- **PHIRE Role**: Nutrition reference database
- **Why PHIRE**: Authoritative, comprehensive, free

**25. Hugging Face Food Recognition Model**
- **Model**: `BinhQuocNguyen/food-recognition-model`
- **Source**: Hugging Face Hub (MIT license)
- **Functionality**: End-to-end food → nutrition pipeline
- **Maturity**: Production-ready (2024)
- **PHIRE Role**: Baseline for comparison
- **Why PHIRE**: Pre-trained, easy integration

---

### B. Exercise Posture & Form Analysis

**26. MediaPipe Pose (finalized: run directly, no dataset/training needed)**
- **GitHub**: [google/mediapipe](https://github.com/google/mediapipe)
- **License**: Apache 2.0
- **Functionality**: Real-time pose estimation (33 landmarks)
- **Maturity**: Production-ready (2024)
- **PHIRE Role**: Exercise form detection — **this replaces "train a custom
  pose model" entirely for MVP.** Compute joint angles (squat depth,
  elbow flexion) directly from its 33-point output; only reach for a
  labeled exercise dataset (item 29) to classify which exercise/rep phase
  is happening, not to re-derive pose itself.
- **Capabilities**:
  - 33-point skeletal model, x/y/z + visibility per point
  - <100ms latency on CPU
  - Webcam/video input
  - Mobile-native support
- **Why PHIRE**: Fastest (runs on Raspberry Pi), privacy-first — no video
  needs to leave the device

**27. OpenPose**
- **GitHub**: [CMU-Perceptual-Computing-Lab/openpose](https://github.com/CMU-Perceptual-Computing-Lab/openpose)
- **License**: BSD
- **Functionality**: Multi-person pose estimation (25 points)
- **Maturity**: Production-ready
- **PHIRE Role**: Alternative to MediaPipe (higher accuracy if needed)
- **Tradeoff**: Slower (~200ms) but more accurate
- **Why PHIRE**: Backup option for group fitness scenarios

**28. YOLOv5 / YOLOv8 Pose**
- **GitHub**: [ultralytics/yolov8](https://github.com/ultralytics/yolov8)
- **License**: AGPL (enterprise available)
- **Functionality**: Pose estimation + detection combined
- **PHIRE Role**: Joint detection + exercise classification
- **Why PHIRE**: Latest variant (2024), good balance of speed/accuracy

**29. Exercise Form Benchmarks (corrected after dataset validation)**
- **Datasets**:
  - ~~**HumanAI 3.6M**: 3.6M 3D pose sequences (various exercises)~~ —
    **removed.** This previously referenced Human3.6M, which does not
    match this description: its 17 activities are indoor daily-life poses
    (talking on the phone, smoking, discussing) with no squat, push-up,
    lunge, or deadlift class. It is also academic-account-gated and
    explicitly non-redistributable. See
    [docs/DATASETS_AND_GRAPH_RAG.md](DATASETS_AND_GRAPH_RAG.md) §2.5.
  - **Kaggle exercise-pose datasets** (e.g. "Squat Exercise Pose
    Dataset"): small, crowd-sourced, joint-angle-labeled sets — usable for
    an MVP form-scoring fine-tune on top of MediaPipe's joint angles.
    Check each dataset's license individually; do not use as the sole
    basis for a clinical-flavored claim like "injury prevention" without
    independent validation.
  - **Custom labeled dataset**: Build from PHIRE user videos (month 3+)
- **PHIRE Role**: Evaluate rep counting, form correctness

**30. Real-Time Feedback Framework**
- **GitHub**: [Pose-Comparison repo](https://github.com/TodayAnalyze/Pose-Comparison)
- **License**: MIT
- **Functionality**: Real-time form correction for push-ups, squats, bicep curls
- **PHIRE Role**: MVP baseline for form feedback
- **Why PHIRE**: Already battle-tested, open-source

---

## TIER 3: ML TRAINING & EVALUATION TOOLS (partially available, recommendations not started)

### A. Model Training

**31. PyTorch**
- **GitHub**: [pytorch/pytorch](https://github.com/pytorch/pytorch)
- **License**: BSD
- **Functionality**: Deep learning framework
- **PHIRE Role**: Training nutrition + HAR models
- **Why PHIRE**: Industry standard, dynamic graphs, GPU-friendly

**32. TensorFlow / Keras**
- **GitHub**: [tensorflow/tensorflow](https://github.com/tensorflow/tensorflow)
- **License**: Apache 2.0
- **Functionality**: Alternative ML framework
- **PHIRE Role**: Option for computer vision tasks
- **Why PHIRE**: Hugging Face models native support

**33. Hugging Face Transformers**
- **GitHub**: [huggingface/transformers](https://github.com/huggingface/transformers)
- **License**: Apache 2.0
- **Functionality**: Pre-trained models library
- **PHIRE Role**: Loading medical NLP models
- **Why PHIRE**: Centralized model hub, easy fine-tuning

**34. LoRA (Low-Rank Adaptation)**
- **GitHub**: [microsoft/LoRA](https://github.com/microsoft/LoRA)
- **License**: MIT
- **Functionality**: Efficient fine-tuning (low VRAM)
- **PHIRE Role**: Fine-tuning Ollama models
- **Benefit**: 50-70% VRAM reduction vs. full fine-tuning
- **Why PHIRE**: GPU-memory constrained environments

---

### B. Evaluation & Benchmarking

**35. ArchEHR-QA 2026**
- **Source**: RVCE / Academic (open access)
- **Functionality**: 167 expert-validated EHR Q&A cases
- **PHIRE Role**: MVP evaluation benchmark
- **Metrics**: Evidence accuracy, claim extraction precision
- **Why PHIRE**: Healthcare-specific, curated by clinicians

**36. MedHallBench 2025**
- **Paper**: "MedHallu: A Comprehensive Benchmark for Detecting Medical Hallucinations"
- **Functionality**: 1K+ medical hallucination examples
- **PHIRE Role**: Hallucination detection evaluation
- **Metrics**: False claim detection rate
- **Why PHIRE**: First comprehensive medical hallucination dataset

**37. scikit-learn**
- **GitHub**: [scikit-learn/scikit-learn](https://github.com/scikit-learn/scikit-learn)
- **License**: BSD
- **Functionality**: ML metrics + classical algorithms
- **PHIRE Role**: Precision/recall/F1 computation
- **Why PHIRE**: Standard evaluation toolkit

**38. Weights & Biases**
- **GitHub**: [wandb/wandb](https://github.com/wandb/wandb)
- **License**: MIT (with commercial cloud)
- **Functionality**: ML experiment tracking
- **PHIRE Role**: Track ablations, hyperparameters
- **Why PHIRE**: Free for open-source, excellent dashboards

---

## TIER 4: WEARABLE & DEPLOYMENT TOOLS (not yet started)

### A. Wearable Integration

**39. Open Wearables**
- **GitHub**: [the-momentum/open-wearables](https://github.com/the-momentum/open-wearables)
- **License**: MIT
- **Functionality**: Unified wearable data API (self-hosted)
- **Maturity**: Production-ready (Dec 2024 launch)
- **PHIRE Role**: Wearable data ingestion (Month 3+)
- **Supported Devices**: Whoop, Garmin, Oura, Apple Health, Strava, Polar, Samsung, Google Health
- **Why PHIRE**: Self-hosted, open-source, no vendor lock-in

**40. Fitbit Web API (Fallback)**
- **Source**: Fitbit / Google Fit
- **License**: Proprietary (free tier available)
- **Functionality**: Heart rate, activity, sleep data
- **PHIRE Role**: Fallback if Open Wearables unavailable
- **Why PHIRE**: Widely used, good documentation

---

### B. Containerization & Deployment

**41. Docker**
- **GitHub**: [moby/moby](https://github.com/moby/moby)
- **License**: Apache 2.0
- **Functionality**: Container orchestration
- **PHIRE Role**: All services (backend, frontend, Ollama, Chroma)
- **Why PHIRE**: Industry standard, isolation, reproducibility

**42. Docker Compose**
- **License**: Apache 2.0
- **Functionality**: Multi-container orchestration
- **PHIRE Role**: Local dev + deployment (all services one-command)
- **File**: `docker-compose.yml`
- **Why PHIRE**: Perfect for MVP (no Kubernetes complexity)

**43. PostgreSQL + pgvector** — evaluated, **not adopted**
- **GitHub**: [pgvector/pgvector](https://github.com/pgvector/pgvector)
- **License**: PostgreSQL (BSD-like)
- **Functionality**: Vector search in PostgreSQL
- **Actual choice**: Chroma is PHIRE's vector store (in-process, `ml/rag/retriever.py`), confirmed authoritative by `CLAUDE.md`. PostgreSQL is relational-only (patients, timeline, claims, evidence) — no pgvector extension in use.
- **Why not pgvector**: Chroma was the earlier decision and is what ingestion/retrieval actually integrate against; consolidating onto pgvector later would mean migrating a working retrieval path for a scale problem PHIRE doesn't have yet.

---

## Integration Strategy by Phase

### Core (`ml/` — implemented)
✅ Adopted:
- Ollama (medgemma:4b chat/extraction, qwen3.5:9b prose extraction, olmOCR-v2 OCR)
- Chroma, MedCPT (embeddings + cross-encoder reranking), rank_bm25
- BART-large-MNLI (claim verification), Neo4j (direct Cypher, not LightRAG)
- pypdf (text PDF extraction)
- PyTorch, scikit-learn (available; not yet used for recommendations)

❌ Not adopted (evaluated, see entries above for why): LangChain, MedRAGChecker, Docling

### Not yet built (backend/frontend scope)
- FastAPI, PostgreSQL, Docker Compose, Next.js — see `docs/ML_HANDOFF_FOR_ANIKA.md`

### Phase 2
➕ Add:
- Multi-hop graph-RAG retrieval (LightRAG or an alternative — see item 9a; **outstanding, not optional**, see `docs/GRAPH_SCHEMA_ROADMAP.md` §3f)
- MEGA-RAG
- YOLOv8/EfficientNet-B0 (Food-101 classification backbone), MediaPipe Pose
- Open Wearables (prep)

### Phase 3
➕ Add:
- Nutrition5k (primary CV nutrition training set), Food-101 (backbone),
  Recipe1M+ (nutrition-filtered subset), USDA FoodData Central integration
- PAMAP2 → WISDM HAR pretrain/fine-tune pipeline
- CGMacros personalization layer; AI4FoodDB only after schema verification
- Exercise form models (MediaPipe joint angles + Kaggle exercise-pose fine-tune)
- LoRA fine-tuning pipeline
- Weights & Biases tracking

### Phase 4
➕ Add:
- FHIR representation
- Advanced evaluation (ablations, statistical tests)
- Paper-ready benchmarks

---

## Licensing & Compliance

| Tool | License | Commercial? | HIPAA-Ready? | Adopted? |
|------|---------|-----------|---|---|
| Ollama | MIT | ✅ | Yes (local) | ✅ |
| MedGemma (4B) | Gemma | ✅ | Yes (local) | ✅ |
| Chroma | Apache 2.0 | ✅ | Yes (local) | ✅ |
| MedCPT | Apache 2.0 | ✅ | Yes (local) | ✅ |
| BART-large-MNLI | Apache 2.0/MIT (facebook/bart-large-mnli on Hugging Face) | ✅ | Yes (local) | ✅ |
| Neo4j (Community) | GPLv3 | ✅ (self-hosted) | Yes (local) | ✅ |
| pypdf | BSD | ✅ | Yes | ✅ |
| olmOCR-v2 | Apache 2.0 | ✅ | Yes (local via Ollama) | ✅ |
| Docling | MIT | ✅ | Yes | ❌ not adopted |
| LangChain | MIT | ✅ | Partial (requires Ollama) | ❌ not adopted |
| MedRAGChecker | Apache 2.0 (claimed by paper) | ✅ | Yes (local) | ❌ not adopted — not pip-installable |
| LightRAG | MIT | ✅ | Yes (local via Ollama) | ❌ not adopted as a library; the capability (multi-hop graph-RAG) is still outstanding, see item 9a |
| MediaPipe | Apache 2.0 | ✅ | Yes (local) | Not yet (CV extension) |
| YOLOv8 | AGPL | ⚠️ | Yes (with license) | Not yet (CV extension) |
| PyTorch | BSD | ✅ | Yes | ✅ (RAG/claims); not yet used for recommendations |
| Docker | Apache 2.0 | ✅ | Requires hardening | Not yet (backend scope) |
| PAMAP2 | CC BY 4.0 | ✅ | N/A (public research data) | Not yet (fitness recs) |
| WISDM | Free, research use | ✅ | N/A | Not yet (fitness recs) |
| Nutrition5k | CC BY 4.0 | ✅ | N/A | Not yet (CV extension) |
| USDA FoodData Central | Public domain | ✅ | N/A | ✅ (`ml/rag/ingest/usda.py` — reference-evidence ingestion, not CV) |
| CGMacros | CC BY-NC-SA 4.0 | ❌ (non-commercial) | N/A | Not yet (nutrition recs) |
| Food-101 | Research/fair-use only | ⚠️ | N/A | Not yet (CV extension) |
| Recipe1M+ | Non-commercial research/education only | ❌ | N/A | Not yet (CV extension) |
| AI4FoodDB | Research-only (see repo LICENSE.md) | ❌ | N/A — pending schema verification | Not yet |

**Note**: Adopted `ml/` tools are fully compliant with commercial + HIPAA-adjacent local deployment. Verify YOLOv8 licensing before any production CV use. Several nutrition datasets (CGMacros, Recipe1M+, AI4FoodDB) are non-commercial-only — fine for PHIRE's current research status, but flag them before any future commercial pivot. Full dataset rationale: [docs/DATASETS_AND_GRAPH_RAG.md](DATASETS_AND_GRAPH_RAG.md).

---

## Open-Source Contribution Opportunities

Consider contributing back:

1. **PHIRE-specific claim verification benchmark** (the 129-pair NLI eval set, `ml/claims/experiments/eval_data.py`) — a real benchmark result, not tied to MedRAGChecker (not adopted, see above)
2. **Exercise form feedback modules** (contribute to pose projects, once built)
3. **Healthcare benchmark toolkit** (extend scikit-learn)
4. **Documentation + tutorials** (Chroma, Neo4j, MedCPT communities — not LangChain, not adopted)

---

## Key Research Papers (2024-2026)

| Paper | Title | Relevance |
|-------|-------|-----------|
| 2025 | MedRAGChecker | Original inspiration for claim verification — **not adopted** (not installable); PHIRE built its own NLI-based verifier instead, see item 8 |
| 2025 | Medical Graph RAG | Entity-aware retrieval — conceptual basis for the graph-RAG leg, which is **not yet implemented**, see item 9a |
| 2025 | MEGA-RAG | Hallucination reduction |
| 2024 | VISA | Visual source attribution |
| 2024 | MedHallBench | Hallucination detection |
| 2024 | Real-Time Pose Correction | Exercise form feedback |
| 2024 | YOLOv8 Pose | Exercise detection |
| 2023 | Nutrition5k | Calorie estimation accuracy |
| 2025 | LightRAG (EMNLP) | Graph-based RAG — evaluated candidate for the not-yet-implemented graph-RAG leg (item 9a), not adopted as a dependency |
| 2025 | CGMacros (Scientific Data) | Personalized nutrition + glycemic outcome data |

---

## Quick Integration Checklist

- [x] Ollama + medgemma:4b + qwen3.5:9b + olmOCR-v2 running locally
- [x] Chroma vector DB initialized
- [x] MedCPT embedding + reranking models in use (not Sentence-Transformers' originally-listed models)
- [x] NLI-based claim verification implemented (`ml/claims/verifier.py`, BART-large-MNLI) — not MedRAGChecker (never installable)
- [x] pypdf + olmOCR-v2 extraction pipeline (not Docling)
- [x] Neo4j graph layer (`ml/graph/`) — direct Cypher, not LightRAG
- [ ] Multi-hop graph-RAG retrieval (LightRAG or alternative) — **outstanding, not yet started**, see `docs/GRAPH_SCHEMA_ROADMAP.md` §3f
- [ ] FastAPI endpoints wired to `ml/` (backend scope, not started)
- [ ] PostgreSQL schema (Chroma is the vector store, not pgvector)
- [ ] Docker Compose services defined
- [ ] MediaPipe Pose (CV extension, not started)
- [ ] YOLOv8 (CV extension, not started)
- [ ] Open Wearables docs reviewed (not started)
- [ ] AI4FoodDB schema pulled and verified before any ingestion code is written

---

**Status**: Core `ml/` tool choices implemented and benchmarked (see `ml/README.md`); backend/frontend/CV-extension tools not yet integrated
**Next**: See `ml/README.md`'s Features & Status, and `docs/AGGRESSIVE_ROADMAP.md`'s Extended Roadmap for what's next

