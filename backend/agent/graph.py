"""
LangGraph Orchestrator with MemorySaver-based conversational memory.
Phase 3: session_id, conversation history context, join hints, and follow-up suggestions.
"""
from typing import TypedDict, List, Optional, Dict, Any
import uuid
import time
import pandas as pd
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from backend.ingestion import get_schema, get_compact_schema, get_dataset_connection
from backend.agent.tools_planner import generate_analysis_plan
from backend.agent.tools_sql import generate_and_run_sql
from backend.agent.tools_chart import generate_chart
from backend.agent.tools_summary import generate_summary
from backend.agent.tools_followup import generate_followup_suggestions
from backend.agent.tools_relations import build_join_hints
from backend.agent.tools_analytics import (
    detect_analysis_intent,
    run_correlation_analysis,
    detect_outliers,
    run_time_series_forecast,
)
from backend.agent.tools_critic import verify_analysis_output
from backend.agent.semantic_layer import build_semantic_guidance_prompt, detect_matched_metrics
from backend.logging_db import log_run


class AgentState(TypedDict):
    dataset_id: str
    session_id: str
    question: str
    schema_str: str
    join_hints: Optional[str]
    conversation_context: str       # Injected prior Q&A turns for follow-up awareness
    plan: Optional[dict]
    analysis_type: Optional[str]    # 'sql', 'correlation', 'outliers', 'forecast'
    analytics_result: Optional[dict]# Statistical or forecasting computation output
    sql: Optional[str]
    df_data: Optional[List[Dict[str, Any]]] # JSON-serializable list of dict records
    chart_base64: Optional[str]
    summary: Optional[str]
    critic_result: Optional[dict]   # Phase 5: Verification and factual grounding output
    follow_up_questions: List[str]
    trace: List[dict]
    retries: int
    success: bool
    error: Optional[str]
    start_time: float


def node_plan(state: AgentState) -> AgentState:
    conn = get_dataset_connection(state["dataset_id"])
    schema_str = get_compact_schema(conn)

    # Discover multi-table join relationships and enrich schema
    join_hints = build_join_hints(conn)
    enriched_schema = schema_str + join_hints

    # Discover Semantic Metric Layer rules matching the query
    matched_metrics = detect_matched_metrics(state["question"])
    semantic_guidance = build_semantic_guidance_prompt(state["question"], enriched_schema)
    if semantic_guidance:
        enriched_schema = f"{enriched_schema}\n{semantic_guidance}"

    # Prepend conversation context for follow-up awareness
    context = state.get("conversation_context", "")
    if context:
        enriched_schema = f"Previous conversation context:\n{context}\n\n{enriched_schema}"

    plan = generate_analysis_plan(state["question"], enriched_schema)
    analysis_type = detect_analysis_intent(state["question"], plan)

    trace = list(state.get("trace", []))
    join_note = f" | {len(join_hints.splitlines())} join hints detected" if join_hints.strip() else ""
    route_badge = f" [Intent: {analysis_type.upper()}]" if analysis_type != "sql" else ""
    metric_note = f" | Semantic Metrics: {', '.join(m['name'] for m in matched_metrics)}" if matched_metrics else ""
    trace.append({
        "node": "Planner",
        "detail": (
            f"Generated Analysis Plan: Intent '{plan.get('intent', '')}'{route_badge} "
            f"with {len(plan.get('steps', []))} steps{join_note}{metric_note}"
        )
    })

    return {
        **state,
        "schema_str": enriched_schema,
        "join_hints": join_hints if join_hints.strip() else None,
        "plan": plan,
        "analysis_type": analysis_type,
        "trace": trace,
    }


def node_sql(state: AgentState) -> AgentState:
    conn = get_dataset_connection(state["dataset_id"])

    sql, df, retries, error = generate_and_run_sql(
        question=state["question"],
        schema_str=state["schema_str"],
        conn=conn,
        plan=state.get("plan"),
    )

    df_data = df.to_dict(orient="records") if df is not None else None

    trace = list(state.get("trace", []))
    if error:
        trace.append({
            "node": "SQL_Tool",
            "detail": f"Failed SQL generation after {retries} retries: {error}"
        })
        return {
            **state,
            "sql": sql,
            "df_data": df_data,
            "retries": retries,
            "success": False,
            "error": error,
            "trace": trace,
        }

    trace.append({
        "node": "SQL_Tool",
        "detail": f"Successfully generated and executed SQL ({len(df) if df is not None else 0} rows returned)"
    })
    return {
        **state,
        "sql": sql,
        "df_data": df_data,
        "retries": retries,
        "success": True,
        "error": None,
        "trace": trace,
    }


