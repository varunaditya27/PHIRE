# PHIRE: Open-Source Tools & Integration Guide

**Status**: Comprehensive toolkit identified for MVP + extended phases
**Date**: August 2026
**Research Basis**: 2024-2026 active projects and papers

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
- **PHIRE Role**: Optional Month 2+ enhancement (entity-aware retrieval)
- **Approach**: Triple-graph construction (subject-predicate-object)
- **Why PHIRE**: Improves retrieval precision for complex medical queries

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

**14. Tesseract OCR**
- **GitHub**: [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
- **License**: Apache 2.0
- **Functionality**: Text extraction from image-based PDFs
- **PHIRE Role**: Scanned medical documents
- **Integration**: Docker container or system package
- **Why PHIRE**: Common for older medical reports

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
- **Source**: ETH Zurich (open access)
- **License**: Creative Commons (non-commercial)
- **Size**: 101 food categories, 101K images
- **PHIRE Role**: Pre-training + evaluation
- **Link**: [food-101.ethz.ch](http://food-101.ethz.ch/)
- **Why PHIRE**: Standard benchmark, excellent quality

**22. Recipe1M Dataset**
- **Source**: MIT-IBM (open access)
- **License**: Creative Commons BY-NC
- **Size**: 1M recipes + images + nutritional labels
- **PHIRE Role**: Recipe-to-nutrition linking
- **Features**: Ingredients + instructions + macros
- **Why PHIRE**: First recipe dataset with nutrition at scale

**23. Nutrition5k Dataset**
- **Source**: MIT-IBM (2021)
- **License**: Creative Commons BY-NC
- **Size**: 5K dishes, 10 images per dish, detailed nutrition
- **PHIRE Role**: Calorie estimation ground truth
- **Accuracy**: ~85% MAPE on macros
- **Why PHIRE**: Best accuracy for vision-based calorie estimation

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

**26. MediaPipe Pose**
- **GitHub**: [google/mediapipe](https://github.com/google/mediapipe)
- **License**: Apache 2.0
- **Functionality**: Real-time pose estimation (33 landmarks)
- **Maturity**: Production-ready (2024)
- **PHIRE Role**: Exercise form detection
- **Capabilities**:
  - 33-point skeletal model
  - <100ms latency on CPU
  - Webcam/video input
  - Mobile-native support
- **Why PHIRE**: Fastest (runs on Raspberry Pi), privacy-first

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

**29. Exercise Form Benchmarks**
- **Datasets**:
  - **HumanAI 3.6M**: 3.6M 3D pose sequences (various exercises)
  - **Custom labeled dataset**: Build from PHIRE user videos (month 3+)
  - **AI Gym Dataset**: Labeled workout exercises
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
- Medical Graph RAG
- MEGA-RAG
- YOLOv8, EfficientNet-B0
- MediaPipe Pose
- Open Wearables (prep)

### Month 4-6 (Phase 3)
➕ Add:
- Food-101, Recipe1M, Nutrition5k, USDA integration
- Custom HAR fine-tuning
- Exercise form models
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

**Note**: All MVP tools are fully compliant with commercial + HIPAA deployments. Verify YOLOv8 licensing for production use.

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

---

**Status**: All tools identified, MVP tools integration-ready
**Next**: Begin Week 1 implementation per CONTRIBUTING.md

