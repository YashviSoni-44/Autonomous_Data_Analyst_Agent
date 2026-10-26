"""
Unit and integration tests for Phase 4: Advanced Analytics Engine
(Correlation, Outlier Detection, Time-Series Forecasting, and Agent Routing).
"""
import pytest
import os
import pandas as pd
import numpy as np

from backend.agent.tools_analytics import (
    detect_analysis_intent,
    run_correlation_analysis,
    detect_outliers,
    run_time_series_forecast,
)
from backend.ingestion import load_file_into_duckdb
from backend.agent.graph import run_agent


# ── 1. Intent Detection Tests ────────────────────────────────────────────────

def test_detect_analysis_intent():
    assert detect_analysis_intent("Forecast sales for next month") == "forecast"
    assert detect_analysis_intent("Predict the future trend of revenue") == "forecast"
    assert detect_analysis_intent("What is the projection for next 6 months?") == "forecast"

    assert detect_analysis_intent("What is the correlation between price and quantity?") == "correlation"
    assert detect_analysis_intent("Show me how discount correlates with profit") == "correlation"
    assert detect_analysis_intent("Relationship between sales and spend") == "correlation"

    assert detect_analysis_intent("Find outliers in transaction amount") == "outliers"
    assert detect_analysis_intent("Are there any anomalies or extreme values in price?") == "outliers"
    assert detect_analysis_intent("Detect abnormal orders") == "outliers"

    assert detect_analysis_intent("What is total revenue by region?") == "sql"
    assert detect_analysis_intent("Show top 5 customers") == "sql"


# ── 2. Correlation Analysis Tests ────────────────────────────────────────────

def test_run_correlation_analysis_valid():
    np.random.seed(42)
    x = np.linspace(1, 100, 50)
    y = 2.5 * x + np.random.normal(0, 5, 50)  # Strong positive correlation
    z = -1.8 * x + np.random.normal(0, 5, 50) # Strong negative correlation

    df = pd.DataFrame({"metric_a": x, "metric_b": y, "metric_c": z})
    res = run_correlation_analysis(df)

    assert res["analysis_type"] == "correlation"
    assert "pearson_matrix" in res
    assert "spearman_matrix" in res
    assert len(res["top_pairs"]) > 0

    top = res["top_pairs"][0]
    assert top["strength"] == "Strong"
    assert top["abs_pearson"] > 0.8
    assert res["sample_size"] == 50


def test_run_correlation_analysis_insufficient_cols():
    df = pd.DataFrame({"only_one_numeric": [1, 2, 3, 4], "category": ["A", "B", "C", "D"]})
    res = run_correlation_analysis(df)
    assert "error" in res
    assert "At least 2 numerical columns" in res["error"]


# ── 3. Outlier Detection Tests ───────────────────────────────────────────────

def test_detect_outliers_iqr():
    data = [10, 12, 11, 13, 12, 10, 11, 12, 14, 11, 100, 110]  # 100, 110 are extreme outliers
    df = pd.DataFrame({"item_id": [f"item_{i}" for i in range(len(data))], "price": data})

    res = detect_outliers(df, num_col="price", method="iqr")
    assert res["analysis_type"] == "outliers"
    assert res["method"] == "IQR"
    assert res["outlier_count"] >= 2
    assert res["outlier_percentage"] > 0
    assert "bounds" in res
    assert res["bounds"]["upper_bound"] < 50.0

    # Ensure identified outliers contain the extreme values
    outlier_vals = [o["value"] for o in res["outliers"]]
    assert 100 in outlier_vals
    assert 110 in outlier_vals


def test_detect_outliers_zscore():
    data = [5.0] * 30 + [100.0]  # Single huge spike
    df = pd.DataFrame({"reading": data})

    res = detect_outliers(df, num_col="reading", method="zscore")
    assert res["method"] == "ZSCORE"
    assert res["outlier_count"] >= 1
    assert res["outliers"][0]["value"] == 100.0


# ── 4. Time-Series Forecasting Tests ─────────────────────────────────────────

def test_run_time_series_forecast_valid():
    dates = pd.date_range(start="2025-01-01", periods=12, freq="ME").strftime("%Y-%m-%d").tolist()
    # Steady upward sales trend with slight noise
    values = [100, 115, 130, 140, 160, 175, 190, 210, 225, 240, 260, 280]
    df = pd.DataFrame({"order_date": dates, "revenue": values})

    res = run_time_series_forecast(df, date_col="order_date", val_col="revenue", horizon=4)
    assert res["analysis_type"] == "forecast"
    assert len(res["historical"]) == 12
    assert len(res["forecast"]) == 4
    assert res["metrics"]["trend_direction"] == "Growth"
    assert res["metrics"]["mae"] >= 0.0
    assert res["metrics"]["rmse"] >= 0.0

    # The next forecasted value should be higher than the last historical point (280)
    fc_vals = [f["predicted"] for f in res["forecast"]]
    assert fc_vals[0] > 270.0

    # Bounds must bracket the prediction
    for f in res["forecast"]:
        assert f["lower_bound"] <= f["predicted"] <= f["upper_bound"]


def test_run_time_series_forecast_insufficient_points():
    df = pd.DataFrame({"date": ["2025-01-01", "2025-01-02"], "sales": [10, 20]})
    res = run_time_series_forecast(df)
    assert "error" in res
    assert "at least 4" in res["error"]


# ── 5. End-to-End Agent Routing Tests ────────────────────────────────────────

def test_agent_routes_forecast():
    if not os.path.exists("data/sample_dataset.csv"):
        pytest.skip("Sample dataset not available")

    dataset_id, _ = load_file_into_duckdb("data/sample_dataset.csv")
    result = run_agent(dataset_id, "Forecast sales for the next 3 months")

    assert result["analysis_type"] == "forecast"
    assert "session_id" in result
    assert result["summary"] != ""
    # Should have trace step for Analytics_Tool
    trace_nodes = [t["node"] for t in result.get("trace", [])]
    assert "Analytics_Tool" in trace_nodes


def test_agent_routes_correlation():
    if not os.path.exists("data/sample_dataset.csv"):
        pytest.skip("Sample dataset not available")

    dataset_id, _ = load_file_into_duckdb("data/sample_dataset.csv")
    result = run_agent(dataset_id, "What is the correlation between sales and quantity?")

    assert result["analysis_type"] == "correlation"
    assert "session_id" in result
    trace_nodes = [t["node"] for t in result.get("trace", [])]
    assert "Analytics_Tool" in trace_nodes


def test_agent_routes_outliers():
    if not os.path.exists("data/sample_dataset.csv"):
        pytest.skip("Sample dataset not available")

    dataset_id, _ = load_file_into_duckdb("data/sample_dataset.csv")
    result = run_agent(dataset_id, "Find outliers in sales_amount")

    assert result["analysis_type"] == "outliers"
    assert "session_id" in result
    trace_nodes = [t["node"] for t in result.get("trace", [])]
    assert "Analytics_Tool" in trace_nodes
