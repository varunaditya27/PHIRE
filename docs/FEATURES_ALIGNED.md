# PHIRE: Feature Specification (Aligned to NLP-06)

**Alignment**: Official RVCE NLP-06 problem statement + Comprehensive research (2023-2026)
**Date**: August 2026
**Version**: 1.0 (MVP focused)

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
- Ollama + MedGemma 1.5 8B
- Conversational query interface
- Real-time streaming responses
- **MVP Status**: ✅ Week 1-2

**2. Personalized Wellness Guidance** (NLP-06 §1, Objectives)
- Nutrition recommendations (LLM-powered)
- Fitness recommendations (HAR-model powered)
- Lifestyle guidance (evidence-backed)
- **MVP Status**: ✅ Week 2-3

**3. Health & Dietary Data Analysis** (NLP-06 §1, Objectives)
- Lab value ingestion & normalization
- Dietary data ingestion (manual entry)
- Historical trend analysis
- **MVP Status**: ✅ Week 1-2

**4. Laboratory Report Explanation** (NLP-06 §1, Objectives)
- PDF report parsing (Docling)
- Automatic value extraction
- Report summarization
- Plain-language explanations
- **MVP Status**: ✅ Week 1

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
- MedRAGChecker integration
- Interactive source highlighting (exact page/line numbers)
- Evidence status labels (SUPPORTED, DERIVED, INFERRED, UNCERTAIN, CONFLICTING)
- **Research Impact**: ⭐⭐⭐⭐⭐
- **MVP Status**: ✅ Week 2-3

**8. Longitudinal Health Reasoning** (Research, from NLP-06 §4.B)
- Temporal normalization of observations
- Health timeline visualization
- Trend detection (upward/downward/stable)
- Multi-year context reasoning
- Report-to-report comparison
- **Research Impact**: ⭐⭐⭐⭐⭐
- **MVP Status**: ✅ Week 1-2

**9. Hallucination Detection & Abstention** (Research, from NLP-06 §4.C)
- Unsupported claim detection
- Evidence sufficiency scoring
- Automatic abstention on low-confidence claims
- Safety gates for high-risk domains
- **Research Impact**: ⭐⭐⭐⭐
- **MVP Status**: ✅ Week 3

---

## TIER 2: Computer Vision Extensions (Months 2-6)

### Vision Feature A: Food Recognition & Calorie Estimation

**10. Food Image Recognition**
- Mobile camera integration
- Real-time food detection
- Multi-dish identification
- Portion size estimation (depth sensing)
- **Open-source tools**:
  - YOLOv8 or EfficientNet (food detection)
  - Food-101, UECFood100 datasets
  - USDA FoodData Central (nutrition reference)
- **MVP Status**: Month 3-4
- **Research Angle**: "How does food image analysis improve personalized nutrition recommendations vs. manual entry?"

**11. Calorie & Nutrition Estimation**
- Macro/micronutrient prediction from image
- Integration with user profile (dietary restrictions, goals)
- Comparison with logged meals (evidence-backed)
- Confidence scores on estimates
- **Tools**:
  - Recipe1M dataset (1M recipes + images + nutrition)
  - Nutrition5k dataset (~5K dishes with labels)
  - Transfer learning from ImageNet baseline
- **MVP Status**: Month 4-5
- **Research Angle**: "Can visual nutrition estimation achieve >85% macro accuracy vs. manual USDA reference?"

### Vision Feature B: Exercise Posture Analysis

**12. Real-time Pose Estimation**
- MediaPipe Pose (33 landmarks) or OpenPose
- Video/webcam input
- Joint angle computation
- **Open-source tools**:
  - MediaPipe Pose (TensorFlow Lite, local deployment)
  - OpenPose (OpenBLAS, GPU-optional)
  - PoseNet (lightweight, TensorFlow)
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
  - Injury prevention alerts
- **Tools**:
  - Custom models trained on form datasets
  - HumanAI3.6M (3.6M 3D poses)
  - DeepLabCut for multi-person pose
- **MVP Status**: Month 4-5
- **Research Angle**: "Does real-time form feedback improve exercise compliance and safety vs. generic recommendations?"

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

**18. Hybrid Structured + Semantic Retrieval** (NLP-06 §4.F)
- BM25 exact term matching (for lab values)
- Dense retrieval (semantic similarity)
- Reranking (authority, recency, relevance)
- **MVP Status**: Month 2-3

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
- **Ollama** (local LLM serving)
- **MedGemma 1.5** (medical model)
- **Chroma** (vector DB, native Python)
- **Docling** (PDF extraction)
- **FastAPI** (backend)
- **Next.js 15** (frontend)
- **PostgreSQL** (data persistence)

### Evidence Attribution
- **MedRAGChecker** (claim verification)
- **LangChain** (RAG orchestration)
- **Sentence-Transformers** (embeddings)

### Computer Vision
- **MediaPipe Pose** (pose estimation)
- **YOLOv8** (food detection)
- **USDA FoodData Central** (nutrition reference)
- **Recipe1M** (recipe + nutrition dataset)
- **Nutrition5k** (food image + macros)
- **Food-101** (food classification dataset)

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

**Prepared**: August 2026
**Status**: Ready for MVP implementation
**Next Step**: Begin Week 1 development per CONTRIBUTING.md work division