def node_analytics(state: AgentState) -> AgentState:
    """
    Analytics Routing Node (Phase 4): Executes correlation, outlier detection,
    or forecasting when analytical intent is detected.
    """
    trace = list(state.get("trace", []))
    df_data = state.get("df_data")

    if not state.get("success") or not df_data:
        return {**state, "analytics_result": None, "trace": trace}

    analysis_type = state.get("analysis_type") or detect_analysis_intent(state["question"], state.get("plan"))
    df = pd.DataFrame(df_data)
    analytics_result = None

    try:
        if analysis_type == "correlation":
            analytics_result = run_correlation_analysis(df)
            cols_cnt = len(analytics_result.get("columns", []))
            trace.append({
                "node": "Analytics_Tool",
                "detail": f"Calculated Pearson/Spearman correlation matrix across {cols_cnt} dimensions"
            })
        elif analysis_type == "outliers":
            analytics_result = detect_outliers(df)
            cnt = analytics_result.get("outlier_count", 0)
            trace.append({
                "node": "Analytics_Tool",
                "detail": f"Detected {cnt} outlier records using IQR/Z-score method"
            })
        elif analysis_type == "forecast":
            analytics_result = run_time_series_forecast(df, horizon=5)
            if "error" not in analytics_result:
                mae = analytics_result.get("metrics", {}).get("mae", 0.0)
                trace.append({
                    "node": "Analytics_Tool",
                    "detail": f"Generated 5-period forecast projection (Model MAE: {mae})"
                })
            else:
                trace.append({
                    "node": "Analytics_Tool",
                    "detail": f"Forecast notice: {analytics_result.get('error')}"
                })
    except Exception as err:
        trace.append({
            "node": "Analytics_Tool",
            "detail": f"Analytics engine note: {err}"
        })

    return {
        **state,
        "analysis_type": analysis_type,
        "analytics_result": analytics_result,
        "trace": trace,
    }


def node_chart(state: AgentState) -> AgentState:
    trace = list(state.get("trace", []))
    df_data = state.get("df_data")

    if not state["success"] or not df_data:
        trace.append({"node": "Chart_Tool", "detail": "Skipped chart generation (no data)"})
        return {**state, "chart_base64": None, "trace": trace}

    df = pd.DataFrame(df_data)
    chart_base64 = generate_chart(
        state["question"],
        df,
        analysis_type=state.get("analysis_type"),
        analytics_result=state.get("analytics_result")
    )

    trace.append({
        "node": "Chart_Tool",
        "detail": "Generated visualization chart" if chart_base64 else "No chart required for this result"
    })
    return {**state, "chart_base64": chart_base64, "trace": trace}


def node_summarize(state: AgentState) -> AgentState:
    trace = list(state.get("trace", []))

    if not state["success"]:
        summary = f"Unable to answer query due to error: {state['error']}"
        trace.append({"node": "Summary_Tool", "detail": "Generated error summary"})
    else:
        df_data = state.get("df_data")
        df = pd.DataFrame(df_data) if df_data else pd.DataFrame()
        summary = generate_summary(
            state["question"],
            state["sql"],
            df,
            analysis_type=state.get("analysis_type"),
            analytics_result=state.get("analytics_result")
        )
        trace.append({"node": "Summary_Tool", "detail": "Generated executive business summary"})

    return {**state, "summary": summary, "trace": trace}


def node_critic(state: AgentState) -> AgentState:
    """
    Critic Verification Node (Phase 5.1):
    Enforces numeric grounding, detects hallucinations, and executes auto-correction.
    """
    trace = list(state.get("trace", []))
    if not state.get("success") or not state.get("summary"):
        return {**state, "critic_result": None, "trace": trace}

    df_data = state.get("df_data")
    df = pd.DataFrame(df_data) if df_data else None

    critic_res = verify_analysis_output(
        question=state["question"],
        sql=state.get("sql"),
        df=df,
        chart_base64=state.get("chart_base64"),
        summary=state.get("summary", ""),
        analytics_result=state.get("analytics_result")
    )

    summary = state.get("summary", "")
    if critic_res.get("hallucination_detected") and critic_res.get("corrected_summary"):
        summary = critic_res["corrected_summary"]
        trace.append({
            "node": "Critic_Tool",
            "detail": f"Discrepancy detected: {critic_res['critique']}. Auto-corrected executive summary."
        })
    else:
        trace.append({
            "node": "Critic_Tool",
            "detail": f"Verification passed (Score: {critic_res['score']}, Hallucinations: 0): {critic_res['critique']}"
        })

    return {
        **state,
        "summary": summary,
        "critic_result": critic_res,
        "trace": trace,
    }


