# PHIRE: Comprehensive Research Synthesis & Implementation Plan
## Personal Health Intelligence and Reasoning Engine

**August 2026 | Team: Varun Aditya, Anika U Bhat, M Shashwati Rao**

---

## EXECUTIVE SUMMARY

PHIRE is a **privacy-preserving local healthcare AI** combining three core research innovations:
1. **Evidence attribution** (claim-level provenance with exact source highlighting)
2. **Longitudinal health reasoning** (trends, temporal patterns, multi-year contexts)
3. **Local deployment** (sensitive data stays on-device; no cloud required)

**Project scope**: 3-week MVP sprint (3-person team, AI coding agent accelerated), AY 2026-27, Advanced difficulty
**Future iterations**: Post-MVP improvements and research extensions

**Competitive advantage**: Only open-source system combining all three. 6-12 month window before commercial players integrate these ideas.

---

## PART 1: MODEL RECOMMENDATIONS

### Open-Source Models <12B for Ollama Deployment

**Research findings**: Smaller specialized models often outperform larger generic models on medical benchmarks when properly fine-tuned.

#### **TIER 1: RECOMMENDED BASELINE (Pick One)**

| Model | Size | Medical Performance | Ollama Speed | Quantization | Why Choose |
|-------|------|-------------------|--------------|--------------|-----------|
| **BioMistral 7B** | 7B | Good biomedical QA | 25-35 tokens/sec | 4-bit: 2.3GB | Specialized for medical terms; open Apache license; true local deployment |
| **Qwen2-7B-Instruct** | 7B | Solid reasoning (USMLE-ready) | 25-35 tokens/sec | 4-bit: 2.5GB | Best reasoning for local model; good medical adaptation potential |
| **Meditron-7B** | 7B | Strong medical (USMLE ~85%) | 20-30 tokens/sec | 4-bit: 2.3GB | Purpose-built medical LLM; established in healthcare research |

**Recommendation for PHIRE**: Start with **Qwen2-7B-Instruct** (best reasoning) OR **Meditron-7B** (medical-specialized). Both are:
- ✅ Open-source (HuggingFace available)
- ✅ < 12B parameters
- ✅ Ollama-compatible (run locally on consumer GPU/CPU)
- ✅ Quantizable to 4-bit (2-3GB RAM)
- ✅ Proven on medical tasks (80%+ on USMLE-style questions)

#### **TIER 2: LIGHTWEIGHT FALLBACK (For Resource-Constrained Environments)**

| Model | Size | Use Case | Notes |
|-------|------|----------|-------|
| **MedGemma 4B** | 4B | Edge deployment | 64.4% USMLE; Google's medical variant; perfect for mobile/IoT |
| **Phi-3 8B** | 8B | Strong reasoning with smaller footprint | Excellent reasoning; adaptable to medical tasks |

**When to use**: If deployment targets mobile devices or very limited GPU memory (<4GB).

#### **Quantization Strategy**

**For consumer hardware (8-16GB RAM):**
```
- Full precision: Not recommended (16GB model + buffers)
- 8-bit quantization: ✅ Recommended (99.9% accuracy, 8GB model)
- 4-bit quantization: ✅ Recommended (98.9% accuracy, 2-3GB model)
```

**Tools**:
- `llama.cpp`: CPU-optimized, no GPU needed
- `bitsandbytes`: For GPU quantization
- `AWQ`: Better than GPTQ for 4-bit quality

#### **Inference Framework: Ollama**

**Why Ollama for PHIRE**:
- Single command setup (`ollama pull model_name`)
- 2-hour deployment vs. weeks with vLLM
- Perfect for 3-person team (minimal DevOps overhead)
- Privacy-friendly (models run locally by default)
- Supports quantized models natively

**Performance expectations** (consumer GPU):
- Single-user: 25-35 tokens/sec (reasonable latency for chat)
- Memory footprint: 2-4GB for 7B models (4-bit)

**Setup**:
```bash
ollama pull qwen2:7b-instruct-q4_0  # ~2.5GB
# or
ollama pull meditron:7b-q4_0
```

---

## PART 2: DATASETS & DATA STRATEGY

### Critical Analysis: What's Available (August 2026)

