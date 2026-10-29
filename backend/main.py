"""
FastAPI application backend for the Autonomous Data Analyst Agent.
"""
import os
import json
import shutil
import uuid as _uuid
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from backend.models import UploadResponse, AskRequest, AskResponse, StatsResponse, ProfileResponse, AutonomousReport
from backend.ingestion import load_file_into_duckdb
from backend.agent.graph import run_agent, run_agent_stream, get_progress
from backend.agent.tools_autonomous import run_autonomous_dataset_investigation
from backend.agent.semantic_layer import load_metrics, save_custom_metric
from backend.logging_db import get_stats
from backend.profiling import profile_dataset

load_dotenv()

app = FastAPI(
    title="Autonomous Data Analyst Agent API",
    description="LLM agent that converts business questions to safe SQL, charts, and business summaries over CSV/Excel datasets.",
    version="1.0.0"
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Autonomous Data Analyst Agent Backend is active."}

@app.post("/upload", response_model=UploadResponse)
async def upload_dataset(file: UploadFile = File(...)):
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    
    if ext not in [".csv", ".xlsx", ".xls"]:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Please upload a .csv or .xlsx / .xls file."
        )

    # Prefix with a short UUID to avoid PermissionError when a same-named
    # file already exists (e.g. locked by a prior DuckDB connection).
    unique_prefix = str(_uuid.uuid4())[:8]
    safe_filename = f"{unique_prefix}_{filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        dataset_id, tables = load_file_into_duckdb(file_path)
        return UploadResponse(
            dataset_id=dataset_id,
            tables=tables,
            message=f"Successfully loaded {filename} into DuckDB tables: {', '.join(tables)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest dataset: {str(e)}")

@app.get("/profile/{dataset_id}", response_model=ProfileResponse)
def get_dataset_profile(dataset_id: str):
    try:
        return profile_dataset(dataset_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to profile dataset: {str(e)}")

@app.get("/progress/{request_id}")
def ask_progress(request_id: str):
    return get_progress(request_id)

@app.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        result = run_agent(
            dataset_id=request.dataset_id,
            question=request.question,
            session_id=request.session_id,
            conversation_context=getattr(request, "conversation_context", ""),
            request_id=request.request_id,
        )
        return AskResponse(
            question=result["question"],
            session_id=result.get("session_id"),
            plan=result.get("plan"),
            sql=result.get("sql"),
            chart_base64=result.get("chart_base64"),
            summary=result.get("summary", ""),
            trace=result.get("trace", []),
            retries=result.get("retries", 0),
            success=result.get("success", False),
            error=result.get("error"),
            follow_up_questions=result.get("follow_up_questions", []),
            join_hints=result.get("join_hints"),
            analysis_type=result.get("analysis_type"),
            analytics_result=result.get("analytics_result"),
            critic_result=result.get("critic_result"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")

@app.post("/ask/stream")
def ask_question_stream(request: AskRequest):
    """
    Server-Sent Events (SSE) streaming endpoint for real-time thought step visualization.
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    def event_stream():
        try:
            for item in run_agent_stream(
                dataset_id=request.dataset_id,
                question=request.question,
                session_id=request.session_id,
                conversation_context=getattr(request, "conversation_context", ""),
                request_id=request.request_id,
            ):
                yield f"data: {json.dumps(item)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'event': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/analyze/{dataset_id}", response_model=AutonomousReport)
def analyze_dataset_autonomous(dataset_id: str, force: bool = False):
    """
    Zero-prompt autonomous dataset analysis (Phase 5.2).
    Discovers KPIs, correlations, outliers, distributions, and returns an executive report.
    Caches the report per dataset_id. Set force=true to bypass cache.
    """
    try:
        return run_autonomous_dataset_investigation(dataset_id, force=force)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Autonomous dataset analysis failed: {str(e)}")

@app.get("/stats", response_model=StatsResponse)
def get_observability_stats():
    return get_stats()

@app.get("/metrics")
def get_semantic_metrics():
    """
    Returns the active dictionary of registered enterprise business metrics.
    """
    return load_metrics()

@app.post("/metrics")
def create_custom_metric(metric: dict):
    """
    Registers or updates a business metric in the Semantic Metric Layer.
    """
    m_id = metric.get("name", "").strip().lower().replace(" ", "_")
    if not m_id:
        raise HTTPException(status_code=400, detail="Metric must have a valid name.")
    ok = save_custom_metric(m_id, metric)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to save custom metric.")
    return {"status": "ok", "message": f"Metric '{metric.get('name')}' successfully registered."}

@app.get("/benchmark/latest")
def get_latest_benchmark():
    """
    Returns the latest benchmark scorecard and evaluation results.
    """
    bench_file = "./benchmark_results.json"
    if os.path.exists(bench_file):
        try:
            with open(bench_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read benchmark results: {e}")
    return {"status": "none", "message": "No benchmark run recorded yet."}

# Mount compiled static React frontend if dist directory exists
dist_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.exists(dist_dir):
    app.mount("/", StaticFiles(directory=dist_dir, html=True), name="static")

