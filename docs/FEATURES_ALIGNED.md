# PHIRE: Feature Specification (Aligned to NLP-06)

**Alignment**: Official RVCE NLP-06 problem statement + Comprehensive research (2023-2026)
**Date**: August 2026
**Version**: 1.1 (dataset/model choices finalized — see
[docs/DATASETS_AND_GRAPH_RAG.md](DATASETS_AND_GRAPH_RAG.md))

---

## Executive Summary

PHIRE implements the NLP-06 requirements with three core research contributions:
1. **Privacy-preserving local inference** (official requirement)
2. **Evidence-attributed generation** (research novel contribution)
3. **Longitudinal health reasoning** (research novel contribution)

Plus **Computer Vision extensions** for multimodal health tracking:
- Food recognition & calorie estimation
- Exercise posture analysis & form feedback

---

## TIER 1: CORE MVP (Weeks 1-3, Aligns to NLP-06)

### Official NLP-06 Required Features

**1. Local LLM Conversational Assistant** (NLP-06 §1)
- Ollama + medgemma:4b (MedGemma ships only as 4B/27B, not "1.5"/"8B")
- Conversational query interface
- Real-time streaming responses
- **Status**: ✅ ML pipeline done (`ml/chains/qa_chain.py`) and wired through `backend`'s `POST /api/chat` (`docs/API_REFERENCE.md`), live-tested end-to-end; no token streaming (single blocking response — see that endpoint's docs) and frontend not yet built

**2. Personalized Wellness Guidance** (NLP-06 §1, Objectives)
- Nutrition recommendations (LLM-powered)
- Fitness recommendations (HAR-model powered)
- Lifestyle guidance (evidence-backed)
- **Status**: ❌ Not started (`ml/recommendations/` is stubs only)

**3. Health & Dietary Data Analysis** (NLP-06 §1, Objectives)
- Lab value ingestion & normalization
- Dietary data ingestion (manual entry)
- Historical trend analysis
- **Status**: ✅ Done for lab values (`ml/graph/`); dietary manual-entry ingestion not built

**4. Laboratory Report Explanation** (NLP-06 §1, Objectives)
- PDF report parsing (pypdf for text PDFs, olmOCR-v2 for scanned/photographed documents — not Docling)
- Automatic value extraction
- Report summarization
- Plain-language explanations
- **Status**: ✅ Done (`ml/rag/ingest/`)

**5. Privacy-Preserving Data Handling** (NLP-06 §1, Objectives)
- All data stays local (no cloud APIs)
- Encrypted storage
- HIPAA audit logging
- No patient data egress
- **MVP Status**: ✅ Week 1-3

**6. Secure Local Deployment** (NLP-06 §1, Objectives)
- Docker containerization
- Local network only
- No external API dependencies
- **MVP Status**: ✅ Week 1

### Research Novel: Evidence Attribution (Proposed Extension → Core)

