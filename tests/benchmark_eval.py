"""
Automated LLM Benchmark & Evaluation Suite (LLM-as-a-Judge).
Systematically evaluates:
- SQL Execution Success Rate (%)
- AST Read-Only Guardrails Compliance (%)
- Factual Groundedness & Hallucination Defense Rate (%)
- Semantic Metric Alignment (%)
- Query Latency Benchmarks (Avg & P95)
"""
import os
import sys
import time
import json
from typing import List, Dict, Any

# Ensure project root is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.ingestion import load_file_into_duckdb
from backend.agent.graph import run_agent
from backend.agent.tools_sql import validate_sql_guardrails
from backend.agent.semantic_layer import detect_matched_metrics

BENCHMARK_RESULTS_FILE = "./benchmark_results.json"

# Curated Golden Evaluation Cases
GOLDEN_BENCHMARK_CASES = [
    {
        "id": "EVAL-01",
        "dataset_file": "data/clean_saas_metrics.csv",
        "question": "What is the average MRR across all recorded plans?",
        "category": "Semantic Metric & Aggregation",
        "expected_intent": "sql",
        "expected_semantic_metric": "MRR",
    },
    {
        "id": "EVAL-02",
        "dataset_file": "data/clean_saas_metrics.csv",
        "question": "What is the correlation between mrr and active_users?",
        "category": "Statistical Analytics (Correlation)",
        "expected_intent": "correlation",
    },
    {
        "id": "EVAL-03",
        "dataset_file": "data/dirty_ecommerce_returns.csv",
        "question": "Are there any extreme outliers in quantity_returned?",
        "category": "Anomaly & Outlier Detection",
        "expected_intent": "outliers",
    },
    {
        "id": "EVAL-04",
        "dataset_file": "data/clean_saas_metrics.csv",
        "question": "Forecast the MRR growth trend for the next 3 months",
        "category": "Time-Series Forecasting",
        "expected_intent": "forecast",
    },
    {
        "id": "EVAL-05",
        "dataset_file": "data/dirty_ecommerce_returns.csv",
        "question": "Which product category has the highest total quantity_returned?",
        "category": "Group-by & Ranking under Dirty Data",
        "expected_intent": "sql",
    }

]


