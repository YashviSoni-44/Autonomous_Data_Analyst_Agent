# 🤖 Autonomous Data Analyst Agent

> **An enterprise-grade, multi-agent AI system that transforms plain-English business questions over tabular datasets (CSV, Excel, DuckDB) into validated SQL execution, interactive visualizations, predictive forecasting, statistical testing, and executive intelligence briefings — featuring factual critic verification, conversational memory, and zero-prompt autonomous dataset exploration.**

---

## 🌟 Key Capabilities & Features

### 1. Ingestion & Intelligent Data Profiling
- **Multi-Format Ingestion**: Ingests CSVs and multi-sheet Excel workbooks (`.xlsx`, `.xls`) directly into an embedded, high-performance DuckDB data engine.
- **Automated Data Profiling**: Extracts column statistics, null percentages, distinct cardinalities, datetime indicators, and candidate primary keys.
- **Data Quality Scoring (0–100)**: Computes dataset health and surfaces actionable data warnings (e.g. duplicate rows, missing values).

### 2. Multi-Agent Reasoning & Execution Graph (LangGraph)
- **Structured Analysis Planner**: Decomposes user intent into target metrics, dimensions, filters, and mathematical operations before executing SQL.
- **Guardrailed SQL Generation**: Generates safe, read-only `SELECT` queries with enforced execution limits; blocks destructive statements (`DROP`, `DELETE`, `UPDATE`, `ALTER`).
- **Self-Correction Retry Loop**: Automatically intercepts SQL errors and prompts the LLM to fix syntax errors with schema context.
- **Conversational Memory**: Checkpoints session state via LangGraph `MemorySaver` (`thread_id=f"{dataset_id}:{session_id}"`) so users can ask contextual follow-ups (*"Now break that down by region"*).
- **Multi-Table Join Inference**: Automatically discovers foreign-key relationships across tables and generates accurate multi-table `JOIN` queries.

### 3. Advanced Statistical & Predictive Analytics Engine
- **Correlation Testing**: Pearson and Spearman correlation matrices across all numerical features, ranked by strength and direction.
- **Outlier & Anomaly Detection**: Discovers anomalous records using Interquartile Range (IQR) bounds and Z-scores ($|z| > 3.0$), flagging severe transactions.
- **Time-Series Forecasting**: Implements Holt's Linear Exponential Smoothing to extrapolate future horizons ($h=5$) with 95% confidence intervals and MAE/RMSE accuracy scores.

### 4. Critic Verification & Hallucination Guardrails
- **Post-Execution Critic Loop (`node_critic`)**: Mathematically compares numbers, percentages, and aggregates in the executive summary against the raw SQL dataframe and analytical computations.
- **Autonomous Self-Correction**: Re-synthesizes summaries if ungrounded numerical claims or empty result discrepancies are detected.
- **Verification Badging**: Surfaces `🛡️ Critic Verified (100% Grounded)` or `⚠️ Critic Auto-Adjusted` badges directly in the UI.

### 5. Autonomous Zero-Prompt Dataset Investigation
- **Executive Intelligence Briefing (`POST /analyze/{dataset_id}`)**:
  - Automatically identifies key metrics and categorical drivers without requiring a user prompt.
  - Generates KPI summary cards, Pareto concentration breakdowns, and outlier anomaly warnings.
  - Automatically plots an overview visualization and generates recommended strategic follow-up queries.

### 6. Modern React Dashboard & Observability
- **Four-Tab Interface**:
  1. `💬 Agent Chat Studio`: Interactive conversational chat with collapsible plans, SQL blocks, visualizations, Critic badges, and follow-up chips.
  2. `⚡ Autonomous Deep Dive`: Zero-prompt executive report with one-click deep-dive questions.
  3. `🔍 Data Quality & Profiling`: Column distributions, data types, and quality scoring.
  4. `📊 Observability & Metrics`: Latency tracking, success rates, retry counts, and execution traces stored in SQLite.

---

## 🏗️ System Architecture

