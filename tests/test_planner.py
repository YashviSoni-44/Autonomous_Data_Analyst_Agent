"""
Unit and integration tests for Query Planning & Structured Agentic Workflow (Phase 2).
"""
import pytest
import os
from backend.agent.tools_planner import generate_analysis_plan
from backend.ingestion import load_file_into_duckdb
from backend.agent.graph import run_agent


def test_generate_analysis_plan_fallback():
    schema_str = "Table: sales\nColumns:\n  - region (VARCHAR)\n  - sales_amount (DOUBLE)"
    question = "What is total sales by region?"
    plan = generate_analysis_plan(question, schema_str)

    assert isinstance(plan, dict)
    assert "intent" in plan
    assert "metrics" in plan
    assert "dimensions" in plan
    assert "operations" in plan
    assert "steps" in plan
    assert len(plan["steps"]) > 0


def test_agent_graph_with_plan():
    """
    Verifies the plan is generated and structured correctly on every agent run,
    regardless of whether the LLM produces valid SQL (Ollama may not be running in test environments).
    """
    if os.path.exists("data/sample_dataset.csv"):
        dataset_id, _ = load_file_into_duckdb("data/sample_dataset.csv")
        result = run_agent(dataset_id, "What is total sales by region?")

        # Plan must always be generated regardless of SQL success
        assert result["plan"] is not None
        assert isinstance(result["plan"], dict)
        assert "intent" in result["plan"]
        assert "steps" in result["plan"]
        assert len(result["plan"]["steps"]) > 0
        assert "metrics" in result["plan"]
        assert "dimensions" in result["plan"]
        assert "operations" in result["plan"]