def node_followup(state: AgentState) -> AgentState:
    """
    Generates 3 follow-up question suggestions after a successful analysis.
    Skipped on failure to keep the error path clean.
    """
    trace = list(state.get("trace", []))

    if not state.get("success") or not state.get("sql"):
        return {**state, "follow_up_questions": [], "trace": trace}

    suggestions = generate_followup_suggestions(
        question=state["question"],
        sql=state.get("sql", ""),
        summary=state.get("summary", ""),
    )

    trace.append({
        "node": "FollowUp_Tool",
        "detail": f"Generated {len(suggestions)} follow-up question suggestions"
    })
    return {**state, "follow_up_questions": suggestions, "trace": trace}


def should_continue_after_sql(state: AgentState) -> str:
    return "chart" if state["success"] else "summarize"


def build_agent_graph(memory: MemorySaver):
    workflow = StateGraph(AgentState)

    workflow.add_node("planner_node", node_plan)
    workflow.add_node("sql_node", node_sql)
    workflow.add_node("analytics_node", node_analytics)
    workflow.add_node("chart", node_chart)
    workflow.add_node("summarize", node_summarize)
    workflow.add_node("critic", node_critic)
    workflow.add_node("followup", node_followup)

    workflow.set_entry_point("planner_node")

    workflow.add_edge("planner_node", "sql_node")
    workflow.add_edge("sql_node", "analytics_node")
    workflow.add_conditional_edges("analytics_node", should_continue_after_sql, {
        "chart": "chart",
        "summarize": "summarize",
    })
    workflow.add_edge("chart", "summarize")
    workflow.add_edge("summarize", "critic")
    workflow.add_edge("critic", "followup")
    workflow.add_edge("followup", END)

    return workflow.compile(checkpointer=memory)


# Singleton MemorySaver — persists in-process memory across all requests
_memory = MemorySaver()
agent_app = build_agent_graph(_memory)


# In-memory progress registry: request_id -> progress info (polled by /progress/{id})
PROGRESS_STAGES = [
    ("planner_node", "Planning analysis"),
    ("sql_node", "Generating & running SQL"),
    ("analytics_node", "Running analytics"),
    ("chart", "Building visualization"),
    ("summarize", "Writing summary"),
    ("critic", "Verifying answer"),
    ("followup", "Suggesting follow-ups"),
]
_progress: dict = {}


def get_progress(request_id: str) -> dict:
    return _progress.get(request_id, {"percent": 0, "stage": "Starting…", "done": False})


def _set_progress(request_id, completed_node=None, done=False):
    if not request_id:
        return
    names = [n for n, _ in PROGRESS_STAGES]
    if done:
        _progress[request_id] = {"percent": 100, "stage": "Done", "done": True}
        return
    idx = names.index(completed_node) + 1 if completed_node in names else 0
    # chart is skipped on failure; jumping ahead is fine
    stage = PROGRESS_STAGES[idx][1] if idx < len(PROGRESS_STAGES) else "Finalizing"
    _progress[request_id] = {
        "percent": int(idx / len(PROGRESS_STAGES) * 100),
        "stage": stage,
        "done": False,
    }
    # keep registry small
    if len(_progress) > 200:
        for k in list(_progress)[:100]:
            _progress.pop(k, None)


