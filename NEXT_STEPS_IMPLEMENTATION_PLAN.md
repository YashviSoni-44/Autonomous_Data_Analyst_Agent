# 🚀 Master Implementation Plan: Evolution of Autonomous Data Analyst Agent

> **Goal**: Evolve the existing functional NL-to-SQL system into an enterprise-grade, multi-agent autonomous data analyst.
> **Guiding Principle**: Zero disruption to existing working features (`FastAPI`, `LangGraph`, `DuckDB`, `Streamlit`, `Ollama/Gemini`). Every phase incrementally layers capabilities on top of the established baseline.

---

## 📅 Roadmap Overview & Vision Progression

```
┌─────────────────┐     ┌───────────────────┐     ┌───────────────────────┐
│   Query Agent   │ ──► │   Analyst Agent   │ ──► │  Autonomous Analyst   │
│   (Current)     │     │ (Phases 1, 2, 3)  │     │    (Phases 4 & 5)     │
└─────────────────┘     └───────────────────┘     └───────────────────────┘
                                                              │
                                                              ▼
┌─────────────────┐     ┌───────────────────┐     ┌───────────────────────┐
│  Production AI  │ ◄── │ Reliable Analyst  │ ◄── │  Enterprise AI System │
│   (Phase 8)     │     │ (Phases 6 & 7)    │     │      Platform         │
└─────────────────┘     └───────────────────┘     └───────────────────────┘
```

---

## 🛠️ Phase-by-Phase Breakdown

### Phase 1: Baseline Stabilization & Intelligent Data Profiling
*Focus: Automatically analyze dataset structure, statistics, and quality BEFORE user questions are submitted.*

- [x] **1.1 Automated Profiling Engine (`backend/profiling.py`)**:
  - Extract column data types, row counts, missing value percentages, unique counts (cardinality), and sample values.
  - Detect candidate primary/foreign keys and datetime columns.
- [x] **1.2 Data Quality Scoring**:
  - Compute an overall dataset quality score (0–100) based on missingness, duplicates, and inconsistent types.
  - Surface potential warning flags (e.g., `"⚠️ Column 'discount' contains 15% missing values"`).
- [x] **1.3 Data Profiling API & UI Display**:
  - Add `/profile/{dataset_id}` endpoint in `backend/main.py`.
  - Update Streamlit sidebar in `frontend/app.py` to display interactive dataset health cards upon file upload.

---

### Phase 2: Query Planning & Structured Agentic Workflow
*Focus: Transition from single-pass prompt generation to structured multi-step intent decomposition.*

- [x] **2.1 Structured Analysis Plan Schema (`backend/models.py`)**:
  - Define Pydantic schema for `AnalysisPlan` containing: `intent`, `metrics`, `dimensions`, `filters`, `time_range`, `operations`, and `required_steps`.
- [x] **2.2 Planner Node Upgrade (`backend/agent/graph.py`)**:
  - Refactor `node_plan` to invoke the LLM to output a structured `AnalysisPlan` before SQL generation.
  - Store the plan in `AgentState` to guide `node_sql` and `node_summarize`.
- [x] **2.3 UI Reasoning Trace**:
  - Display the generated step-by-step reasoning plan in Streamlit expanders (`"🎯 Agent Strategy & Decomposed Analysis Plan"`).

---

### Phase 3: Conversational Memory & Multi-Table Schema Integration
*Focus: Contextual follow-up questions and automatic multi-table relationship joins.*

- [ ] **3.1 LangGraph State Checkpointing (`MemorySaver`)**:
  - Add thread/session state persistence so users can ask contextual follow-up questions (e.g., *"Now break that down by region"*).
  - Implement dynamic follow-up query suggestions at the end of each agent response.
- [ ] **3.2 Multi-Table Relationship Inference**:
  - Auto-discover foreign key relationships across multiple uploaded CSVs/Excel sheets.
  - Enhance `tools_sql.py` prompt context to generate clean multi-table `JOIN` statements automatically.
- [ ] **3.3 Schema Vector RAG Index (ChromaDB / FAISS)** *(Optional Scale Upgrade)*:
  - Embed large database schemas into local vector store to retrieve only top-k relevant tables for massive schemas.

---

