"""
Pydantic models for FastAPI request/response validation.
"""
from pydantic import BaseModel
from typing import Optional


class UploadResponse(BaseModel):
    dataset_id: str
    tables: list[str]
    message: str


class ConversationTurn(BaseModel):
    question: str
    sql: Optional[str] = None
    summary: Optional[str] = None


class AskRequest(BaseModel):
    dataset_id: str
    question: str
    session_id: Optional[str] = None
    conversation_context: Optional[str] = ""
    request_id: Optional[str] = None


class TraceStep(BaseModel):
    node: str
    detail: str


class AnalysisPlan(BaseModel):
    intent: str
    metrics: list[str]
    dimensions: list[str]
    filters: list[str]
    time_range: Optional[str] = None
    operations: list[str]
    visualization_recommended: bool
    chart_type_suggestion: Optional[str] = None
    steps: list[str]


class AskResponse(BaseModel):
    question: str
    session_id: Optional[str] = None
    plan: Optional[dict] = None
    sql: Optional[str] = None
    chart_base64: Optional[str] = None
    summary: str
    trace: list[TraceStep]
    retries: int
    success: bool
    error: Optional[str] = None
    follow_up_questions: list[str] = []
    join_hints: Optional[str] = None
    analysis_type: Optional[str] = None
    analytics_result: Optional[dict] = None
    critic_result: Optional[dict] = None


class AutonomousReport(BaseModel):
    dataset_id: str
    table_name: str
    executive_summary: str
    kpi_metrics: list[dict]
    top_findings: list[str]
    anomalies_detected: list[dict]
    correlations: list[dict]
    chart_base64: Optional[str] = None
    recommended_actions: list[str]
    generated_at: str



class StatsResponse(BaseModel):
    total_runs: int
    successful_runs: int
    failed_runs: int
    success_rate: float
    avg_latency_seconds: float
    avg_retries: float
    recent_failures: list[dict]
    recent_runs: list[dict] = []


class ColumnProfile(BaseModel):
    name: str
    data_type: str
    null_count: int
    null_percentage: float
    distinct_count: int
    sample_values: list[str]
    is_candidate_pk: bool
    is_datetime: bool
    min_val: Optional[str] = None
    max_val: Optional[str] = None
    mean_val: Optional[float] = None


class TableProfile(BaseModel):
    table_name: str
    row_count: int
    column_count: int
    duplicate_rows: int
    columns: list[ColumnProfile]
    quality_score: float
    warnings: list[str]


class ProfileResponse(BaseModel):
    dataset_id: str
    overall_quality_score: float
    tables: list[TableProfile]
    total_rows: int
    total_columns: int
    warnings: list[str]

