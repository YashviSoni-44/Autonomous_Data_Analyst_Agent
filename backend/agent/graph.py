"""
LangGraph Orchestrator: Connects Planning, SQL Execution, Charting, and Summarization into an agentic workflow.
"""
from typing import TypedDict, List, Optional, Any
import time
import pandas as pd
from langgraph.graph import StateGraph, END

from backend.ingestion import get_schema, get_dataset_connection
from backend.agent.tools_planner import generate_analysis_plan
from backend.agent.tools_sql import generate_and_run_sql
from backend.agent.tools_chart import generate_chart
from backend.agent.tools_summary import generate_summary
from backend.logging_db import log_run

class AgentState(TypedDict):
    dataset_id: str
    question: str
    schema_str: str
    plan: Optional[dict]
    sql: Optional[str]
    df: Optional[pd.DataFrame]
    chart_base64: Optional[str]
    summary: Optional[str]
    trace: List[dict]
    retries: int
    success: bool
    error: Optional[str]
    start_time: float

def node_plan(state: AgentState) -> AgentState:
    conn = get_dataset_connection(state["dataset_id"])
    schema_str = get_schema(conn)
    
    # Generate structured AnalysisPlan
    plan = generate_analysis_plan(state["question"], schema_str)
    
    trace = list(state.get("trace", []))
    trace.append({
        "node": "Planner",
        "detail": f"Generated Analysis Strategy Plan: Intent '{plan.get('intent', '')}' with {len(plan.get('steps', []))} steps"
    })
    
    return {
        **state,
        "schema_str": schema_str,
        "plan": plan,
        "trace": trace
    }

def node_sql(state: AgentState) -> AgentState:
    conn = get_dataset_connection(state["dataset_id"])
    
    sql, df, retries, error = generate_and_run_sql(
        question=state["question"],
        schema_str=state["schema_str"],
        conn=conn,
        plan=state.get("plan")
    )
    
    trace = list(state.get("trace", []))
    if error:
        trace.append({
            "node": "SQL_Tool",
            "detail": f"Failed SQL generation after {retries} retries: {error}"
        })
        return {
            **state,
            "sql": sql,
            "df": df,
            "retries": retries,
            "success": False,
            "error": error,
            "trace": trace
        }
        
    trace.append({
        "node": "SQL_Tool",
        "detail": f"Successfully generated and executed SQL ({len(df)} rows returned)"
    })
    
    return {
        **state,
        "sql": sql,
        "df": df,
        "retries": retries,
        "success": True,
        "error": None,
        "trace": trace
    }

def node_chart(state: AgentState) -> AgentState:
    trace = list(state.get("trace", []))
    
    if not state["success"] or state["df"] is None or state["df"].empty:
        trace.append({"node": "Chart_Tool", "detail": "Skipped chart generation (no data)"})
        return {**state, "chart_base64": None, "trace": trace}
        
    chart_base64 = generate_chart(state["question"], state["df"])
    
    if chart_base64:
        trace.append({"node": "Chart_Tool", "detail": "Generated visualization chart"})
    else:
        trace.append({"node": "Chart_Tool", "detail": "Determined no chart was required"})
        
    return {
        **state,
        "chart_base64": chart_base64,
        "trace": trace
    }

def node_summarize(state: AgentState) -> AgentState:
    trace = list(state.get("trace", []))
    
    if not state["success"]:
        summary = f"Unable to answer query due to error: {state['error']}"
        trace.append({"node": "Summary_Tool", "detail": "Generated error summary"})
    else:
        summary = generate_summary(state["question"], state["sql"], state["df"])
        trace.append({"node": "Summary_Tool", "detail": "Generated executive business summary"})
        
    return {
        **state,
        "summary": summary,
        "trace": trace
    }

def should_continue_after_sql(state: AgentState) -> str:
    if not state["success"]:
        return "summarize"
    return "chart"

def build_agent_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("planner_node", node_plan)
    workflow.add_node("sql_node", node_sql)
    workflow.add_node("chart", node_chart)
    workflow.add_node("summarize", node_summarize)
    
    workflow.set_entry_point("planner_node")
    
    workflow.add_edge("planner_node", "sql_node")
    workflow.add_conditional_edges("sql_node", should_continue_after_sql, {
        "chart": "chart",
        "summarize": "summarize"
    })
    workflow.add_edge("chart", "summarize")
    workflow.add_edge("summarize", END)
    
    return workflow.compile()

# Instantiated workflow agent
agent_app = build_agent_graph()

def run_agent(dataset_id: str, question: str) -> dict:
    start_time = time.time()
    
    initial_state: AgentState = {
        "dataset_id": dataset_id,
        "question": question,
        "schema_str": "",
        "plan": None,
        "sql": None,
        "df": None,
        "chart_base64": None,
        "summary": "",
        "trace": [],
        "retries": 0,
        "success": False,
        "error": None,
        "start_time": start_time
    }
    
    final_state = agent_app.invoke(initial_state)
    latency = round(time.time() - start_time, 2)
    
    # Log run to SQLite database
    log_run(
        dataset_id=dataset_id,
        question=question,
        sql=final_state.get("sql") or "",
        latency=latency,
        retries=final_state.get("retries", 0),
        success=final_state.get("success", False),
        error=final_state.get("error")
    )
    
    return {
        "question": question,
        "plan": final_state.get("plan"),
        "sql": final_state.get("sql"),
        "chart_base64": final_state.get("chart_base64"),
        "summary": final_state.get("summary", ""),
        "trace": final_state.get("trace", []),
        "retries": final_state.get("retries", 0),
        "success": final_state.get("success", False),
        "error": final_state.get("error")
    }

