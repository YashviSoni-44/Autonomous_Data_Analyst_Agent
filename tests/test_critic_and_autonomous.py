"""
Unit & Integration Tests for Phase 5:
- Critic Verification Loop (numeric grounding, hallucination detection, auto-correction)
- Autonomous Dataset Investigation Engine & API (/analyze/{dataset_id})
"""
import pytest
import pandas as pd
from fastapi.testclient import TestClient

from backend.agent.tools_critic import (
    verify_analysis_output,
    extract_numbers_from_text,
    extract_numbers_from_dataframe,
)
from backend.agent.tools_autonomous import run_autonomous_dataset_investigation
from backend.ingestion import load_file_into_duckdb
from backend.main import app
from backend.agent.graph import run_agent

client = TestClient(app)


@pytest.fixture(scope="module")
def sample_sales_data(tmp_path_factory):
    fn = tmp_path_factory.mktemp("data") / "sales_audit.csv"
    csv_content = (
        "Category,Product,Sales_Amount,Quantity,Region,Discount\n"
        "Electronics,Laptop,1200,2,North,0.1\n"
        "Electronics,Phone,800,5,South,0.05\n"
        "Furniture,Chair,150,10,East,0.0\n"
        "Furniture,Desk,450,3,West,0.15\n"
        "Office,Pen,20,50,North,0.0\n"
        "Electronics,Tablet,600,4,East,0.1\n"
        "Electronics,Server,9500,1,North,0.0\n"  # Extreme outlier
    )
    fn.write_text(csv_content)
    dataset_id, _ = load_file_into_duckdb(str(fn))
    return dataset_id, str(fn)


def test_extract_numbers_from_text():
    text = "The total sales reached 12,500.50 with an average of 450 across 6 orders."
    numbers = extract_numbers_from_text(text)
    assert 12500.50 in numbers
    assert 450.0 in numbers
    assert 6.0 in numbers


def test_critic_passes_grounded_summary():
    df = pd.DataFrame({
        "Category": ["Electronics", "Furniture"],
        "Sales_Amount": [2000.0, 600.0]
    })
    summary = "Electronics generated 2000.0 in sales while Furniture accounted for 600.0 across 2 categories."
    res = verify_analysis_output(
        question="Total sales by category",
        sql="SELECT Category, SUM(Sales_Amount) FROM data GROUP BY Category",
        df=df,
        chart_base64=None,
        summary=summary,
        analytics_result=None
    )
    assert res["is_valid"] is True
    assert res["hallucination_detected"] is False
    assert res["score"] >= 0.8


def test_critic_flags_hallucinated_numbers():
    df = pd.DataFrame({
        "Category": ["Electronics", "Furniture"],
        "Sales_Amount": [2000.0, 600.0]
    })
    # Fabricated numbers not in data
    hallucinated_summary = "Electronics skyrocketed to 98500.75 with a 47000.00 margin increase."
    res = verify_analysis_output(
        question="Total sales by category",
        sql="SELECT Category, SUM(Sales_Amount) FROM data GROUP BY Category",
        df=df,
        chart_base64=None,
        summary=hallucinated_summary,
        analytics_result=None
    )
    assert res["hallucination_detected"] is True
    assert res["checks"]["numeric_grounding"] is False
    assert res["corrected_summary"] is not None
    # Verified that corrected summary is grounded
    assert "98500" not in res["corrected_summary"]


def test_critic_flags_empty_dataframe_discrepancy():
    empty_df = pd.DataFrame()
    summary = "Analysis reveals highest profit in North region."
    res = verify_analysis_output(
        question="Sales in Antarctica",
        sql="SELECT * FROM data WHERE Region = 'Antarctica'",
        df=empty_df,
        chart_base64=None,
        summary=summary,
    )
    assert res["hallucination_detected"] is True
    assert res["checks"]["row_count_valid"] is False
    assert "0 matching records" in res["corrected_summary"]


def test_agent_graph_includes_critic_node(sample_sales_data):
    dataset_id, _ = sample_sales_data
    result = run_agent(
        dataset_id=dataset_id,
        question="What is the total sales amount by category?",
    )
    assert result["success"] is True
    assert result["critic_result"] is not None
    assert "is_valid" in result["critic_result"]
    assert "score" in result["critic_result"]
    # Verify Critic trace step
    trace_nodes = [t["node"] for t in result["trace"]]
    assert "Critic_Tool" in trace_nodes


def test_run_autonomous_dataset_investigation(sample_sales_data):
    dataset_id, _ = sample_sales_data
    report = run_autonomous_dataset_investigation(dataset_id)

    assert report["dataset_id"] == dataset_id
    assert report["table_name"] is not None
    assert len(report["executive_summary"]) > 20
    assert len(report["kpi_metrics"]) >= 2
    assert len(report["top_findings"]) >= 1
    assert len(report["recommended_actions"]) >= 2

    # Check that anomaly detection captured the 9500 server record
    assert len(report["anomalies_detected"]) > 0
    anomaly = report["anomalies_detected"][0]
    assert anomaly["outlier_count"] >= 1
    assert report["chart_base64"] is not None


def test_api_analyze_endpoint(sample_sales_data):
    dataset_id, _ = sample_sales_data
    response = client.post(f"/analyze/{dataset_id}")
    assert response.status_code == 200
    data = response.json()

    assert data["dataset_id"] == dataset_id
    assert "kpi_metrics" in data
    assert "top_findings" in data
    assert "anomalies_detected" in data
    assert "recommended_actions" in data
    assert "executive_summary" in data
