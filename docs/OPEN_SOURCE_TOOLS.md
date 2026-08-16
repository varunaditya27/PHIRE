# PHIRE: Open-Source Tools & Integration Guide

**Status**: Comprehensive toolkit identified for MVP + extended phases
**Date**: August 2026
**Research Basis**: 2024-2026 active projects and papers
**Note**: Dataset/model choices in this doc are finalized in
[docs/DATASETS_AND_GRAPH_RAG.md](DATASETS_AND_GRAPH_RAG.md), which also
corrects one factual error (item 29, "HumanAI 3.6M") found during dataset
validation. That doc is authoritative where the two disagree.

---

## Overview

PHIRE integrates 30+ open-source tools across RAG, computer vision, medical LLMs, and evaluation. This document lists each tool with GitHub links, licensing, maturity, and PHIRE integration strategy.

---

## TIER 1: CORE MVP TOOLS (Weeks 1-3)

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

**2. MedGemma 1.5 8B**
- **Source**: Google DeepMind (open-weight via Ollama)
- **License**: Gemma License (commercial use allowed with attribution)
- **Functionality**: Medical foundation model, 91% USMLE score
- **Maturity**: 2026 latest version
- **PHIRE Role**: Primary clinical LLM
- **Integration**: `ollama pull medgemma:8b-q4_0` (~4.1GB quantized)
- **Alternative**: Meditron-7B (if MedGemma unavailable)
- **Why PHIRE**: 91% USMLE, open-weight, auditable, quantizable

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