def run_agent(dataset_id: str, question: str, session_id: str = None,
              conversation_context: str = "", request_id: str = None) -> dict:
    """
    Runs the full LangGraph agent with optional session_id for conversational memory.
    conversation_context: serialized prior Q&A from the frontend session.
    """
    if not session_id:
        session_id = str(uuid.uuid4())[:8]

    start_time = time.time()

    initial_state: AgentState = {
        "dataset_id": dataset_id,
        "session_id": session_id,
        "question": question,
        "schema_str": "",
        "join_hints": None,
        "conversation_context": conversation_context,
        "plan": None,
        "analysis_type": None,
        "analytics_result": None,
        "sql": None,
        "df_data": None,
        "chart_base64": None,
        "summary": "",
        "critic_result": None,
        "follow_up_questions": [],
        "trace": [],
        "retries": 0,
        "success": False,
        "error": None,
        "start_time": start_time,
    }

    # MemorySaver uses thread_id to persist/restore per session
    config = {"configurable": {"thread_id": f"{dataset_id}:{session_id}"}}
    _set_progress(request_id)
    try:
        for update in agent_app.stream(initial_state, config=config, stream_mode="updates"):
            for node_name in update:
                _set_progress(request_id, completed_node=node_name)
        final_state = agent_app.get_state(config).values
    finally:
        _set_progress(request_id, done=True)

    latency = round(time.time() - start_time, 2)

    log_run(
        dataset_id=dataset_id,
        question=question,
        sql=final_state.get("sql") or "",
        latency=latency,
        retries=final_state.get("retries", 0),
        success=final_state.get("success", False),
        error=final_state.get("error"),
    )

    return {
        "question": question,
        "session_id": session_id,
        "plan": final_state.get("plan"),
        "analysis_type": final_state.get("analysis_type"),
        "analytics_result": final_state.get("analytics_result"),
        "sql": final_state.get("sql"),
        "chart_base64": final_state.get("chart_base64"),
        "summary": final_state.get("summary", ""),
        "critic_result": final_state.get("critic_result"),
        "trace": final_state.get("trace", []),
        "retries": final_state.get("retries", 0),
        "success": final_state.get("success", False),
        "error": final_state.get("error"),
        "follow_up_questions": final_state.get("follow_up_questions", []),
        "join_hints": final_state.get("join_hints"),
    }


def run_agent_stream(dataset_id: str, question: str, session_id: str = None,
                     conversation_context: str = "", request_id: str = None):
    """
    Generator yielding real-time execution steps and final result payload for SSE streaming.
    """
    if not session_id:
        session_id = str(uuid.uuid4())[:8]

    start_time = time.time()

    initial_state: AgentState = {
        "dataset_id": dataset_id,
        "session_id": session_id,
        "question": question,
        "schema_str": "",
        "join_hints": None,
        "conversation_context": conversation_context,
        "plan": None,
        "analysis_type": None,
        "analytics_result": None,
        "sql": None,
        "df_data": None,
        "chart_base64": None,
        "summary": "",
        "critic_result": None,
        "follow_up_questions": [],
        "trace": [],
        "retries": 0,
        "success": False,
        "error": None,
        "start_time": start_time,
    }

    config = {"configurable": {"thread_id": f"{dataset_id}:{session_id}"}}
    yield {
        "event": "start",
        "stage": "Starting",
        "percent": 5,
        "session_id": session_id,
        "message": "Initializing autonomous agent pipeline..."
    }

    stage_dict = dict(PROGRESS_STAGES)
    stage_names = [n for n, _ in PROGRESS_STAGES]

    try:
        for update in agent_app.stream(initial_state, config=config, stream_mode="updates"):
            for node_name, node_state in update.items():
                trace = node_state.get("trace", [])
                latest_detail = trace[-1]["detail"] if trace else f"Finished {node_name}"
                idx = stage_names.index(node_name) + 1 if node_name in stage_names else 1
                percent = min(int((idx / len(PROGRESS_STAGES)) * 100), 95)
                stage_label = stage_dict.get(node_name, node_name.replace('_', ' ').capitalize())

                yield {
                    "event": "step",
                    "node": stage_label,
                    "stage": stage_label,
                    "percent": percent,
                    "detail": latest_detail,
                    "plan": node_state.get("plan") if "planner" in node_name else None,
                    "sql": node_state.get("sql") if "sql" in node_name else None,
                }
        final_state = agent_app.get_state(config).values
    except Exception as e:
        yield {
            "event": "error",
            "error": str(e),
            "message": f"Execution encountered an error: {str(e)}"
        }
        return

    latency = round(time.time() - start_time, 2)

    log_run(
        dataset_id=dataset_id,
        question=question,
        sql=final_state.get("sql") or "",
        latency=latency,
        retries=final_state.get("retries", 0),
        success=final_state.get("success", False),
        error=final_state.get("error"),
    )

    result_payload = {
        "question": question,
        "session_id": session_id,
        "plan": final_state.get("plan"),
        "analysis_type": final_state.get("analysis_type"),
        "analytics_result": final_state.get("analytics_result"),
        "sql": final_state.get("sql"),
        "chart_base64": final_state.get("chart_base64"),
        "summary": final_state.get("summary", ""),
        "critic_result": final_state.get("critic_result"),
        "trace": final_state.get("trace", []),
        "retries": final_state.get("retries", 0),
        "success": final_state.get("success", False),
        "error": final_state.get("error"),
        "follow_up_questions": final_state.get("follow_up_questions", []),
        "join_hints": final_state.get("join_hints"),
    }

    yield {
        "event": "result",
        "percent": 100,
        "stage": "Complete",
        "data": result_payload
    }

