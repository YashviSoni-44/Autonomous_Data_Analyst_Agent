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
| Frontend | **Streamlit** | Fast to build, file upload + chat UI in one file |
| Charts | **matplotlib / plotly** | Agent-generated visualizations |
| Logging/observability | **SQLite table + a Streamlit metrics tab** (or MLflow if you want it fancier) | Tracks runs, latency, success rate |
| Containerization | **Docker** | One-command run, portable |
| Deployment | **Render / Railway / HuggingFace Spaces** | Free live demo link |
| Version control | **Git + GitHub** | Public portfolio piece |

---

## 3. Architecture

```
                ┌─────────────────────────┐
                │   Streamlit Frontend    │
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
│   └── app.py                  # Streamlit UI
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

## 5. Step-by-Step Build Order

### Phase 0 — Setup (Day 1)
1. Install Python 3.11+, Git, and an editor (VS Code / Cursor).
2. `mkdir data-analyst-agent && cd data-analyst-agent && git init`
3. Create a virtual environment: `python -m venv venv && source venv/bin/activate` (or `venv\Scripts\activate` on Windows)
4. `pip install fastapi uvicorn duckdb pandas openpyxl langgraph langchain-google-genai streamlit matplotlib plotly python-dotenv pytest`
5. Get a free Gemini API key from Google AI Studio, put it in `.env` (never commit this file — add to `.gitignore`).
6. Grab a demo dataset (Kaggle e-commerce/sales CSV, or export a few Excel sheets) and drop it in `/data`.

### Phase 1 — Ingestion Layer
7. Write `ingestion.py`: functions `load_csv(path)`, `load_excel(path)` (loop over `pd.read_excel(path, sheet_name=None)` for multi-sheet), `load_postgres(conn_str)` — each registers tables into a shared DuckDB connection.
8. Write a `get_schema(duckdb_conn)` helper that queries `information_schema` and returns table/column names + types as a string the LLM can read.
9. Test manually: load your sample CSV, confirm you can `SELECT * FROM table LIMIT 5` through DuckDB.

### Phase 2 — SQL Tool + Guardrails
10. Write `tools_sql.py`: a function that takes `(question, schema)` → calls the LLM → returns SQL.
11. Add validation: reject anything that isn't a `SELECT`, enforce a row `LIMIT`, run in a read-only DuckDB connection.
12. Add a retry loop: if execution throws an error, feed the error back to the LLM and ask it to fix the query (max 2-3 retries).

### Phase 3 — Chart + Summary Tools
13. Write `tools_chart.py`: given a result dataframe, ask the LLM "does this need a chart, and what type?" then generate it with matplotlib/plotly, return as base64 PNG.
14. Write `tools_summary.py`: feed the result rows back to the LLM, ask for a 2-3 sentence business insight.

### Phase 4 — Agent Orchestration
15. Wire everything into a LangGraph graph (or a simple Python loop) with nodes: `plan → run_sql → maybe_chart → summarize → done`.
16. Test end-to-end with a few sample questions against your demo dataset.

### Phase 5 — Backend API
17. Build `main.py` with:
    - `POST /upload` — accepts CSV/XLSX, calls ingestion, returns a `dataset_id`
    - `POST /ask` — takes `{dataset_id, question}`, runs the agent, returns `{sql, chart_base64, summary, trace}`
    - `GET /stats` — returns aggregated metrics from the logging DB
18. Add request/response validation with Pydantic models.

### Phase 6 — Frontend
19. Build a Streamlit app with: a file uploader, a chat-style question box, rendered SQL (in a code block), the chart, and the summary.
20. Add a second tab/page showing the observability metrics (success rate, avg latency, recent failures).

### Phase 7 — Logging & Observability
21. On every `/ask` call, log: timestamp, question, generated SQL, execution time, retry count, success/failure, token usage (if available from the LLM response).
22. Surface this in the `/stats` endpoint and the Streamlit metrics tab.

### Phase 8 — Testing
23. Write a handful of `pytest` tests: SQL guardrail rejects a `DROP TABLE`, ingestion correctly loads a multi-sheet Excel file, schema retrieval returns expected columns.

### Phase 9 — Containerize & Deploy
24. Write a `Dockerfile` (and `docker-compose.yml` if running backend + frontend as two services).
25. Deploy to Render/Railway/HuggingFace Spaces free tier. Get a public URL.

### Phase 10 — Documentation
26. Write the README: problem statement, architecture diagram, example questions + screenshots, known limitations, what you'd add for production (auth, rate limiting, caching, bigger models).
27. Push to GitHub, pin it on your profile, add the live link + repo link to your resume.

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