**5. Sentence-Transformers**
- **GitHub**: [UKPLab/sentence-transformers](https://github.com/UKPLab/sentence-transformers)
- **License**: Apache 2.0
- **Functionality**: Dense embeddings (medical-optimized models)
- **Maturity**: Production-ready
- **PHIRE Role**: Document + query encoding
- **Models for PHIRE**:
  - `allenai-specter` (biomedical papers, 768-dim)
  - `pubmedbert` (PubMed abstracts, 768-dim)
  - `msmarco-distilbert-base-v4` (general retrieval)
- **Why PHIRE**: Fast (~50ms per document), medical-specialized

**6. BM25 / Rank-BM25**
- **GitHub**: [dorianbrown/rank_bm25](https://github.com/dorianbrown/rank_bm25)
- **License**: Apache 2.0
- **Functionality**: Lexical (exact term) matching
- **PHIRE Role**: Lab value queries ("LDL", "glucose")
- **Why PHIRE**: Critical for structured lab data where semantic fuzzing fails

---

### C. RAG & Evidence Attribution

**7. LangChain**
- **GitHub**: [langchain-ai/langchain](https://github.com/langchain-ai/langchain)
- **License**: MIT
- **Functionality**: Orchestration (RAG chains, memory, tools)
- **Maturity**: Production-ready (2026 stable)
- **PHIRE Role**: RAG pipeline orchestration
- **Integration**: Python package, pip install langchain
- **Why PHIRE**: Industry standard, OpenAI/Ollama support, retriever chains

**8. MedRAGChecker**
- **GitHub**: [chufangao/MedRAGChecker](https://github.com/chufangao/MedRAGChecker) [2025 paper]
- **License**: Apache 2.0
- **Functionality**: Claim-level verification for biomedical RAG
- **Maturity**: Research/early production (2025)
- **PHIRE Role**: Verifying each extracted claim against evidence
- **Paper**: "MedRAGChecker: Claim-Level Verification for Biomedical Retrieval-Augmented Generation" (2025)
- **Features**:
  - NLI (Natural Language Inference) for claim verification
  - SUPPORTED / REFUTED / UNDETERMINED labels
  - Confidence scoring per claim
- **Why PHIRE**: First system to atomically verify medical claims in RAG

**9. Medical Graph RAG**
- **Paper**: [ACL 2025](https://aclanthology.org/2025.acl-long.1381.pdf)
- **Functionality**: Graph-based RAG with entity linking
- **PHIRE Role**: Month 2-3, **finalized** (was "optional") — this is the
  conceptual basis for PHIRE's third retrieval leg. See items 9a/9b for the
  concrete tools and [docs/DATASETS_AND_GRAPH_RAG.md](DATASETS_AND_GRAPH_RAG.md)
  §3 for the full architecture and rationale.
- **Approach**: Triple-graph construction (subject-predicate-object)
- **Why PHIRE**: Vector/lexical retrieval is similarity-based and cannot
  answer multi-hop or relational questions ("how did my LDL change
  relative to my statin dose changes"); a graph makes those chains
  traversable instead of hoping embedding similarity surfaces them.

**9a. LightRAG** (Graph RAG implementation — finalized choice)
- **GitHub**: [HKUDS/LightRAG](https://github.com/HKUDS/LightRAG) · **Paper**: EMNLP 2025
- **License**: MIT
- **Functionality**: Graph-based RAG with local entity/relationship
  extraction and retrieval
- **Maturity**: Actively developed, multimodal support + RAGAS evaluation (2026)
- **PHIRE Role**: Primary graph-RAG library, replacing generic "Medical
  Graph RAG" as a concrete dependency
- **Why PHIRE**: Natively supports Ollama for entity/relationship
  extraction, so PHI never leaves the local boundary during graph
  construction — the deciding factor over Microsoft's GraphRAG, whose
  cloud-oriented, global-summarization design is a worse fit for
  real-time, per-patient, local queries. Published benchmarks show it
  outperforming naive RAG, HyDE, and Microsoft GraphRAG on retrieval
  accuracy and efficiency. Supports Neo4j, MongoDB, PostgreSQL, and
  OpenSearch as storage backends.

**9b. Neo4j (graph store)**
- **GitHub**: [neo4j/neo4j](https://github.com/neo4j/neo4j) · [neo4j/neo4j-graphrag-python](https://github.com/neo4j/neo4j-graphrag-python)
- **License**: GPLv3 (Community Edition, self-hosted)
- **Functionality**: Graph database backing LightRAG's entity/relationship graph
- **PHIRE Role**: Storage for the Longitudinal Health Graph (Observation /
  Medication / Condition / Claim nodes with temporal + provenance edges)
- **Why PHIRE**: Already PHIRE's candidate "graph layer" in the original
  architecture notes; self-hosted keeps it inside the local privacy
  boundary. A graph edge (`supports`, `contraindicated_by`,
  `conflicts_with`) doubles as an evidence/provenance link for free —
  directly reusable for fitness/nutrition recommendation attribution, not
  just medical claims.

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

**12. Docling**
- **GitHub**: [DS4SD/docling](https://github.com/DS4SD/docling)
- **License**: MIT
- **Functionality**: PDF → structured text + tables + figures
- **Maturity**: Production-ready (IBM released 2024)
- **PHIRE Role**: Lab report extraction
- **Integration**: `pip install docling`
- **Output**: JSON + markdown + table extraction
- **Why PHIRE**: Better than PyPDF2 for medical PDFs (handles tables)

**13. PyMuPDF (fitz)**
- **License**: AGPL (proprietary option available)
- **Functionality**: PDF extraction fallback
- **PHIRE Role**: Fallback if Docling unavailable
- **Why PHIRE**: Fast, lightweight

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

**14a. olmOCR-v2 (Allen AI)** — *finalized choice for patient document OCR*
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

## TIER 2: COMPUTER VISION TOOLS (Months 2-6)

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

## TIER 3: ML TRAINING & EVALUATION TOOLS (Months 3-9)

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

## TIER 4: WEARABLE & DEPLOYMENT TOOLS (Months 3+)

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

**43. PostgreSQL + pgvector**
- **GitHub**: [pgvector/pgvector](https://github.com/pgvector/pgvector)
- **License**: PostgreSQL (BSD-like)
- **Functionality**: Vector search in PostgreSQL
- **PHIRE Role**: Store embeddings + audit logs
- **Why PHIRE**: Faster than separate vector DB for small scale

---

## Integration Strategy by Phase

### MVP (Weeks 1-3)
✅ Required:
- Ollama, MedGemma
- Chroma, Sentence-Transformers, BM25
- LangChain, MedRAGChecker
- Docling, Spacy
- PyTorch, scikit-learn
- Docker, PostgreSQL

### Month 2-3 (Phase 2)
➕ Add:
- LightRAG + Neo4j (graph RAG — finalized third retrieval leg, see
  [docs/DATASETS_AND_GRAPH_RAG.md](DATASETS_AND_GRAPH_RAG.md))
- MEGA-RAG
- YOLOv8/EfficientNet-B0 (Food-101 classification backbone), MediaPipe Pose
- Open Wearables (prep)

### Month 4-6 (Phase 3)
➕ Add:
- Nutrition5k (primary CV nutrition training set), Food-101 (backbone),
  Recipe1M+ (nutrition-filtered subset), USDA FoodData Central integration
- PAMAP2 → WISDM HAR pretrain/fine-tune pipeline
- CGMacros personalization layer; AI4FoodDB only after schema verification
- Exercise form models (MediaPipe joint angles + Kaggle exercise-pose fine-tune)
- LoRA fine-tuning pipeline
- Weights & Biases tracking

### Month 7-9 (Phase 4)
➕ Add:
- FHIR representation
- Advanced evaluation (ablations, statistical tests)
- Paper-ready benchmarks

---

## Licensing & Compliance

| Tool | License | Commercial? | HIPAA-Ready? |
|------|---------|-----------|---|
| Ollama | MIT | ✅ | Yes (local) |
| MedGemma | Gemma | ✅ | Yes (local) |
| Chroma | Apache 2.0 | ✅ | Yes (local) |
| Docling | MIT | ✅ | Yes |
| LangChain | MIT | ✅ | Partial (requires Ollama) |
| MedRAGChecker | Apache 2.0 | ✅ | Yes (local) |
| MediaPipe | Apache 2.0 | ✅ | Yes (local) |
| YOLOv8 | AGPL | ⚠️ | Yes (with license) |
| PyTorch | BSD | ✅ | Yes |
| Docker | Apache 2.0 | ✅ | Requires hardening |
| MediaPipe | Apache 2.0 | ✅ | Yes (local) |
| YOLOv8 | AGPL | ⚠️ | Yes (with license) |
| PyTorch | BSD | ✅ | Yes |
| Docker | Apache 2.0 | ✅ | Requires hardening |
| LightRAG | MIT | ✅ | Yes (local via Ollama) |
| Neo4j (Community) | GPLv3 | ✅ (self-hosted) | Yes (local) |
| PAMAP2 | CC BY 4.0 | ✅ | N/A (public research data) |
| WISDM | Free, research use | ✅ | N/A |
| Nutrition5k | CC BY 4.0 | ✅ | N/A |
| USDA FoodData Central | Public domain | ✅ | N/A |
| CGMacros | CC BY-NC-SA 4.0 | ❌ (non-commercial) | N/A |
| Food-101 | Research/fair-use only | ⚠️ | N/A |
| Recipe1M+ | Non-commercial research/education only | ❌ | N/A |
| AI4FoodDB | Research-only (see repo LICENSE.md) | ❌ | N/A — pending schema verification |

**Note**: All MVP tools are fully compliant with commercial + HIPAA deployments. Verify YOLOv8 licensing for production use. Several finalized nutrition datasets (CGMacros, Recipe1M+, AI4FoodDB) are non-commercial-only — fine for PHIRE's current research status, but flag them before any future commercial pivot. Full dataset rationale: [docs/DATASETS_AND_GRAPH_RAG.md](DATASETS_AND_GRAPH_RAG.md).

---

## Open-Source Contribution Opportunities

After MVP, consider contributing back:

1. **PHIRE-specific claim verification dataset** (extend MedRAGChecker)
2. **Exercise form feedback modules** (contribute to pose projects)
3. **Healthcare benchmark toolkit** (extend scikit-learn)
4. **Documentation + tutorials** (LangChain, Chroma communities)

---

## Key Research Papers (2024-2026)

| Paper | Title | Relevance |
|-------|-------|-----------|
| 2025 | MedRAGChecker | Claim verification (CORE) |
| 2025 | Medical Graph RAG | Entity-aware retrieval |
| 2025 | MEGA-RAG | Hallucination reduction |
| 2024 | VISA | Visual source attribution |
| 2024 | MedHallBench | Hallucination detection |
| 2024 | Real-Time Pose Correction | Exercise form feedback |
| 2024 | YOLOv8 Pose | Exercise detection |
| 2023 | Nutrition5k | Calorie estimation accuracy |
| 2024 | Real-Time Pose Correction | Exercise form feedback |
| 2024 | YOLOv8 Pose | Exercise detection |
| 2023 | Nutrition5k | Calorie estimation accuracy |
| 2025 | LightRAG (EMNLP) | Local graph-based RAG (finalized) |
| 2025 | CGMacros (Scientific Data) | Personalized nutrition + glycemic outcome data |

---

## Quick Integration Checklist

- [ ] Ollama + MedGemma running locally
- [ ] Chroma vector DB initialized
- [ ] Sentence-Transformers model downloaded
- [ ] MedRAGChecker pseudocode → Python
- [ ] Docling extraction pipeline
- [ ] FastAPI endpoints wired to Ollama
- [ ] PostgreSQL + pgvector schema
- [ ] Docker Compose services defined
- [ ] MediaPipe Pose (placeholder for Month 3)
- [ ] YOLOv8 (placeholder for Month 3)
- [ ] Open Wearables docs reviewed (Month 3)
- [ ] MediaPipe Pose (placeholder for Month 3)
- [ ] YOLOv8 (placeholder for Month 3)
- [ ] Open Wearables docs reviewed (Month 3)
- [ ] LightRAG + Neo4j graph layer (Month 2-3, see DATASETS_AND_GRAPH_RAG.md)
- [ ] AI4FoodDB schema pulled and verified before any ingestion code is written

---

**Status**: All tools identified, MVP tools integration-ready
**Next**: Begin Week 1 implementation per CONTRIBUTING.md