**7. Claim-Level Evidence Attribution** (Research, from NLP-06 §4.A)
- Atomic claim extraction from LLM output
- Evidence retrieval & linking
- NLI-based verification (BART-large-MNLI, `ml/claims/verifier.py`) — not MedRAGChecker, which isn't installable (see `docs/OPEN_SOURCE_TOOLS.md`)
- Source highlighting via exact character spans (`ml/rag/ingest/chunking.py`'s `locate_chunk_offsets`) — not page/line numbers; frontend rendering of this not yet built
- Evidence status labels: SUPPORTED, DERIVED, CONFLICTING, UNCERTAIN, UNSUPPORTED (not INFERRED — no validated signal exists for multi-hop-reasoning claims yet, see `ml/claims/verifier.py`'s docstring)
- **Research Impact**: ⭐⭐⭐⭐⭐
- **Status**: ✅ ML pipeline done and live-tested; frontend evidence display not yet built

**8. Longitudinal Health Reasoning** (Research, from NLP-06 §4.B)
- Temporal normalization of observations
- Health timeline visualization
- Trend detection (upward/downward/stable)
- Multi-year context reasoning
- Report-to-report comparison
- **Research Impact**: ⭐⭐⭐⭐⭐
- **Status**: ✅ Graph-backed trend computation done (`ml/graph/patient_context.py`'s `get_trend_facts`, feeds `DERIVED` claim labeling); timeline visualization (frontend) not yet built

**9. Hallucination Detection & Abstention** (Research, from NLP-06 §4.C)
- Unsupported claim detection
- Evidence sufficiency scoring
- Automatic abstention on low-confidence claims
- Safety gates for high-risk domains
- **Research Impact**: ⭐⭐⭐⭐
- **Status**: ✅ Done and live-tested (`ml/chains/qa_chain.py`'s `ABSTENTION_THRESHOLD`)

---

## TIER 2: Computer Vision Extensions (Months 2-6)

### Vision Feature A: Food Recognition & Calorie Estimation

**10. Food Image Recognition**
- Mobile camera integration
- Real-time food detection
- Multi-dish identification
- Portion size estimation (depth sensing)
- **Open-source tools (finalized)**:
  - YOLOv8 or EfficientNet-B0 (food detection/classification)
  - Food-101 dataset — **classification backbone only**; category labels
    carry no macro/portion data, so this stage answers "what dish is this,"
    not "what's in it"
  - USDA FoodData Central (nutrition reference, joined after identification)
- **MVP Status**: Month 3-4
- **Research Angle**: "How does food image analysis improve personalized nutrition recommendations vs. manual entry?"

**11. Calorie & Nutrition Estimation**
- Macro/micronutrient prediction from image
- Integration with user profile (dietary restrictions, goals)
- Comparison with logged meals (evidence-backed)
- Confidence scores on estimates
- **Tools (finalized)**:
  - **Nutrition5k dataset — primary training set.** CC BY 4.0 (commercial
    use permitted), weighed (not estimated) ground truth, clean per-dish
    and per-ingredient CSV schema. Promoted ahead of Recipe1M+ after
    dataset validation found it to be the only CV nutrition dataset with
    unrestricted licensing and directly-usable columns.
  - Recipe1M+ dataset — recipe/meal generation and recipe↔image linking
    only; its nutrition fields cover a subset of recipes (only those with
    parsed unit+quantity), so it is a secondary source for macro ground
    truth, not primary
  - Transfer learning from ImageNet baseline
- **MVP Status**: Month 4-5
- **Research Angle**: "Can visual nutrition estimation achieve >85% macro accuracy vs. manual USDA reference?"

### Vision Feature B: Exercise Posture Analysis

**12. Real-time Pose Estimation**
- MediaPipe Pose (33 landmarks) — **finalized as the primary approach; no
  custom pose model is trained.** OpenPose kept only as a slower,
  higher-accuracy fallback for group-fitness scenarios.
- Video/webcam input
- Joint angle computation directly from MediaPipe's 33-point x/y/z +
  visibility output
- **Open-source tools**:
  - MediaPipe Pose (TensorFlow Lite, local deployment) — run directly, this
    replaces training on a pose dataset entirely
  - OpenPose (OpenBLAS, GPU-optional) — fallback only
- **MVP Status**: Month 3-4
- **Research Angle**: "Can local pose estimation provide exercise form feedback without cloud processing?"

**13. Exercise Form Analysis**
- Rep counting (squat depth, push-up form)
- Posture correctness (alignment, range of motion)
- Form correction feedback (real-time, evidence-backed)
- Exercise type classification (squat, lunge, deadlift, etc.)
- **Integration with fitness recommendations**:
  - Link form feedback to user's current fitness level
  - Progressive difficulty tracking
  - Injury prevention alerts *(soften this claim, or back it with a proper
    study — see fit issue below)*
- **Tools (corrected after dataset validation)**:
  - MediaPipe Pose joint angles as the input feature (no separate pose
    dataset needed)
  - Kaggle exercise-pose datasets (e.g. "Squat Exercise Pose Dataset") to
    fine-tune an MVP form-scoring classifier on top of those joint angles
  - ~~HumanAI3.6M (3.6M 3D poses)~~ — **removed.** This referenced
    Human3.6M, whose 17 activities are indoor daily-life poses (phone
    calls, smoking, discussing), not exercises — no squat/push-up/lunge
    class exists in it. It is also academic-account-gated and
    non-redistributable. See
    [docs/DATASETS_AND_GRAPH_RAG.md](DATASETS_AND_GRAPH_RAG.md) §2.5.
- **MVP Status**: Month 4-5
- **Research Angle**: "Does real-time form feedback improve exercise compliance and safety vs. generic recommendations?"
- **Fit issue**: Kaggle exercise-pose datasets are small, crowd-sourced,
  and unevenly licensed — fine for an MVP demo, not a sufficient basis on
  their own for a clinically-flavored "injury prevention" claim.

### Vision Integration with Evidence Attribution

**14. Grounded Nutrition Analysis**
- Link calorie estimates to USDA FoodData Central evidence
- Show confidence (how certain is the estimate?)
- Alternative serving suggestions with macro breakdowns
- Evidence-backed portion recommendations
- **Example output**:
  ```
  "This appears to be a ~200g chicken breast (155 cal, 31g protein, 3g fat)"
  - Estimate confidence: 87% (based on color, size, shape similarity)
  - USDA reference: Chicken breast, skinless, cooked, 100g = 77 cal, 15.5g protein, 1.8g fat
  - Alternative portions: 150g (~115 cal), 250g (~192 cal)
  ```

**15. Form-Based Fitness Recommendations**
- Current fitness level assessment from pose data
- Personalized exercise modifications
- Progressive overload tracking
- Safety alerts (poor form, injury risk)
- **Example**: "Your squat depth is 82° (target 90°). Here are 3 mobility exercises to improve range of motion."

---

## TIER 2: Research-Grade Features (Months 2-9)

### From NLP-06 §4 (Proposed Extensions)

**16. Contradiction-Aware Health RAG** (NLP-06 §4.D)
- Detect conflicting values across records
- Source authority ranking (lab report > wearable > manual entry)
- Temporal precedence logic
- **MVP Status**: Month 2-3

**17. Privacy-Utility Benchmarking** (NLP-06 §4.E)
- Compare 7B local vs 70B cloud models
- Measure accuracy, latency, privacy
- Quantized model evaluation
- **MVP Status**: Month 4-6

**18. Hybrid Structured + Semantic + Graph Retrieval** (NLP-06 §4.F, extended)
- BM25 exact term matching (for lab values) — ✅ done
- Dense retrieval (semantic similarity, Chroma) — ✅ done
- **Graph-backed patient facts** — ✅ done: `ml/graph/` (Neo4j, direct
  Cypher, not LightRAG) stores structured Observation/Medication/Condition
  facts and precomputes trend deltas, read into chat via
  `ml/graph/patient_context.py`.
- **Multi-hop graph-RAG traversal — ❌ not yet implemented, outstanding
  work.** Questions requiring entity/relationship traversal at query time
  ("how did my LDL change relative to my statin dose changes" as one hop,
  or surfacing conflicts via explicit `conflicts_with`/`supersedes`
  edges) aren't answerable yet — today's graph layer is single-patient
  fact *lookup*, not traversal. See
  [docs/GRAPH_SCHEMA_ROADMAP.md](GRAPH_SCHEMA_ROADMAP.md) §3f for the
  detailed status and what's needed to build it. LightRAG itself was
  evaluated as a candidate library for this and not adopted (see
  [docs/DATASETS_AND_GRAPH_RAG.md](DATASETS_AND_GRAPH_RAG.md) §3) — that's
  a decision about *how*, not *whether*, to build this leg.
- Reranking (authority, recency, relevance) — ✅ done, benchmarked (`ml/rag/reranker_experiments/RESULTS.md`)

**19. Evidence Quality Ranking** (NLP-06 §4.G)
- Authority tiers (guidelines > RCTs > observational)
- Recency weighting
- Population relevance
- Guideline version awareness
- **MVP Status**: Month 4-5

**20. FHIR Health Representation** (NLP-06 §4.I)
- FHIR-compliant observation/condition/medication models
- Interoperability with healthcare systems
- Export/import capabilities
- **MVP Status**: Month 6-8

**21. Doctor-Preparation Summaries** (NLP-06 §4.J)
- Concise health trend summaries
- Evidence-backed questions for clinician
- Supporting evidence bundles
- **MVP Status**: Month 4-5

---

## TIER 3: Future Research (Months 9+)

From NLP-06 §4 (Later Extensions):

- **22. Wearable Integration** (NLP-06 §4.H, Possible Extensions)
- **23. Federated Learning** (NLP-06 Possible Extensions)
- **24. Multilingual Support** (NLP-06 Possible Extensions)
- **25. Voice Interface** (NLP-06 Possible Extensions)
- **26. IoT Device Integration** (NLP-06 Possible Extensions)

---

## Alignment to Official NLP-06 Outcomes

| NLP-06 Outcome | PHIRE Implementation | Status |
|---|---|---|
| Privacy-preserving healthcare chatbot | Features 1, 5, 6 | MVP ✅ |
| Personalized nutrition recommendations | Features 2, 11, 14 | MVP + Vision ✅ |
| Personalized fitness recommendations | Features 2, 12, 13, 15 | MVP + Vision ✅ |
| Calorie tracking & dashboard | Features 3, 11, 14 | Vision ✅ |
| Laboratory report summaries | Features 4, 7 | MVP ✅ |
| Simplified report explanations | Features 4, 8 | MVP ✅ |
| Preventive wellness alerts | Features 2, 8, 19 | MVP ✅ |
| Locally deployed secure AI assistant | Features 1, 5, 6 | MVP ✅ |

---

## Open-Source Tools Integrated

### Core Infrastructure
- **Ollama** (local LLM serving) — medgemma:4b (chat), qwen3.5:9b (prose extraction), olmOCR-v2 (OCR)
- **Chroma** (vector DB, in-process)
- **pypdf + olmOCR-v2** (PDF/OCR extraction — not Docling)
- **FastAPI** (backend)
- **Next.js 15** (frontend)
- **PostgreSQL** (data persistence)

### Evidence Attribution
- **BART-large-MNLI** (NLI-based claim verification — not MedRAGChecker, which isn't installable; see `docs/OPEN_SOURCE_TOOLS.md`)
- Hand-written QA orchestration (`ml/chains/qa_chain.py`) — LangChain was evaluated and not adopted
- **MedCPT** (dual-encoder embeddings + cross-encoder reranking)
- **Neo4j** (graph store, direct Cypher — not LightRAG; multi-hop graph-RAG retrieval is not yet implemented, see Feature 18)

### Computer Vision
- **MediaPipe Pose** (pose estimation — run directly, no training)
- **YOLOv8 / EfficientNet-B0** (food detection/classification)
- **USDA FoodData Central** (nutrition reference — essential grounding source)
- **Nutrition5k** (primary CV nutrition training set — CC BY 4.0, weighed ground truth)
- **Recipe1M+** (recipe generation + recipe↔image linking; nutrition-filtered subset only)
- **Food-101** (classification backbone only, not a nutrition source)
- **Kaggle exercise-pose datasets** (MVP-only form-scoring fine-tune)

### Fitness & Nutrition Tabular ML
- **PAMAP2 → WISDM** (HAR pretrain → fine-tune pipeline)
- **CGMacros** (nutrition personalization/outcome layer)
- **AI4FoodDB** (candidate, pending schema verification — not yet committed)

### ML Training
- **PyTorch/TensorFlow** (model training)
- **Hugging Face** (pretrained models)
- **scikit-learn** (classical ML)

---

## Research Contributions (Publication-Ready)

### Paper 1: Evidence Attribution + Longitudinal Reasoning
- **Title**: "PHIRE: Privacy-Preserving Local Healthcare AI with Claim-Level Evidence Attribution"
- **Contributions**: Features 1, 2, 7, 8, 9
- **Timeline**: Month 4-5 (paper writing), submit Month 6
- **Venues**: ACL, EMNLP, Medical AI

### Paper 2: Computer Vision + Multimodal Integration
- **Title**: "Multimodal Food & Exercise Analysis with Local Computer Vision for Personalized Wellness"
- **Contributions**: Features 10-15
- **Timeline**: Month 7-8 (paper writing), submit Month 9
- **Venues**: CVPR, ICCV, Medical AI, Nutrition

### Benchmark Release
- **Claim-level evidence attribution benchmark** (custom dataset from PHIRE)
- **Exercise posture dataset** (pose sequences + form labels)
- **Food recognition + nutrition dataset** (images + structured macros)

---

## Success Metrics (Evaluation)

| Feature | Metric | Target | MVP |
|---|---|---|---|
| Evidence attribution accuracy | Precision/Recall | >85% | ✅ |
| Hallucination reduction | Unsupported-claim rate | <15% | ✅ |
| Trend reasoning accuracy | Trend QA accuracy | >80% | ✅ |
| Food recognition accuracy | Top-1 accuracy | >90% | Month 3 |
| Calorie estimation error | MAPE vs USDA | <15% | Month 4 |
| Posture estimation accuracy | Joint angle error | <10° | Month 3 |
| Exercise form accuracy | Rep counting accuracy | >95% | Month 4 |

---

## Scope Control (What We're NOT Doing)

✅ **In scope**:
- Evidence attribution + verification
- Longitudinal reasoning
- Food/exercise computer vision
- Privacy-preserving local deployment

❌ **Out of scope (this sprint)**:
- Autonomous diagnosis (wellness only)
- Wearable integration (defer to Month 6+)
- Federated learning (future research)
- Multilingual support (future)
- Voice interface (future)

---

## Alignment Statement

This feature specification is authoritative for PHIRE development and directly implements:
- **Section 1 (Executive Summary)** of NLP-06 official requirements
- **Section 4 (Research Directions)** proposed research extensions
- **Section 8 (Candidate Feature Set)** Tier 0, 1, 2 maturity levels
- **Section 15 (Expected Outcomes)** all outcome categories

Computer vision features (10-15) extend NLP-06 scope with novel research angles while maintaining core privacy and local-deployment requirements.

---

**Prepared**: August 2026, updated 2026-08-28
**Status**: Tier 1 core ML pipeline (features 1, 3, 4, 7, 8, 9, part of 18) implemented and live-tested — see [ml/README.md](../ml/README.md) for details. `backend/` is now wired to it end-to-end (see [backend/README.md](../backend/README.md), [docs/API_REFERENCE.md](API_REFERENCE.md)); `frontend/` integration, recommendations (feature 2), Tier 2 CV extensions, and multi-hop graph retrieval are not yet built — see [docs/BACKLOG.md](BACKLOG.md) for the current open-items list.
**Next Step**: See [docs/FRONTEND_HANDOFF.md](FRONTEND_HANDOFF.md) to start `frontend/` work; `ml/README.md`'s Features & Status for `ml/`-specific next steps; CONTRIBUTING.md for cross-team work division
