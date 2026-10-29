"""
Unit & Integration Tests for Semantic Metric Layer (Phase 6).
"""
import pytest
from fastapi.testclient import TestClient

from backend.agent.semantic_layer import (
    load_metrics,
    detect_matched_metrics,
    build_semantic_guidance_prompt,
    save_custom_metric
)
from backend.main import app

client = TestClient(app)


def test_default_metrics_loaded():
    metrics = load_metrics()
    assert "mrr" in metrics
    assert "arr" in metrics
    assert "aov" in metrics
    assert "churn_rate" in metrics
    assert "gross_margin" in metrics


def test_detect_matched_metrics():
    # Should match MRR
    q1 = "What was our total MRR for last month?"
    matched1 = detect_matched_metrics(q1)
    assert len(matched1) >= 1
    names = [m["name"] for m in matched1]
    assert "MRR" in names

    # Should match Churn Rate
    q2 = "Calculate the quarterly churn rate across all regions."
    matched2 = detect_matched_metrics(q2)
    assert len(matched2) >= 1
    names2 = [m["name"] for m in matched2]
    assert "Churn Rate" in names2

    # Should match Average Order Value
    q3 = "Show me the average order value by customer segment."
    matched3 = detect_matched_metrics(q3)
    assert len(matched3) >= 1
    names3 = [m["name"] for m in matched3]
    assert "AOV" in names3


def test_build_semantic_guidance_prompt():
    prompt = build_semantic_guidance_prompt("What is our gross margin by product category?")
    assert "[SEMANTIC METRIC LAYER RULES]" in prompt
    assert "Gross Margin" in prompt
    assert "SUM(sales_amount)" in prompt or "cost_amount" in prompt


def test_api_metrics_endpoint():
    res = client.get("/metrics")
    assert res.status_code == 200
    data = res.json()
    assert "mrr" in data
    assert "churn_rate" in data


def test_api_post_custom_metric():
    new_metric = {
        "name": "NPS Score",
        "label": "Net Promoter Score",
        "aliases": ["nps", "net promoter score"],
        "formula": "(COUNT(promoters) - COUNT(detractors)) * 100.0 / COUNT(responses)",
        "category": "satisfaction",
        "description": "Customer loyalty and satisfaction index."
    }
    res = client.post("/metrics", json=new_metric)
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    # Verify detected
    matched = detect_matched_metrics("Show trends in our NPS score")
    assert any(m["name"] == "NPS Score" for m in matched)
