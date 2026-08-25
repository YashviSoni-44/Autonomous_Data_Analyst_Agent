"""
FastAPI application backend for the Autonomous Data Analyst Agent.
"""
import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from backend.models import UploadResponse, AskRequest, AskResponse, StatsResponse, ProfileResponse
from backend.ingestion import load_file_into_duckdb
from backend.agent.graph import run_agent
from backend.logging_db import get_stats
from backend.profiling import profile_dataset

load_dotenv()

app = FastAPI(
    title="Autonomous Data Analyst Agent API",
    description="LLM agent that converts business questions to safe SQL, charts, and business summaries over CSV/Excel datasets.",
    version="1.0.0"
)

# Enable CORS for Streamlit frontend
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

    file_path = os.path.join(UPLOAD_DIR, filename)
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

@app.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        result = run_agent(dataset_id=request.dataset_id, question=request.question)
        return AskResponse(
            question=result["question"],
            plan=result.get("plan"),
            sql=result.get("sql"),
            chart_base64=result.get("chart_base64"),
            summary=result.get("summary", ""),
            trace=result.get("trace", []),
            retries=result.get("retries", 0),
            success=result.get("success", False),
            error=result.get("error")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {str(e)}")

@app.get("/stats", response_model=StatsResponse)
def get_observability_stats():
    return get_stats()