### Phase 4: Advanced Analytics Engine (Statistics, Outliers & Forecasting)
*Focus: Expand beyond SQL queries to statistical testing, anomaly detection, and predictive modeling.*

- [ ] **4.1 Statistical Analysis Tools (`backend/agent/tools_analytics.py`)**:
  - Pearson/Spearman correlation matrices for numerical columns.
  - Outlier detection via IQR (Interquartile Range) and Z-score methods.
- [ ] **4.2 Time-Series Forecasting Tool**:
  - Detect time-series queries and invoke `statsmodels` (Exponential Smoothing / Holt-Winters) or baseline ARIMA.
  - Return forecasted metrics along with model accuracy scores (MAE / RMSE).
- [ ] **4.3 Agent Routing Node (`AnalyticsRouter`)**:
  - Add an intent classification router in LangGraph to direct queries to `SQL_Node`, `Statistical_Node`, or `Forecast_Node`.

---

### Phase 5: Critic Verification Loop & Autonomous Investigation Mode
*Focus: Autonomous verification of answers and self-directed dataset exploration.*

- [ ] **5.1 Critic / Verification Node (`node_critic`)**:
  - Add a post-execution LLM check comparing raw SQL outputs against executive summaries and charts.
  - Reject hallucinated data, mismatched metrics, or invalid chart types with auto-correction retries.
- [ ] **5.2 Autonomous "Analyze Dataset" Mode**:
  - Implement zero-prompt dataset analysis: agent independently formulates hypotheses, detects trend anomalies, ranks top findings, and generates an executive overview.

---

### Phase 6: Evaluation Harness & LLMOps Metrics
*Focus: Quantitative benchmarking and model performance tracking.*

- [ ] **6.1 Golden Dataset Benchmark (`tests/eval_benchmark.json`)**:
  - Build 20 curated Natural Language ➔ Ground Truth SQL pairs.
- [ ] **6.2 Automated Evaluation Script (`tests/run_eval.py`)**:
  - Benchmark query execution accuracy, SQL syntax success rate, and latency.
- [ ] **6.3 Cost & Token Intelligence**:
  - Track prompt & completion token consumption per query; calculate costs for Gemini vs. Ollama.
  - Surface cost and token breakdowns in the Streamlit Observability tab.

---

### Phase 7: Security Guardrails, PII Governance & Resource Limits
*Focus: Enterprise safety, privacy protection, and execution bounds.*

- [ ] **7.1 SQL Parsing & AST Validation**:
  - Enforce AST-level read-only checks using `sqlglot` or `sqlparse` (strictly block `DROP`, `DELETE`, `UPDATE`, `ALTER`, `CREATE`).
- [ ] **7.2 Execution Guardrails**:
  - Hard limit query execution time (timeout) and max returned row bounds.
- [ ] **7.3 PII Detection & Anonymization**:
  - Scan dataset columns for sensitive fields (Emails, Phone Numbers, SSNs) and automatically mask/redact them from output charts, summaries, and logs.

---

### Phase 8: Interactive Visualizations, Dynamic Reports & Containerization
*Focus: Frontend UX elevation and production deployment readiness.*

- [ ] **8.1 Dual Visualization Layer (Plotly + Matplotlib)**:
  - Add Plotly support for interactive charts (zoom, hover, tooltips) while retaining Matplotlib for static exports.
- [ ] **8.2 One-Click Executive PDF/HTML Export**:
  - Generate standalone, styled HTML/PDF business reports summarizing findings, metrics, and charts using `Jinja2` + `WeasyPrint`.
- [ ] **8.3 Production Docker Compose & CI/CD**:
  - Containerize frontend, backend, DuckDB storage, and optional Redis cache with healthchecks and automated GitHub Actions CI/CD workflows.

---

## 🔒 Backwards Compatibility Guarantee

To ensure existing code remains 100% operational throughout development:
1. All new nodes in `backend/agent/` will extend `AgentState` without removing existing fields.
2. New API endpoints in `backend/main.py` will be additive (`/profile`, `/ask_stream`, `/eval`) while keeping `/upload`, `/ask`, and `/stats` untouched.
3. Modules will be introduced incrementally with fallbacks so the app is always runnable via `streamlit run frontend/app.py` and `uvicorn backend.main:app`.