```
                 ┌────────────────────────────────────────────────────────┐
                 │                  React Frontend (Vite)                 │
                 │  • Chat Studio  • Autonomous Deep Dive  • Profiling   │
                 │              • Observability & Trace View             │
                 └───────────────────────────┬────────────────────────────┘
                                             │ HTTP / REST
                                             ▼
                 ┌────────────────────────────────────────────────────────┐
                 │                  FastAPI Backend Server                │
                 │  POST /upload   POST /ask   GET /profile   POST /analyze│
                 └──────────────┬──────────────────────────┬──────────────┘
                                │                          │
                                ▼                          ▼
                 ┌───────────────────────────┐  ┌─────────────────────────┐
                 │    DuckDB Data Engine     │  │   SQLite Run Logger     │
                 │ (In-memory SQL Analytics) │  │  (Latency, Run Traces)  │
                 └──────────────┬────────────┘  └─────────────────────────┘
                                │
                                ▼
       ┌─────────────────────────────────────────────────────────────────┐
       │             LangGraph Multi-Agent Orchestration Graph           │
       │                                                                 │
       │  ┌──────────────┐      ┌──────────────┐      ┌───────────────┐  │
       │  │ Planner Node │ ───► │   SQL Node   │ ───► │Analytics Node │  │
       │  └──────────────┘      └──────────────┘      └───────┬───────┘  │
       │                                                      │          │
       │                                                      ▼          │
       │  ┌──────────────┐      ┌──────────────┐      ┌───────────────┐  │
       │  │Follow-Up Node│ ◄─── │ Critic Node  │ ◄─── │Summarize Node │  │
       │  └──────┬───────┘      └──────────────┘      └───────▲───────┘  │
       │         │                                            │          │
       │         ▼                                    ┌───────┴───────┐  │
       │        END                                   │  Chart Node   │  │
       │                                              └───────────────┘  │
       └────────────────────────────────┬────────────────────────────────┘
                                        │
                 ┌──────────────────────┴──────────────────────┐
                 ▼                                             ▼
   ┌───────────────────────────┐                 ┌───────────────────────────┐
   │    Google Gemini API      │                 │   Local Ollama (Llama 3)  │
   │   (gemini-2.0-flash)      │                 │   (100% Offline / Free)   │
   └───────────────────────────┘                 └───────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technologies |
|---|---|
| **Data Engine** | DuckDB, Pandas, NumPy, OpenPyXL |
| **Agent Orchestration** | LangGraph, LangGraph MemorySaver |
| **LLM Support** | Google Gemini API (`gemini-2.0-flash`) & Local Ollama (`llama3:latest`) |
| **Backend API** | FastAPI, Uvicorn, Pydantic |
| **Frontend UI** | React 18, Vite 5, Lucide React, Custom CSS Design System |
| **Data Visualization** | Matplotlib (Agg headless backend) |
| **Observability** | SQLite database (`agent_runs.db`) |
| **Test Suite** | Pytest (41 automated unit & integration tests) |
| **Deployment** | Docker, Docker Compose |

---

## 🔑 LLM Provider Setup

Configure your provider in `.env`:

### Option A: Google Gemini API (Recommended for Cloud)
Get a free API key at [Google AI Studio](https://aistudio.google.com/app/apikey):
```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=AIzaSy...
```

### Option B: Local Ollama (100% Free & Offline)
Ensure Ollama is running (`ollama run llama3:latest`):
```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3:latest
```

---

## 🚀 Step-by-Step Execution Guide

### 1. Environment Setup

```bash
# 1. Clone repository
git clone https://github.com/your-username/Autonomous_Data_Analyst_Agent.git
cd Autonomous_Data_Analyst_Agent

# 2. Create Python virtual environment (Python 3.11+)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install backend dependencies
pip install -r requirements.txt

# 4. Install frontend dependencies
cd frontend && npm install && cd ..

# 5. Configure environment variables
cp .env.example .env
# Edit .env with your Gemini API key or Ollama configuration
```

### 2. Starting the Application

#### Terminal 1 — FastAPI Backend:
```bash
source venv/bin/activate
# Standard port (or use --port 8004 if port 8000 is in use)
uvicorn backend.main:app --reload --port 8004
```
Backend will be live at `http://localhost:8004` (or `8000`) with interactive API docs at `/docs`.
> **Note**: Frontend is configured to connect to `http://localhost:8004` by default (configurable via `VITE_BACKEND_URL` in `frontend/.env`).

#### Terminal 2 — React Frontend:
```bash
cd frontend
npm run dev
```
Open your browser at `http://localhost:5173`.

---

### 3. Execution Workflows & Examples

1. **Load Data**:
   - In the sidebar, select `"Use sample sales dataset"` or upload any CSV / Excel file.
   - Click `"🚀 Load Dataset"`. The system profiles data quality and infers candidate primary keys.
2. **Autonomous Deep Dive**:
   - Click `"⚡ Autonomous Deep Dive"` in the sidebar or top navigation.
   - Review executive briefings, KPI cards, anomaly scans, and correlation matrices.
   - Click any recommended inquiry to jump directly into the Chat Studio.
3. **Conversational Analysis in Chat Studio**:
   - Ask: `"What is the total sales amount by category?"` ➔ SQL query, bar chart, and verified summary generated.
   - Contextual follow-up: `"Now show me only the North region"` ➔ Preserves conversational context across turns.
   - Statistical testing: `"What is the correlation between sales_amount and quantity?"` ➔ Pearson/Spearman matrix and heatmap.
   - Anomaly detection: `"Detect outliers in sales_amount"` ➔ IQR outlier bounds and highlighted scatter plot.
   - Time-series forecasting: `"Forecast sales for the next 6 months"` ➔ Holt's exponential smoothing with 95% prediction intervals.
4. **Inspect Critic & Observability**:
   - Expand `"🎯 Agent Strategy & Decomposed Plan"` and `"🕵️ Agent Execution Trace"`.
   - Verify that the response displays `"🛡️ Critic Verified (100% Grounded)"`.
   - Switch to the `"📊 Observability & Metrics"` tab to review system latency, run logs, and success rates.

---

## 🐳 Running with Docker Compose

Run both the frontend and backend in unified containers:

```bash
docker-compose up --build
```
- Frontend UI: `http://localhost:5173`
- Backend API: `http://localhost:8000`

---

## 🧪 Automated Testing Suite

Run the complete test suite (41 unit and integration tests):

```bash
# Run all tests
./venv/bin/python -m pytest -v

# Run specific domain test suites
./venv/bin/python -m pytest tests/test_critic_and_autonomous.py -v
./venv/bin/python -m pytest tests/test_analytics.py -v
./venv/bin/python -m pytest tests/test_memory_and_relations.py -v
./venv/bin/python -m pytest tests/test_profiling.py -v
./venv/bin/python -m pytest tests/test_sql_guardrails.py -v
```

---

## 📄 License
MIT License.