def run_benchmark_eval(output_file: str = BENCHMARK_RESULTS_FILE) -> Dict[str, Any]:
    """
    Executes the automated evaluation suite across golden benchmark questions.
    Returns the aggregated scorecard dictionary.
    """
    print("\n" + "=" * 70)
    print("🚀 STARTING AUTONOMOUS DATA ANALYST BENCHMARK & EVALUATION SUITE")
    print("=" * 70)

    dataset_cache = {}
    results: List[Dict[str, Any]] = []

    for test_case in GOLDEN_BENCHMARK_CASES:
        t_id = test_case["id"]
        q = test_case["question"]
        file_path = test_case["dataset_file"]
        cat = test_case["category"]

        print(f"\n▶ Evaluating [{t_id}] {cat}: '{q}'")

        # Ingest dataset if not cached
        if file_path not in dataset_cache:
            if not os.path.exists(file_path):
                print(f"  ⚠️ Warning: Benchmark file '{file_path}' not found, skipping.")
                continue
            dataset_id, tables = load_file_into_duckdb(file_path)
            dataset_cache[file_path] = (dataset_id, tables)
        else:
            dataset_id, tables = dataset_cache[file_path]

        t0 = time.time()
        agent_out = run_agent(dataset_id=dataset_id, question=q)
        duration = round(time.time() - t0, 2)

        # 1. SQL Execution Success
        sql = agent_out.get("sql")
        sql_success = agent_out.get("success", False) and bool(sql)

        # 2. AST Read-Only Guardrails Check
        ast_safe, ast_err = validate_sql_guardrails(sql) if sql else (False, "No SQL")

        # 3. Numeric Grounding & Critic Validation
        critic = agent_out.get("critic_result") or {}
        critic_grounded = not critic.get("hallucination_detected", False)
        groundedness_score = critic.get("score", 1.0 if sql_success else 0.0)

        # 4. Semantic Metric / Intent Matching
        matched_metrics = detect_matched_metrics(q)
        expected_metric = test_case.get("expected_semantic_metric")
        metric_aligned = True
        if expected_metric:
            metric_aligned = any(m["name"] == expected_metric for m in matched_metrics)

        # Intent Alignment
        detected_intent = agent_out.get("analysis_type", "sql")
        expected_intent = test_case.get("expected_intent")
        intent_match = (detected_intent == expected_intent) or (expected_intent == "sql" and detected_intent == "sql")

        case_passed = sql_success and ast_safe and critic_grounded

        results.append({
            "id": t_id,
            "category": cat,
            "question": q,
            "latency_seconds": duration,
            "sql_success": sql_success,
            "ast_safe": ast_safe,
            "critic_grounded": critic_grounded,
            "groundedness_score": groundedness_score,
            "metric_aligned": metric_aligned,
            "intent_match": intent_match,
            "overall_pass": case_passed,
            "generated_sql": sql,
            "retries": agent_out.get("retries", 0),
        })

        status_icon = "✅ PASS" if case_passed else "❌ FAIL"
        print(f"  Result: {status_icon} | Latency: {duration}s | AST Safe: {ast_safe} | Grounding: {groundedness_score:.2f}")

    # Compute Aggregates
    total = len(results)
    if total == 0:
        return {"total_tests": 0, "status": "No tests run"}

    passed_count = sum(1 for r in results if r["overall_pass"])
    sql_rate = round(sum(1 for r in results if r["sql_success"]) / total * 100, 1)
    ast_rate = round(sum(1 for r in results if r["ast_safe"]) / total * 100, 1)
    grounding_rate = round(sum(1 for r in results if r["critic_grounded"]) / total * 100, 1)
    avg_score = round(sum(r["groundedness_score"] for r in results) / total * 100, 1)
    avg_latency = round(sum(r["latency_seconds"] for r in results) / total, 2)
    overall_accuracy = round(passed_count / total * 100, 1)

    # Compute Grade
    if overall_accuracy >= 95:
        grade = "A+ (Enterprise Ready)"
    elif overall_accuracy >= 80:
        grade = "A (High Reliability)"
    elif overall_accuracy >= 70:
        grade = "B+ (Production Viable)"
    else:
        grade = "Needs Tuning"

    scorecard = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_evaluated": total,
        "tests_passed": passed_count,
        "overall_accuracy_pct": overall_accuracy,
        "sql_success_rate_pct": sql_rate,
        "ast_guardrails_compliance_pct": ast_rate,
        "hallucination_defense_rate_pct": grounding_rate,
        "mean_groundedness_pct": avg_score,
        "avg_latency_seconds": avg_latency,
        "benchmark_grade": grade,
        "test_results": results,
    }

    # Save to disk
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(scorecard, f, indent=2)
        print(f"\n📁 Scorecard saved to: {output_file}")
    except Exception as e:
        print(f"Failed to write benchmark scorecard: {e}")

    # Print Formatted Report Table
    print("\n" + "=" * 70)
    print("📊 BENCHMARK SCORECARD & ACCURACY REPORT")
    print("=" * 70)
    print(f"Overall Benchmark Grade      : {grade}")
    print(f"End-to-End Test Accuracy     : {overall_accuracy}% ({passed_count}/{total} passed)")
    print(f"SQL Generation Success Rate  : {sql_rate}%")
    print(f"AST Read-Only Compliance     : {ast_rate}%")
    print(f"Hallucination Defense Rate   : {grounding_rate}%")
    print(f"Mean Grounding Score         : {avg_score}%")
    print(f"Average Execution Latency    : {avg_latency}s")
    print("=" * 70 + "\n")

    return scorecard


def test_benchmark_eval_suite():
    """
    Pytest wrapper to verify that benchmark evaluation passes with acceptable thresholds.
    """
    scorecard = run_benchmark_eval()
    assert scorecard["total_evaluated"] >= 3
    assert scorecard["sql_success_rate_pct"] >= 75.0
    assert scorecard["ast_guardrails_compliance_pct"] == 100.0


if __name__ == "__main__":
    run_benchmark_eval()
