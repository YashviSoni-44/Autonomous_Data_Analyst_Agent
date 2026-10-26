# 🎨 Autonomous Data Analyst Agent — Frontend

Modern, dark-mode React application powered by **Vite 5**, **React 18**, and **Lucide React**.

---

## 🌟 Application Views & Architecture

The frontend is structured into four specialized tabs:

1. **💬 Agent Chat Studio (`AgentChatStudio.jsx`)**:
   - Conversational chat interface connected to the LangGraph backend.
   - Decomposed reasoning plans (`AnalysisPlan`) with collapsible step views.
   - Syntax-highlighted SQL code blocks with one-click copy.
   - Matplotlib visualization preview with interactive full-screen zoom modal (`ChartModal.jsx`).
   - Dynamic **Critic Verification Badges** (`🛡️ Critic Verified: 100% Grounded` / `⚠️ Critic Auto-Adjusted`).
   - Specialized diagnostic cards for **predictive forecasts**, **correlation matrices**, and **outlier detection**.
   - Dynamic follow-up question chips.

2. **⚡ Autonomous Deep Dive (`AutonomousReportView.jsx`)**:
   - Zero-prompt executive intelligence reports triggered on any uploaded dataset (`/analyze/{dataset_id}`).
   - Core KPI metrics grid with primary anchors.
   - Dominant segment Pareto breakdown and risk alerts.
   - Anomaly severity indicators and correlation highlights.
   - Interactive overview chart.
   - Clickable follow-up inquiries that auto-navigate into the Chat Studio.

3. **🔍 Data Quality & Profiling (`DataProfiling.jsx`)**:
   - Automatic dataset health score (0–100) and warning cards.
   - Column-by-column breakdown: types, missing value percentages, distinct cardinalities, and candidate primary keys.

4. **📊 Observability & Metrics (`ObservabilityDashboard.jsx`)**:
   - Real-time performance metrics (Total Runs, Success Rate, Average Latency, Average Retries).
   - Recent execution logs and failure diagnosis table.

---

## 🚀 Running Locally

```bash
# 1. Install dependencies
npm install

# 2. Start Vite development server
npm run dev
```

App runs at `http://localhost:5173`. Proxies backend requests to `http://localhost:8000`.

---

## 🏗️ Production Build

```bash
# Build production bundle
npm run build

# Preview production build
npm run preview
```
Output bundles are generated in `dist/` and automatically served by FastAPI when running in production mode.
