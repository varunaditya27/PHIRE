# CHANGELOG

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-08-15

### Initial Setup & Documentation

**Added**
- Core documentation structure (README, CONTRIBUTING, GET_STARTED, REPO_STRUCTURE)
- Feature specification aligned to research requirements (docs/FEATURES_ALIGNED.md)
- Aggressive implementation roadmap (docs/AGGRESSIVE_ROADMAP.md)
- Open-source tools integration guide (docs/OPEN_SOURCE_TOOLS.md)
- Role division with clear responsibilities across 3-person team

**Team Roles**
- **Varun Aditya**: ML & Intelligence (RAG, claims, evidence attribution, recommendations)
- **Anika U Bhat**: Backend Infrastructure (FastAPI, Ollama, PostgreSQL, Chroma, Docker)
- **M Shashwati Rao**: Frontend & Evaluation (Next.js UI, metrics, benchmarks, research)

**Core Features (MVP - 3 weeks)**
- Local LLM conversational assistant (Ollama + MedGemma 1.5)
- Privacy-preserving data handling (no cloud APIs, encrypted storage)
- Evidence-attributed generation (claim-level verification with sources)
- Longitudinal health reasoning (temporal analysis over years)
- Hallucination detection & abstention (refuse to guess)
- Document processing & ingestion (PDF extraction, normalization)
- Health timeline visualization (interactive, trend-based)
- Fitness recommendations (HAR-based personalization)

**Extended Features (Months 2-9)**
- Nutrition recommendations (ML model trained on real data)
- Computer vision: Food recognition & calorie estimation
- Computer vision: Exercise posture analysis & form feedback
- Wearable integration (Fitbit, Oura, Apple Health, etc.)
- Contradiction detection (conflicting records)
- FHIR-compliant health representation
- Doctor-preparation summaries for clinical appointments

**Technology Stack**
- **LLM**: Ollama + MedGemma 1.5 (8B, 4-bit quantized)
- **Backend**: FastAPI (Python), PostgreSQL with pgvector
- **Vector DB**: Chroma (native Python)
- **Frontend**: Next.js 15 with TypeScript/React
- **Containerization**: Docker + Docker Compose
- **Evidence Attribution**: MedRAGChecker, LangChain
- **ML Training**: PyTorch, TensorFlow, Hugging Face
- **Evaluation**: ArchEHR-QA 2026, scikit-learn

**Open-Source Tools (40+ integrated)**
- RAG & Evidence: MedRAGChecker, Medical Graph RAG, MEGA-RAG, VISA, Docling, Spacy
- Computer Vision: YOLOv8, EfficientNet, MediaPipe Pose, OpenPose
- Food/Nutrition: Recipe1M, Nutrition5k, USDA FoodData Central, Food-101
- Embeddings: Sentence-Transformers, SciBERT, PubMedBERT
- Deployment: Open Wearables (wearable integration), Docker

**Project Structure**
- Flat directory layout (no `src/` wrapper)
- Parallel development paths (zero blocking between team members)
- Clear API contracts between subsystems
- Mock/stub implementation for Week 1 independence

**Success Metrics (MVP)**
- Response latency: <3 seconds end-to-end
- Evidence attribution precision: >85%
- Hallucination rate reduction: >40% vs baseline
- ArchEHR-QA accuracy: >75% claims fully supported
- Zero cloud data egress (privacy audit passes)

**Effort Estimate (MVP)**
- **Total**: 410 hours (3 weeks, ~137 hours per person)
- **Varun (ML)**: 115 hours
- **Anika (Backend)**: 125 hours
- **Shashwati (Frontend + Eval)**: 170 hours

**Extended Timeline (9 months)**
- **Phase 2 (Months 2-3)**: Advanced evidence & ML, wearable integration (260 hrs)
- **Phase 3 (Months 4-6)**: ML models & personalization (400 hrs)
- **Phase 4 (Months 7-9)**: Production hardening, regulatory, publication (420 hrs)
- **Total Extended**: 1,490 hours (~165 hours per person per month)

**Research Contributions (Publication-Ready)**
- Paper 1 (Month 4-5): Evidence attribution + longitudinal reasoning
- Paper 2 (Month 8-9): Hallucination detection + privacy-utility trade-offs
- Target venues: ACL, EMNLP, NeurIPS, Medical AI conferences
- Reproducible artifacts: Code, benchmarks, datasets

**Key Decisions**
- ✅ Local-only deployment (no cloud APIs)
- ✅ 8B model quantized for local inference
- ✅ Native vector DB (Chroma) for MVP simplicity
- ✅ Evidence-first design (every claim has sources)
- ✅ Three-person team with clear role division
- ✅ Aggressive but realistic 1.5x AI agent acceleration
- ✅ Computer vision as Month 2+ extension (not MVP bloat)

**Disclaimer**
PHIRE is NOT a medical device and NOT a substitute for professional medical advice. Designed for wellness and decision-support purposes only.

---

## Future Versions

See `docs/AGGRESSIVE_ROADMAP.md` for month-by-month breakdown of Phases 2-4.

