# 🚀 Master Implementation Plan: Evolution of Autonomous Data Analyst Agent

> **Goal**: Evolve the existing functional NL-to-SQL system into an enterprise-grade, multi-agent autonomous data analyst.
> **Guiding Principle**: Zero disruption to existing working features (`FastAPI`, `LangGraph`, `DuckDB`, `React`, `Ollama/Gemini`). Every phase incrementally layers capabilities on top of the established baseline.

---

## 📌 Current Operational Status & Quick Resume Guide

- **Backend Service**: FastAPI running on **Port 8004** (`uvicorn backend.main:app --reload --port 8004`)
  *(Note: Port 8000 is occupied by a separate system process `OPS RAG` on this machine).*
- **Frontend Service**: Vite React running on **Port 5173** (`cd frontend && npm run dev`)
- **DuckDB Session Persistence**: Dataset files stored in `./uploads/{dataset_id}.duckdb` (persists across server reloads).
- **Execution Telemetry**: Stored in `./agent_runs.db` and rendered in the **Observability & Metrics** tab.
- **Frontend Configuration**: [frontend/src/config.js](file:///home/yashvi.soni/Yashvi%20Soni/Autonomous_Data_Analyst_Agent/frontend/src/config.js) and [frontend/.env](file:///home/yashvi.soni/Yashvi%20Soni/Autonomous_Data_Analyst_Agent/frontend/.env) (`VITE_BACKEND_URL=http://localhost:8004`).

### Recent Fixes & Completed Enhancements:
1. **Modernized File Upload Card**: Replaced standard cloud icon with a glowing spreadsheet badge, CSV/XLSX format pills, drag-and-drop animations, and active selected file badge with instant remove button.
2. **Autonomous Deep Dive Stabilization**: Enabled disk-backed DuckDB persistence, eliminating *"No tables found for dataset"* errors on server restarts, and automatic state reset when switching datasets.
3. **Real-Time Observability Query Logs**: Updated backend `/stats` and `ObservabilityDashboard.jsx` to render a comprehensive **Recent Query Execution Logs** table showing timestamps, dataset IDs, questions asked, generated SQL, latency, and retries.

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
  - Update React sidebar in `frontend/src/components/Sidebar.jsx` to display interactive dataset health cards upon file upload.

---

### Phase 2: Query Planning & Structured Agentic Workflow
*Focus: Transition from single-pass prompt generation to structured multi-step intent decomposition.*

- [x] **2.1 Structured Analysis Plan Schema (`backend/models.py`)**:
  - Define Pydantic schema for `AnalysisPlan` containing: `intent`, `metrics`, `dimensions`, `filters`, `time_range`, `operations`, and `required_steps`.
- [x] **2.2 Planner Node Upgrade (`backend/agent/graph.py`)**:
  - Refactor `node_plan` to invoke the LLM to output a structured `AnalysisPlan` before SQL generation.
  - Store the plan in `AgentState` to guide `node_sql` and `node_summarize`.
- [x] **2.3 UI Reasoning Trace**:
  - Display the generated step-by-step reasoning plan in React expanders (`"🎯 Agent Strategy & Decomposed Analysis Plan"`).

---

### Phase 3: Conversational Memory & Multi-Table Schema Integration
*Focus: Contextual follow-up questions and automatic multi-table relationship joins.*

- [x] **3.1 LangGraph State Checkpointing (`MemorySaver`)**:
  - Add thread/session state persistence so users can ask contextual follow-up questions (e.g., *"Now break that down by region"*).
  - Implement dynamic follow-up query suggestions at the end of each agent response (`backend/agent/tools_followup.py`).
- [x] **3.2 Multi-Table Relationship Inference (`backend/agent/tools_relations.py`)**:
  - Auto-discover foreign key relationships across multiple uploaded CSVs/Excel sheets.
  - Enhance schema context to generate clean multi-table `JOIN` statements automatically.
- [ ] **3.3 Schema Vector RAG Index (ChromaDB / FAISS)** *(Optional Scale Upgrade)*:
  - Embed large database schemas into local vector store to retrieve only top-k relevant tables for massive schemas.

---

### Phase 4: Advanced Analytics Engine (Statistics, Outliers & Forecasting)
*Focus: Expand beyond SQL queries to statistical testing, anomaly detection, and predictive modeling.*

- [x] **4.1 Statistical Analysis Tools (`backend/agent/tools_analytics.py`)**:
  - Pearson/Spearman correlation matrices for numerical columns.
  - Outlier detection via IQR (Interquartile Range) and Z-score methods.
- [x] **4.2 Time-Series Forecasting Tool**:
  - Holt's Linear Exponential Smoothing with trend projection and 95% confidence intervals.
  - Return forecasted metrics along with model accuracy scores (MAE / RMSE).
- [x] **4.3 Agent Routing Node (`AnalyticsRouter`)**:
  - LangGraph intent routing node (`node_analytics`) dynamically directing queries to SQL, Correlation, Outlier, or Forecast execution.

---

### Phase 5: Critic Verification Loop & Autonomous Investigation Mode
*Focus: Autonomous verification of answers and self-directed dataset exploration.*

- [x] **5.1 Critic / Verification Node (`node_critic`)**:
  - Add a post-execution LLM check comparing raw SQL outputs against executive summaries and charts.
  - Reject hallucinated data, mismatched metrics, or invalid chart types with auto-correction retries.
- [x] **5.2 Autonomous "Analyze Dataset" Mode**:
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
  - Surface cost and token breakdowns in the React Observability tab.

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
3. Modules will be introduced incrementally with fallbacks so the app is always runnable via `cd frontend && npm run dev` and `uvicorn backend.main:app`.
