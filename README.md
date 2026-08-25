# 🤖 Autonomous Data Analyst Agent

> **An LLM-powered agent that answers natural-language business questions over any tabular data source (CSV, Excel, or DuckDB) by generating and safely executing SQL, visualizing results, and summarizing insights — with guardrails, retries, dual LLM support (Local Ollama & Google Gemini), and an observability dashboard.**

---

## 🌟 Key Features

- **Multi-Format Ingestion**: Supports CSV, multi-sheet Excel workbooks (`.xlsx`, `.xls`), and DuckDB integration.
- **Dual LLM Architecture**: Supports **Local Ollama (`llama3:latest`)** for 100% free offline usage and **Google Gemini API (`gemini-2.0-flash`)** with zero-latency failover.
- **Safe SQL Generation with Guardrails**: Enforces read-only `SELECT` queries (blocks `DROP`, `DELETE`, `UPDATE`, `INSERT`, etc.) and enforces row limit bounds.
- **Self-Correction Retry Loop**: Automatically captures SQL execution errors and prompts the LLM to auto-correct syntax errors.
- **Automated Visualization**: Uses LLM logic to generate clean Matplotlib charts rendered directly in the UI.
- **Executive Summarization**: Translates raw SQL result tables into 2-3 sentence executive business narratives.
- **LangGraph Agent Orchestration**: Modular graph nodes (`planner` ➔ `sql_node` ➔ `chart` ➔ `summarize`).
- **Real-Time Observability**: Built-in SQLite logging and Streamlit observability metrics tab tracking total runs, success rates, latency, retries, and failure logs.

---

## 🏗️ System Architecture

```
                                ┌─────────────────────────┐
                                │   Streamlit Frontend    │
                                │  (Chat UI + Upload +    │
                                │   Metrics Dashboard)    │
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
                                │    Ingestion Engine     │
                                │ (CSV/Excel ➔ DuckDB)    │
                                └───────────┬─────────────┘
                                            │
                                            ▼
                                ┌─────────────────────────┐
                                │  LangGraph Orchestrator │
                                │ Planner ➔ SQL ➔ Chart ➔ │
                                │        Summarize        │
                                └───────────┬─────────────┘
                                            │
                     ┌──────────────────────┴──────────────────────┐
                     ▼                                             ▼
       ┌───────────────────────────┐                 ┌───────────────────────────┐
       │   Local Ollama (Llama 3)  │                 │    Google Gemini API      │
       │   (Primary / Offline)     │                 │   (gemini-2.0-flash)      │
       └───────────────────────────┘                 └───────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Data Engine** | DuckDB, Pandas, openpyxl |
| **LLM Support** | Local Ollama (`llama3:latest`) & Google Gemini API (`gemini-2.0-flash`) |
| **Orchestration** | LangGraph |
| **Backend API** | FastAPI, Uvicorn, Pydantic |
| **Frontend UI** | Streamlit |
| **Visualization** | Matplotlib |
| **Observability** | SQLite database (`agent_runs.db`) |
| **Testing & CI** | Pytest |
| **Containerization**| Docker, Docker Compose |

---

## 🔑 LLM Provider Configuration

The agent supports two LLM providers, configured in `.env`:

### Option A: Local Ollama (100% Free & Offline - Recommended)
Set `LLM_PROVIDER=ollama` in `.env`:
```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3:latest
```

### Option B: Google Gemini API (Cloud Fast)
Set `LLM_PROVIDER=gemini` and add your free Gemini API Key from [Google AI Studio](https://aistudio.google.com/app/apikey):
```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=AIzaSy...
```

---

## 🚀 Quick Start Guide

### 1. Clone & Setup Environment
```bash
git clone https://github.com/your-username/Autonomous_Data_Analyst_Agent.git
cd Autonomous_Data_Analyst_Agent

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### 3. Run Backend & Frontend

**Terminal 1 (FastAPI Backend):**
```bash
PYTHONPATH=. uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 (Streamlit Frontend):**
```bash
streamlit run frontend/app.py
```

Open your browser at `http://localhost:8501`.

---

## 🐳 Running with Docker

Build and run the entire application using Docker Compose:

```bash
docker-compose up --build
```
Access the Streamlit application at `http://localhost:8501`.

*Note: When running with Docker Compose, the container automatically maps `host.docker.internal` to talk directly to your host machine's local Ollama server.*

---

## 🧪 Running Unit Tests

```bash
PYTHONPATH=. pytest tests/
```

---

## 📄 License
MIT License.