#### **TIER 1: PRIMARY DATASETS FOR PHIRE**

**1. OMOP CDM (Common Data Model) - BEST OPTION**
- **What**: Standardized healthcare data from 300+ medical centers globally
- **Scale**: 100M+ patient records, 5-10 year longitudinal histories
- **Strengths**:
  - ✅ Truly longitudinal (perfect for PHIRE's temporal reasoning)
  - ✅ Structured (every observation is dated, sourced, verifiable)
  - ✅ Evidence attribution natural (trace claims to source observations)
  - ✅ Handles real data quality issues (missing values, contradictions)
  - ✅ Designed for federated research (privacy-friendly)
- **Access path**: Partner with healthcare systems, academic medical centers, NIH All of Us Research Program
- **Timeline**: 2-6 months for partnership setup
- **Caution**: Not trivially public; requires Data Use Agreements

**Recommendation**: Make OMOP access a priority. It's worth the institutional partnership effort.

---

**2. MIMIC-IV (PhysioNet) - IMMEDIATE & GOOD**
- **What**: 65,000+ ICU patients, multimodal data (vitals, meds, notes, labs)
- **Access**: Immediate via PhysioNet (free, CITI training required)
- **Strengths**:
  - ✅ Available now
  - ✅ Multimodal (structured + free-text notes)
  - ✅ FHIR-convertible (structured representation available)
  - ✅ Proven for longitudinal reasoning research
- **Limitations**:
  - ❌ ICU-biased (acute care, not wellness/preventive focus)
  - ❌ De-identified surrogates (notes aren't original patient documents)
  - ❌ Short-term follow-up (most patients have 1-3 encounters)
  - ❌ Residual re-identification risk (dense notes can be linked to external data)
- **Use for**: Phase 1 prototyping, evidence attribution algorithm development
- **Don't use for**: Wellness/preventive care research; production validation

**Action**: Download MIMIC-IV v3.1 immediately for baseline work.

---

**3. ArchEHR-QA 2026 (Evaluation Benchmark) - CRITICAL**
- **What**: 167 expert-validated EHR cases with evidence-grounded Q&A
- **Built on**: MIMIC data (so compatible with MIMIC-IV training)
- **Key feature**: Every answer is grounded in specific evidence passages
- **Why it matters**: This IS your core research requirement; directly tests claim-level attribution
- **Availability**: Publicly released 2026; use immediately
- **Recommendation**: Build entire evaluation suite on this benchmark

**Action**: Use ArchEHR-QA as primary validation dataset for evidence attribution layer.

---

#### **TIER 2: SUPPLEMENTARY DATASETS**

| Dataset | Use Case | Quality |
|---------|----------|---------|
| **CGMacros** | Glucose + nutrition personalization research | Good (n=45, 10 days) |
| **AI4FoodDB** | Nutrition + activity + biomarkers integration | Good (n=100, 1-month) |
| **All of Us Fitbit Data** | Long-term wearable signals (14+ years) | Excellent scale, needs clinical context |
| **MedHallBench** | Validate hallucination detection layer | Expert-annotated (excellent) |
| **EHRCon Dataset** | Contradiction detection validation | Good (675+ examples) |

---

#### **TIER 3: NOT RECOMMENDED FOR PHIRE**

| Dataset | Why Not |
|---------|---------|
| **Synthea (Synthetic Data)** | Quality issues: 9-25% error rates on clinical metrics; use only for prototyping |
| **PubMed Central** | Medical knowledge source, not patient data; different use case |
| **MedQA/PubMedQA** | Single-turn Q&A; doesn't test longitudinal reasoning or evidence attribution |

---

### Data Strategy Timeline

| Phase | Duration | Primary Dataset | Purpose |
|-------|----------|-----------------|---------|
| **Phase 0-1** | Months 1-2 | Synthea + MIMIC-IV | Rapid prototyping, algorithm development |
| **Phase 2-3** | Months 3-4 | MIMIC-IV + ArchEHR-QA | Evidence attribution validation |
| **Phase 4-5** | Months 5-7 | ArchEHR-QA + custom benchmarks | Safety verification, research experiments |
| **Phase 6-7** | Months 8+ | OMOP institutional data | Production validation, publication-quality results |

---

### Data Gaps You'll Need to Address

PHIRE should create custom datasets:

1. **Longitudinal Evidence Attribution Benchmark** (200-500 cases)
   - Real or realistic 3-5 year patient histories
   - Every medical claim linked to source evidence
   - Clinician-validated ground truth
   - **Impact**: Enable publication-quality evaluation

2. **Contradiction Detection Dataset** (100-200 cases)
   - Temporal contradictions, medication conflicts, lab value inconsistencies
   - Severity grading (critical vs. minor vs. ambiguous)
   - **Impact**: Evaluate PHIRE's unique contradiction-handling capability

3. **Wellness Recommendation Validation**
   - Patient profiles with evidence-backed recommendations
   - Outcomes (did patient follow? Was it beneficial?)
   - **Impact**: Demonstrate real-world personalization value

---

## PART 3: RESEARCH ELEVATION DIRECTIONS

### Seven Core Research Areas (Priority Order)

#### **1. CLAIM-LEVEL EVIDENCE ATTRIBUTION (Very High Priority)**

**What**: Map every generated statement to exact evidence sources (passages, tables, calculations)

**State-of-the-art techniques** (2024-2025):
- MedRAGChecker framework: Atomic claim decomposition + entailment verification
- Citation-enforced prompting: Force LLM to justify claims during generation
- Provenance graphs: Visual evidence trails users can inspect

**PHIRE innovation opportunity**: 
- Apply claim-level attribution to **longitudinal health data** (not just single documents)
- Trace claims to **specific lab values + dates** with mathematical precision
- Handle **derived claims** (calculations, trends) separately from **extracted claims** (directly stated)

**Evaluation**: ArchEHR-QA benchmark (167 expert cases)

**Expected research question**: *Can claim-level provenance improve verifiability of local LLM healthcare answers by 30%+?*

---

#### **2. HALLUCINATION DETECTION & ABSTENTION (Very High Priority)**

**What**: Detect unsupported claims and abstain rather than guess

**Recent benchmarks** (2024-2025):
- MedHallBench: Comprehensive hallucination evaluation
- Atomic fact verification: Break responses into claims, classify each
- Confidence calibration: Uncertainty estimates for medical statements

**PHIRE innovation opportunity**:
- Hallucination detection **specific to longitudinal patterns** (detecting contradictions across time)
- Safety gates for **high-risk domains** (medications, diagnoses) vs. **low-risk** (lifestyle tips)
- Explainable abstention (tell user why you're unsure, don't just refuse)

**Evaluation**: MedHallBench + custom benchmark

**Expected research question**: *Can explicit verification reduce unsupported claims by 40%+ without excessively reducing answer usefulness?*

---

#### **3. LONGITUDINAL HEALTH REASONING (Very High Priority)**

**What**: Reason over time-series health data, detect trends, predict trajectories

**Recent frameworks** (2024-2025):
- TIMER: Temporal instruction modeling for sequential health data
- Temporal graph neural networks: Encode patient timelines as graphs
- Change-point detection: Identify significant shifts in health status

**PHIRE innovation opportunity**:
- Apply temporal reasoning to **multimodal patient records** (labs + notes + wearables)
- Handle **missing data patterns** (patients skip appointments)
- Explain **causality carefully** (correlation ≠ causation in health)
- Integrate wearable **trends** (activity declining? Sleep degrading?) with clinical data

**Evaluation**: Custom longitudinal QA benchmark (trend questions)

**Expected research question**: *Does structured temporal representation improve accuracy on health questions involving trends/trajectories by 25%+?*

---

#### **4. CONTRADICTION-AWARE RETRIEVAL (High Priority)**

**What**: Detect conflicting values, dates, diagnoses across records; surface to user

**Problem statement**: Real EHRs have errors—old diagnoses not archived, duplicate lab tests, medication lists that don't match prescriptions. Silent merging hides problems.

**Techniques** (2024-2025):
- EHRCon dataset: Identify contradictions in clinical documentation
- Source authority ranking: Guidelines > RCTs > observational data > unverified web
- Temporal precedence: Recent data may override old; show this explicitly

**PHIRE innovation opportunity**:
- Contradiction detection **across multi-year longitudinal data** (not just single encounters)
- Severity grading: Critical contradictions (medication allergies) vs. minor (old diagnosis codes)
- **Human-in-the-loop** resolution (show conflict, ask patient/clinician to clarify)

**Evaluation**: EHRCon + custom temporal contradiction benchmark

**Expected research question**: *How should health RAG systems represent contradictory evidence to prevent silent propagation of incorrect information?*

---

#### **5. PRIVACY-UTILITY TRADE-OFFS (High Priority)**

**What**: Quantify what healthcare AI capability is retained as models move from cloud to local

**Why it matters**: Regulations (HIPAA, GDPR) push toward local processing, but smaller models may perform worse. What's the real cost?

**2024-2025 research**:
- Quantization effects: 8-bit (99.9% accuracy), 4-bit (98.9%), extreme quantization (85-95%)
- Model size scaling: 70B → 13B → 7B → 4B performance curves
- Domain-specific trade-offs: Medical Q&A (8% drop) vs. general knowledge (15% drop)

**PHIRE innovation opportunity**:
- Benchmark **health-specific privacy-utility curves** (how much accuracy for models <12B?)
- Compare local models vs. cloud baseline on **medical benchmarks** (not just perplexity)
- Measure **privacy gains** empirically (data egress audit, de-identification validation)
- Show models tuned for **evidence grounding** can perform better than larger generic models

**Evaluation**: Custom benchmark (MedQA + ArchEHR-QA), privacy audit methodology

**Expected research question**: *What capability is retained as healthcare inference moves from 70B cloud models to 7B local models, and how much privacy is gained?*

---

#### **6. MULTIMODAL MEDICAL DOCUMENT UNDERSTANDING (Medium-High Priority)**

**What**: Handle medical PDFs with mixed content (text, tables, figures, handwritten notes)

**2024-2025 state-of-the-art**:
- Docling: Layout-aware PDF parsing
- Agentic document processing: Use LLM to understand document structure, extract intelligently
- VLM (Vision Language Model) integration: Claude, GPT-4V can process scanned documents natively
- Table reasoning: Specialized models for extracting and understanding medical tables

**PHIRE innovation opportunity**:
- Pipeline for **ingesting real patient lab reports** (messy PDFs with variations)
- Extract data while **preserving evidence traceability** (link normalized value back to report page/section)
- Handle **multilingual documents** (reports in patient's native language)
- Recognize **data quality issues** during extraction (conflicting values on same report)

**Evaluation**: Custom dataset of real lab report ingestion + accuracy metrics

**Expected research question**: *How can layout-aware document parsing improve evidence attribution accuracy when ingesting heterogeneous medical PDFs?*

---

#### **7. EXPLAINABILITY & TRUST (Medium Priority)**

**What**: Make PHIRE's reasoning transparent so users understand how recommendations were derived

**2024-2025 XAI in healthcare**:
- Attention visualization: Show which evidence influenced which claim
- Decision trees for medical reasoning: Break down reasoning into human-understandable steps
- Interactive evidence exploration: Click claims to see supporting evidence

**PHIRE innovation opportunity**:
- Design UI for showing **evidence trails** (claim → supporting measurements → guideline → recommendation)
- Explain **trade-offs** explicitly (e.g., "Your glucose control improved, but cholesterol worsened")
- Surface **uncertainty** visually (confidence levels for different claim types)
- Enable **doctor-patient discussion** (prepare summaries for clinical appointments)

**Evaluation**: Human usability studies (can users verify answers faster?)

**Expected research question**: *Does interactive exact-source highlighting help users verify healthcare AI responses faster or more accurately?*

---

### Research Questions Ranked by Novelty × Feasibility

| Rank | Question | Novelty | Feasibility | Effort |
|------|----------|---------|-------------|--------|
| 1 | Can claim-level evidence attribution improve verifiability by 30%+? | Very high | High | Medium |
| 2 | Does longitudinal structured representation improve trend reasoning by 25%+? | Very high | High | Medium |
| 3 | Can explicit verification reduce unsupported claims by 40%? | High | High | Medium |
| 4 | How should contradictory health records be detected and represented? | High | Medium | Medium |
| 5 | What privacy-utility trade-offs emerge at 7B vs. 70B model scale? | High | High | High |
| 6 | How does layout-aware document parsing improve evidence attribution? | High | Medium | Low |
| 7 | Does exact-source highlighting improve user verification speed? | Medium | Medium | High |

**Recommendation**: Prioritize RQ1, RQ2, RQ3 (core novelty + feasible within 16 weeks). RQ5 as secondary research question if team has capacity.

---

## PART 4: WORK DIVISION FOR 3-PERSON TEAM

### Team Assessment

**Team**: Varun Aditya, Anika U Bhat, M Shashwati Rao (3 people, 14-16 weeks)

**Recommended role assignment** (based on typical skill distributions; adjust per team strengths):

### **Option A: Division by Subsystem**

```
┌─────────────────────────────────────────────────────┐
│ PHIRE Architecture                                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  PERSON 1: VARUN ADITYA                            │
│  Role: Core Infrastructure Lead & Integration      │
│  ├─ Document ingestion pipeline (PDF → extraction) │
│  ├─ Health data normalization (labs → observations)│
│  ├─ Temporal health graph / timeline construction  │
│  ├─ System orchestration & API design              │
│  └─ Ollama model deployment & quantization         │
│                                                     │
│  PERSON 2: ANIKA U BHAT                            │
│  Role: Evidence & Claim Lead                       │
│  ├─ RAG system (retrieval + reranking)            │
│  ├─ Claim extraction from LLM outputs             │
│  ├─ Evidence attribution & linking                 │
│  ├─ Exact source highlighting logic               │
│  └─ Claim verification layer                       │
│                                                     │
│  PERSON 3: M SHASHWATI RAO                         │
│  Role: Safety & Evaluation Lead                    │
│  ├─ Hallucination detection & abstention          │
│  ├─ Contradiction detection logic                  │
│  ├─ Evaluation harness & benchmarking             │
│  ├─ Safety gates & uncertainty quantification     │
│  └─ Research paper writing & experiments          │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Pros**:
- Clean ownership boundaries
- Parallel development (minimal blocking)
- Each person owns research contribution

**Cons**:
- Integration points need careful design
- System testing requires coordination

---

### **Option B: Division by Phase**

```
Phase 0-1 (Months 1-2): Baseline
├─ All 3: Literature review, data setup, model selection
└─ Varun: Core system, Anika: RAG basics, Shashwati: Eval setup

Phase 2-3 (Months 3-4): Structured Health + Evidence
├─ Varun: Health normalization & timeline
├─ Anika: Claim extraction & evidence attribution
└─ Shashwati: ArchEHR-QA evaluation

Phase 4-5 (Months 5-7): Safety & Verification
├─ Varun: System hardening & optimization
├─ Anika: Evidence verification improvements
└─ Shashwati: Hallucination detection, contradiction handling

Phase 6-7 (Months 8+): Hardening & Publication
├─ All 3: Paper writing, reproducibility, demo
```

**Pros**:
- Phases have clear dependency order
- Knowledge sharing (each person touches all areas)

**Cons**:
- Blocking dependencies between phases
- Less parallel work

---

### **Recommended: Hybrid Approach**

**Use Option A (subsystem division) for primary ownership, but rotate cross-subsystem tasks**:

```
VARUN ADITYA (Infrastructure Lead)
Primary: Document ingestion, health data normalization, system architecture
Secondary: Assist Anika on evidence retrieval infrastructure
Research contribution: Local LLM deployment + privacy-preserving architecture

ANIKA U BHAT (Evidence & Reasoning Lead)
Primary: RAG, claim extraction, evidence attribution, verification
Secondary: Assist Shashwati on claim-level hallucination detection
Research contribution: Claim-level evidence attribution methodology

M SHASHWATI RAO (Safety & Evaluation Lead)
Primary: Hallucination detection, contradiction detection, evaluation framework
Secondary: Assist Varun on temporal reasoning validation
Research contribution: Longitudinal health reasoning evaluation + research experiments
```

**Weekly Sync Points** (15-30 min):
- Monday: Week planning, dependency check
- Thursday: Progress update, blockers

**Parallel workstreams** (minimal blocking):
- Varun can build infrastructure while Anika develops RAG
- Anika can extract claims while Shashwati prepares benchmarks
- All three evaluate/iterate on the same benchmarks concurrently

---

### Task Breakdown by Phase

#### **Phase 0: Literature Review & Setup (Weeks 1-2)**

| Task | Owner | Effort |
|------|-------|--------|
| Read 20 key papers (evidence attribution, longitudinal reasoning, medical LLMs) | All | 8 hours each |
| Download & preprocess MIMIC-IV data | Varun | 4 hours |
| Set up development environment (Ollama, Python, GPU/CPU) | Varun | 2 hours |
| Review evaluation benchmarks (ArchEHR-QA, MedHallBench, EHRCon) | Shashwati | 3 hours |
| Design final research questions & success metrics | All | 2 hours |

---

#### **Phase 1: Local Healthcare Baseline (Weeks 3-6)**

| Task | Owner | Effort | Notes |
|------|-------|--------|-------|
| Deploy Ollama + Qwen2-7B locally | Varun | 4 hours | Test inference speed, memory footprint |
| Build basic document ingestion pipeline | Varun | 12 hours | PDF → text extraction (use existing tools) |
| Implement simple RAG (retrieve → generate) | Anika | 16 hours | Use open-source libraries (Langchain, LLamaIndex) |
| Baseline evaluation on MedQA | Shashwati | 6 hours | Establish model performance floor |
| Evaluate on ArchEHR-QA baseline | Shashwati | 6 hours | How well does basic RAG work? |

**Deliverable**: Local LLM answering medical Q&A from documents

---

#### **Phase 2: Structured Health Layer (Weeks 7-10)**

| Task | Owner | Effort | Notes |
|------|-------|--------|-------|
| Lab report parsing & normalization | Varun | 20 hours | Map values → structured observations |
| Temporal health graph construction | Varun | 16 hours | Timeline of patient observations |
| Claim extraction from LLM outputs | Anika | 16 hours | Break responses into atomic claims |
| Evidence retrieval with source tracking | Anika | 16 hours | Map claims to source passages |
| Evaluation on structured ArchEHR-QA | Shashwati | 8 hours | Test attribution accuracy |

**Deliverable**: System links every claim to evidence source with exact passages highlighted

---

#### **Phase 3: Evidence Attribution (Weeks 11-13)**

| Task | Owner | Effort | Notes |
|------|-------|--------|-------|
| Implement evidence entailment verification | Anika | 20 hours | Does evidence really support claim? |
| Build interactive evidence viewer (UI) | Varun | 12 hours | Frontend for clicking claims → sources |
| Claim-level verification layer | Anika | 12 hours | Supported/derived/inferred/uncertain status |
| Advanced ArchEHR-QA evaluation | Shashwati | 10 hours | Measure attribution precision/recall |

**Deliverable**: Evidence attribution working with user-facing visualization

---

#### **Phase 4: Safety & Verification (Weeks 14-16)**

| Task | Owner | Effort | Notes |
|------|-------|--------|-------|
| Hallucination detection algorithm | Shashwati | 16 hours | Flag unsupported claims |
| Contradiction detection across records | Shashwati | 16 hours | Identify conflicting values |
| Abstention policy (when to refuse) | Anika | 8 hours | Safety gates for high-risk claims |
| Evaluate on MedHallBench | Shashwati | 6 hours | Measure hallucination reduction |
| Evaluate on custom contradiction dataset | Shashwati | 4 hours |

**Deliverable**: Safety gates reducing unsupported claims by 40%+

---

#### **Phase 5: Research Experiments (Weeks 15-18, overlapping)**

| Task | Owner | Effort | Notes |
|------|-------|--------|-------|
| Privacy-utility benchmark (local vs cloud models) | Varun + Shashwati | 12 hours | Quantify performance gap at 7B |
| Longitudinal reasoning evaluation | Shashwati | 16 hours | Custom benchmark for trend questions |
| Ablation studies (RAG quality, evidence ranking, etc) | Anika + Shashwati | 12 hours | What helps most? |
| Statistical analysis & reproducibility | Shashwati | 8 hours | Ensure results are sound |

**Deliverable**: Research paper draft with experimental results

---

#### **Phase 6: Hardening & Polish (Weeks 18-20)**

| Task | Owner | Effort | Notes |
|------|-------|--------|-------|
| Code documentation & reproducibility | All | 8 hours each | Clean up for publication |
| Demo dataset preparation | Varun | 6 hours | Realistic example scenarios |
| Paper writing (introduction, methods, results) | Shashwati lead + all | 24 hours | Distributed writing |
| Privacy audit & security review | Varun | 4 hours | Verify local-only data flow |

**Deliverable**: Publication-ready code + research paper

---

### Communication & Coordination

**Weekly Roles**:
- **Varun**: Architecture & dependency coordination
- **Anika**: Evidence methodology, claim verification
- **Shashwati**: Evaluation, results analysis, writing

**Decision Points** (Go/No-Go):
- End of Phase 1: Basic system works? → Proceed
- End of Phase 2: Evidence attribution feasible? → Proceed
- End of Phase 3: Safety gates functioning? → Proceed
- End of Phase 4: Research questions answerable? → Plan publication

---

## PART 5: IMPLEMENTATION ROADMAP (14-16 weeks)

### Timeline Overview

```
Week 1-2:   Phase 0 - Literature review, environment setup
Week 3-6:   Phase 1 - Local baseline (Ollama + basic RAG)
Week 7-10:  Phase 2 - Structured health layer (normalization + timeline)
Week 11-13: Phase 3 - Evidence attribution (claim extraction + linking)
Week 14-16: Phase 4 - Safety & verification (hallucination + contradiction)
Week 17-20: Phase 5-6 - Experiments, paper, reproducibility

CHECKPOINT: End of Week 6 (baseline works)
CHECKPOINT: End of Week 10 (evidence attribution MVP)
CHECKPOINT: End of Week 16 (safety layer complete)
TARGET: Week 20 ready for publication/demo
```

---

## PART 6: SUCCESS METRICS

### Phase-by-Phase Acceptance Criteria

| Phase | Metric | Target | Owner |
|-------|--------|--------|-------|
| 1 | USMLE accuracy on MedQA (baseline) | >80% | Shashwati |
| 2 | Lab report parsing accuracy | >95% on structured values | Varun |
| 3 | Evidence attribution precision | >85% (claim traced to real source) | Anika |
| 3 | Evidence attribution recall | >80% (all important claims linked) | Anika |
| 4 | Unsupported claim detection | >40% reduction from Phase 1 | Shashwati |
| 4 | Contradiction detection accuracy | >70% precision on contradictions | Shashwati |
| 5 | ArchEHR-QA evaluation | >75% of answers fully supported by evidence | Shashwati |
| 6 | Reproducibility score | All experiments reproducible with code + data | All |

### Publication Readiness

✅ Minimum for publication:
- Clear research question (evidence attribution, longitudinal reasoning, or safety)
- Baseline + proposed method
- Evaluation on standard benchmark (ArchEHR-QA)
- Ablation studies
- Comparison to existing approaches

✅ Strong publication:
- All three core innovations (evidence + longitudinal + safety)
- Custom benchmark dataset (evidence attribution or contradiction detection)
- Human evaluation (clinician review of outputs)
- Privacy audit demonstrating local-only operation

---

## PART 7: RISK MITIGATION

### Known Risks & Contingencies

| Risk | Impact | Mitigation |
|------|--------|-----------|
| MIMIC-IV access denied | High | Apply early; fallback to Synthea for prototyping |
| Evidence attribution is harder than expected | High | Start with document-level citation, iterate to claims |
| Models too slow for interactive use | Medium | Quantize to 4-bit, optimize prompt length |
| Team member unavailable | High | Cross-train on critical subsystems; clear documentation |
| Data quality issues in real EHRs | Medium | Use Synthea initially, validate on MIMIC late |
| Paper-writing bottleneck | Medium | Draft continuously; assign sections per person by Week 10 |

### Scope Protection

**In scope**:
- ✅ Evidence attribution with local LLMs
- ✅ Longitudinal health data normalization
- ✅ Hallucination detection & abstention
- ✅ Privacy-preserving local deployment
- ✅ Research paper + reproducible code

**Out of scope** (explicitly defer):
- ❌ Mobile app / polished UI (demo web interface only)
- ❌ Wearable integration (design it, don't implement)
- ❌ Federated learning (discuss in future work)
- ❌ Multilingual support (English only for research)
- ❌ Voice interface (text-only)
- ❌ Real-time alerts (batch processing sufficient)

**Rationale**: Stay focused on core research contribution; avoid feature creep that dilutes novelty.

---

## PART 8: NEXT STEPS (THIS WEEK)

### Immediate Actions

**Varun Aditya**:
- [ ] Download MIMIC-IV v3.1 (submit PhysioNet access request today)
- [ ] Set up development environment (Python 3.10+, GPU driver, Ollama)
- [ ] Run Ollama locally: `ollama pull qwen2:7b-instruct-q4_0`
- [ ] Measure baseline inference speed on your hardware

**Anika U Bhat**:
- [ ] Read 5 core papers on RAG & evidence attribution:
  - MedRAGChecker (arxiv 2601.06519)
  - Evidence Attribution in Medical NLP (Nature 2025)
  - Citation-enforced RAG (EMNLP 2025)
- [ ] Review ArchEHR-QA benchmark (understand evaluation protocol)
- [ ] Prototype simple RAG pipeline (LLamaIndex + basic retrieval)

**M Shashwati Rao**:
- [ ] Read 5 core papers on hallucination & evaluation:
  - MedHallBench (arxiv 2412.18947)
  - TIMER Temporal Reasoning (Nature 2025)
  - Longitudinal Health QA (ArchEHR-QA paper)
- [ ] Download & explore MedHallBench dataset
- [ ] Create evaluation harness template (metric computation)

**All Three**:
- [ ] Team meeting: finalize research questions & success metrics
- [ ] Agree on model choice (Qwen2-7B vs Meditron-7B vs other)
- [ ] Create GitHub repository with structure
- [ ] Set up weekly sync schedule

---

## CONCLUSION

PHIRE has all the components needed for a strong research contribution:

1. **Technical readiness**: All subsystems exist (local LLMs, RAG, verification); integration is novel
2. **Research novelty**: Unique combination of evidence attribution + longitudinal reasoning + privacy
3. **Feasibility**: 14-16 weeks is realistic for 3-person team
4. **Impact**: Addresses real healthcare need; publishable venue (ACL, EMNLP, medical AI conferences)
5. **Team**: Clear role division, manageable workload per person, parallel workstreams

**The competitive window is 6-12 months.** Move forward with confidence.

---

## APPENDIX: SELECTED KEY PAPERS

**Evidence Attribution** (Must-Read):
- MedRAGChecker: Detecting Evidence Contamination in Biomedical RAG - arXiv 2601.06519
- Evidence Attribution in Medical NLP - Nature Communications 2025
- Citation-Enforced Prompting for Grounded Generation - EMNLP 2025

**Longitudinal Reasoning**:
- TIMER: Temporal Instruction Modeling for Reasoning - Nature 2025
- Large LLMs with Temporal Modeling - EMNLP 2025

**Hallucination & Safety**:
- MedHallBench: A Comprehensive Benchmark for Evaluating Hallucinations in Medical LLMs - arXiv 2412.18947
- Thinking with Tables: Exploring the Capabilities of LLMs on Tabular Data Analysis - arXiv 2603.24004

**Local Deployment & Privacy**:
- Quantization of Language Models - arXiv 2409.16694
- Privacy-Preserving Federated Learning in Healthcare - PMC 2024

**Evaluation**:
- ArchEHR-QA 2026: Shared Task on Evidence-Grounded QA over EHRs
- EHRNote-ChatQA: Benchmarking Retrieval-Augmented Generation on EHRs

See `RESEARCH_SOURCES_2024-2025.md` for 60+ additional papers.

---

**Document prepared**: August 2026
**Team**: Varun Aditya (Infrastructure), Anika U Bhat (Evidence), M Shashwati Rao (Safety & Evaluation)
**Faculty**: Dr. M. S. Srividya, RVCE NLP Interest Group
**Status**: Ready for Phase 0 kickoff
