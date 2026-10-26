# Autonomous Data-Analyst Agent — Full Project Plan

A portfolio project for an Associate AI/ML Engineer role: an agent that takes a plain-English
business question, figures out what data it needs (CSV, Excel, or a live database), writes and
runs SQL, generates a chart, and gives you a written insight — with full observability into what
it did and why.

---

## 1. Goal & Positioning

**One-line pitch (for your resume/README):**
> "An LLM-powered agent that answers natural-language business questions over any tabular data
> source (CSV, Excel, or SQL database) by generating and safely executing SQL, visualizing
> results, and summarizing insights — with guardrails, retries, and an observability dashboard."

**What it proves to a hiring manager:**
- You can build agentic systems with tool-calling (the #1 2026 hiring trend)
- You understand SQL generation risk and how to guard against it
- You think about data-source flexibility, not just a single hardcoded pipeline
- You build with observability/logging in mind (the MLOps differentiator)
- You can ship something with a live demo link, not just a notebook

---

## 2. Tech Stack

| Layer | Tool | Why |
|---|---|---|
| Data engine | **DuckDB** | Query CSV/Excel/Parquet/Postgres with the same SQL layer |
| File parsing | **pandas** (+ openpyxl) | Reads CSV and multi-sheet Excel workbooks |
| LLM | **Google Gemini API (free tier)**, fallback **Ollama** (Llama 3.2 / Qwen2.5) | Free, reliable tool-calling |
| Agent orchestration | **LangGraph** (or a simple custom loop) | Plan → execute → visualize → summarize |
| Backend | **FastAPI** | Async, typed, production-flavored |
| Frontend | **React** (Vite + Lucide React) | Sleek dark-mode UI, file uploader, chat studio, interactive profiling, metrics dashboard |
| Charts | **matplotlib / plotly** | Agent-generated visualizations |
| Logging/observability | **SQLite table + a React metrics tab** (or MLflow if you want it fancier) | Tracks runs, latency, success rate |
| Containerization | **Docker** | One-command run, portable |
| Deployment | **Render / Railway / HuggingFace Spaces** | Free live demo link |
| Version control | **Git + GitHub** | Public portfolio piece |

---

## 3. Architecture

```
                ┌─────────────────────────┐
                │      React Frontend     │
                │  (chat box + file       │
                │   upload + metrics tab) │
                └───────────┬─────────────┘
                            │ HTTP
                            ▼
                ┌─────────────────────────┐
                │      FastAPI Backend    │
                │  /upload   /ask  /stats │
                └───────────┬─────────────┘
                            │
                            ▼
                ┌─────────────────────────┐
                │   Ingestion Layer       │
                │  CSV / Excel / Postgres │
                │        → DuckDB         │
                └───────────┬─────────────┘
                            │
                            ▼
                ┌─────────────────────────┐
                │   Agent Orchestrator    │
                │      (LangGraph)        │
                │                         │
                │  plan → sql_tool →      │
                │  chart_tool →           │
                │  summarize_tool         │
                └───────────┬─────────────┘
                            │
                            ▼
                ┌─────────────────────────┐
                │   Logging / Trace DB    │
                │  (runs, latency, tokens,│
                │   success/failure)      │
                └─────────────────────────┘
```

---

## 4. Folder Structure

```
data-analyst-agent/
├── backend/
│   ├── main.py                # FastAPI app, routes: /upload /ask /stats
│   ├── ingestion.py           # CSV/Excel/Postgres → DuckDB loader
│   ├── agent/
│   │   ├── graph.py           # LangGraph orchestration
│   │   ├── tools_sql.py       # schema retrieval + SQL gen + guardrails
│   │   ├── tools_chart.py     # chart generation
│   │   └── tools_summary.py   # LLM summarization
│   ├── llm_client.py          # provider-agnostic call_llm() wrapper
│   ├── logging_db.py          # writes agent_runs to SQLite
│   └── models.py               # pydantic request/response schemas
├── frontend/
│   ├── src/                   # React app components & styles
│   └── package.json           # Frontend dependencies
├── data/
│   └── sample_dataset.csv      # a demo dataset shipped with the repo
├── tests/
│   ├── test_sql_guardrails.py
│   └── test_ingestion.py
├── Dockerfile
├── docker-compose.yml           # backend + frontend together
├── requirements.txt
├── .env.example                 # LLM API key placeholder
└── README.md
```

---

## 5. Step-by-Step Build Order & Current Status

### Phase 0 — Setup ✅ (Completed)
1. Python virtualenv, Git repo, and dependency baseline installed.
2. Dual LLM support configured (Google Gemini & Local Ollama).

### Phase 1 — Ingestion & Intelligent Profiling ✅ (Completed)
3. `ingestion.py`: CSV, multi-sheet Excel, DuckDB shared connection.
4. `profiling.py`: automated column type detection, null percentages, distinct cardinalities, PK detection, and data quality scoring (0–100).
5. `/profile/{dataset_id}` API endpoint and React profiling cards.

### Phase 2 — SQL Tool, Planning & Guardrails ✅ (Completed)
6. `tools_sql.py`: read-only `SELECT` enforcement, limit bounds, schema retrieval.
7. `tools_planner.py`: decomposed `AnalysisPlan` with reasoning steps.
8. Self-correction retry loop for query syntax recovery.

### Phase 3 — Memory & Multi-Table Joins ✅ (Completed)
9. Conversational memory checkpointing via LangGraph `MemorySaver`.
10. `tools_relations.py`: multi-table foreign-key discovery and join hints.
11. `tools_followup.py`: dynamic follow-up query suggestions.

### Phase 4 — Advanced Analytics Engine ✅ (Completed)
12. `tools_analytics.py`: Pearson & Spearman correlation matrices, IQR/Z-Score anomaly detection, and Holt's linear exponential smoothing time-series forecasting ($h=5$) with 95% confidence bands and MAE/RMSE calculations.
13. `node_analytics`: intent-based routing node in LangGraph.

### Phase 5 — Critic Verification Loop & Autonomous Investigation ✅ (Completed)
14. `tools_critic.py`: post-execution factual check, numerical grounding verification, hallucination detector, and automated self-correction loop.
15. `tools_autonomous.py`: zero-prompt dataset investigation, hypothesis generation, KPI summary calculation, Pareto breakdown, and executive intelligence report generation (`POST /analyze/{dataset_id}`).
16. React `AutonomousReportView.jsx`: dedicated executive dashboard with one-click follow-up navigation into the Chat Studio.

### Phase 6 — Evaluation & Benchmarking ⏳ (Next)
17. Golden SQL evaluation benchmark dataset (`tests/eval_benchmark.json`).
18. Automated evaluation execution script (`tests/run_eval.py`) tracking execution accuracy and token cost metrics.

---

## 6. How to "Vibe Code" This Effectively

Vibe coding works best when you give your AI coding assistant (Claude Code, Cursor, Copilot, etc.)
tight, scoped instructions rather than "build me the whole thing." Suggested approach:

1. **Feed it this plan** as context, then ask for one phase at a time — e.g. "Implement Phase 1 (ingestion.py) based on this plan. Use DuckDB and pandas."
2. **Review every SQL guardrail and execution path yourself** — this is the one part of the project where you genuinely need to understand what the code does, since it's your main talking point in interviews.
3. **Ask the assistant to write tests alongside code**, not after — "add a pytest test that confirms a DROP TABLE is rejected."
4. **Run and manually verify each phase before moving to the next** — don't let the assistant chain five phases unreviewed; agentic bugs compound.
5. **Ask it to explain tricky parts back to you** (e.g. "explain how the LangGraph retry loop works") so you can actually discuss it in an interview — a project you can't explain is a red flag, not a green one.
6. **Keep commits small and per-phase** — gives you a clean git history that itself shows methodical engineering practice if someone looks at your repo.

---

## 7. Suggested Timeline (part-time, evenings/weekends)

| Week | Focus |
|---|---|
| 1 | Phase 0-2 (setup, ingestion, SQL tool + guardrails) |
| 2 | Phase 3-4 (chart/summary tools, agent orchestration) |
| 3 | Phase 5-6 (backend API, frontend) |
| 4 | Phase 7-10 (logging, tests, deploy, README) |

---

## 8. Resume Bullet (once done)

> "Built an autonomous LLM agent (LangGraph + Gemini) that answers natural-language questions over
> CSV, Excel, or SQL data sources by generating and safely executing SQL with self-correction
> retries, auto-generating visualizations, and producing business summaries; instrumented with an
> observability dashboard tracking query success rate and latency. Deployed live on [Render/HF Spaces]."