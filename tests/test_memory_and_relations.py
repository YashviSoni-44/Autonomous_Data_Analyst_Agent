"""
Unit tests for Phase 3: Conversational Memory & Multi-Table Schema Integration.
"""
import pytest
import os
import duckdb
import pandas as pd
from backend.agent.tools_relations import infer_table_relationships, build_join_hints
from backend.agent.tools_followup import generate_followup_suggestions
from backend.ingestion import load_file_into_duckdb


# ── Multi-Table Relationship Inference ───────────────────────────────────────

def test_no_relationships_for_single_table():
    """Single-table dataset returns no relationships."""
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE orders (order_id INT, customer_id INT, amount DOUBLE)")
    rels = infer_table_relationships(conn)
    assert rels == []


def test_exact_column_match_detected():
    """Two tables with an identical column name should produce a HIGH-confidence relationship."""
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE orders (order_id INT, customer_id INT)")
    conn.execute("CREATE TABLE customers (customer_id INT, name VARCHAR)")
    rels = infer_table_relationships(conn)
    assert len(rels) >= 1
    match = [r for r in rels if r["left_col"] == "customer_id" or r["right_col"] == "customer_id"]
    assert len(match) >= 1
    assert match[0]["confidence"] == "HIGH"


def test_normalised_suffix_match():
    """Columns 'customer_id' and 'customer_key' should match after suffix normalisation."""
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE orders (order_id INT, customer_id INT)")
    conn.execute("CREATE TABLE customers (customer_key INT, name VARCHAR)")
    rels = infer_table_relationships(conn)
    # Should find at least a MEDIUM confidence link via normalised suffix
    medium = [r for r in rels if r["confidence"] in ("MEDIUM", "HIGH")]
    assert len(medium) >= 1


def test_build_join_hints_no_relations():
    """Single table: build_join_hints returns empty string."""
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE data (id INT, val DOUBLE)")
    hints = build_join_hints(conn)
    assert hints == ""


def test_build_join_hints_with_relations():
    """Two related tables: build_join_hints returns non-empty hint block."""
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE orders (order_id INT, customer_id INT)")
    conn.execute("CREATE TABLE customers (customer_id INT, name VARCHAR)")
    hints = build_join_hints(conn)
    assert "JOIN" in hints
    assert "customer_id" in hints


# ── Follow-up Question Generator ─────────────────────────────────────────────

def test_followup_returns_list():
    """generate_followup_suggestions always returns a list of 3 strings."""
    suggestions = generate_followup_suggestions(
        question="What is total sales by region?",
        sql="SELECT region, SUM(sales) FROM orders GROUP BY region",
        summary="The East region generated the highest sales at $1.2M.",
    )
    assert isinstance(suggestions, list)
    assert len(suggestions) == 3
    for s in suggestions:
        assert isinstance(s, str)
        assert len(s) > 5


def test_followup_fallback_on_empty_inputs():
    """Even with minimal inputs, fallback suggestions are returned."""
    suggestions = generate_followup_suggestions(question="", sql="", summary="")
    assert len(suggestions) == 3


# ── Session State in Agent ───────────────────────────────────────────────────

def test_run_agent_returns_session_id():
    """run_agent must always return a session_id."""
    if not os.path.exists("data/sample_dataset.csv"):
        pytest.skip("Sample dataset not available")

    from backend.agent.graph import run_agent
    dataset_id, _ = load_file_into_duckdb("data/sample_dataset.csv")
    result = run_agent(dataset_id, "What is total sales?")
    assert "session_id" in result
    assert result["session_id"] is not None
    assert isinstance(result["session_id"], str)


def test_run_agent_session_id_persists():
    """Passing the same session_id returns it back unchanged."""
    if not os.path.exists("data/sample_dataset.csv"):
        pytest.skip("Sample dataset not available")

    from backend.agent.graph import run_agent
    dataset_id, _ = load_file_into_duckdb("data/sample_dataset.csv")
    result = run_agent(dataset_id, "How many rows?", session_id="test-sess-01")
    assert result["session_id"] == "test-sess-01"
