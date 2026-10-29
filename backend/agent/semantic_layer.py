"""
Semantic Metric Layer (Phase 6):
Defines business metric formulas, aliases, and semantic guidance to prevent
LLM business logic hallucinations (e.g. churn rate, MRR, gross margin, AOV).
"""
import os
import json
import re
from typing import Dict, List, Optional, Any

METRICS_STORAGE_PATH = os.getenv("METRICS_STORAGE_PATH", "./metrics.json")

# Built-in Standard Enterprise Metric Definitions
DEFAULT_METRICS: Dict[str, Dict[str, Any]] = {
    "mrr": {
        "name": "MRR",
        "label": "Monthly Recurring Revenue",
        "aliases": ["mrr", "monthly recurring revenue", "recurring revenue", "monthly revenue"],
        "formula": "SUM(mrr) or SUM(amount) for active subscriptions",
        "category": "revenue",
        "description": "Total predictable recurring revenue earned from active subscriptions on a monthly cadence."
    },
    "arr": {
        "name": "ARR",
        "label": "Annual Recurring Revenue",
        "aliases": ["arr", "annual recurring revenue", "yearly run rate", "annual revenue run rate"],
        "formula": "SUM(mrr) * 12 or SUM(annual_contract_value)",
        "category": "revenue",
        "description": "Value of contracted recurring revenue normalized to a single calendar year."
    },
    "aov": {
        "name": "AOV",
        "label": "Average Order Value",
        "aliases": ["aov", "average order value", "avg order value", "order basket size", "average ticket"],
        "formula": "SUM(sales_amount) * 1.0 / NULLIF(COUNT(DISTINCT order_id), 0)",
        "category": "sales",
        "description": "Average dollar amount spent each time a customer places an order."
    },
    "churn_rate": {
        "name": "Churn Rate",
        "label": "Customer Churn Percentage",
        "aliases": ["churn", "churn rate", "attrition rate", "customer churn", "subscriber loss"],
        "formula": "COUNT(CASE WHEN status IN ('churned', 'cancelled') THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0)",
        "category": "retention",
        "description": "Percentage of customers or accounts that stop doing business within a specified timeframe."
    },
    "gross_margin": {
        "name": "Gross Margin",
        "label": "Gross Profit Margin (%)",
        "aliases": ["gross margin", "profit margin", "gross profit margin", "margin percentage"],
        "formula": "(SUM(sales_amount) - SUM(cost_amount)) * 100.0 / NULLIF(SUM(sales_amount), 0)",
        "category": "profitability",
        "description": "Proportion of money left over from revenues after accounting for the cost of goods sold (COGS)."
    },
    "return_rate": {
        "name": "Return Rate",
        "label": "Product Return Rate (%)",
        "aliases": ["return rate", "product returns", "refund rate", "return percentage"],
        "formula": "COUNT(CASE WHEN return_status = 'returned' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0)",
        "category": "operations",
        "description": "Percentage of fulfilled orders or items that are subsequently returned or refunded."
    }
}


def load_metrics() -> Dict[str, Dict[str, Any]]:
    """
    Loads custom metrics merged with default enterprise definitions.
    """
    metrics = dict(DEFAULT_METRICS)
    if os.path.exists(METRICS_STORAGE_PATH):
        try:
            with open(METRICS_STORAGE_PATH, "r", encoding="utf-8") as f:
                custom = json.load(f)
                if isinstance(custom, dict):
                    metrics.update(custom)
        except Exception as e:
            print(f"[SemanticLayer] Warning: Failed to read {METRICS_STORAGE_PATH}: {e}")
    return metrics


def save_custom_metric(metric_id: str, metric_data: Dict[str, Any]) -> bool:
    """
    Saves or updates a custom metric definition to disk.
    """
    try:
        current = {}
        if os.path.exists(METRICS_STORAGE_PATH):
            try:
                with open(METRICS_STORAGE_PATH, "r", encoding="utf-8") as f:
                    current = json.load(f)
            except Exception:
                current = {}

        current[metric_id.lower().strip()] = metric_data
        with open(METRICS_STORAGE_PATH, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2)
        return True
    except Exception as e:
        print(f"[SemanticLayer] Error saving metric: {e}")
        return False


def detect_matched_metrics(question: str) -> List[Dict[str, Any]]:
    """
    Identifies if a natural language question references any registered semantic metrics.
    """
    all_metrics = load_metrics()
    matched = []
    q_lower = question.lower()

    for m_id, metric in all_metrics.items():
        aliases = metric.get("aliases", [m_id])
        for alias in aliases:
            # Match whole word / phrase boundaries
            pattern = rf"\b{re.escape(alias.lower())}\b"
            if re.search(pattern, q_lower):
                matched.append(metric)
                break

    return matched


def build_semantic_guidance_prompt(question: str, schema_str: str = "") -> str:
    """
    Constructs contextual semantic instructions for LLM planning and SQL generation
    when known business metrics are queried.
    """
    matched = detect_matched_metrics(question)
    if not matched:
        return ""

    lines = ["\n[SEMANTIC METRIC LAYER RULES]"]
    lines.append("The question references verified business metric definitions. Follow these standard formulas:")

    for m in matched:
        lines.append(f"• Metric '{m['name']}' ({m['label']}):")
        lines.append(f"  - Business Definition: {m['description']}")
        lines.append(f"  - Standard Analytical SQL Formula: {m['formula']}")

    lines.append("Adapt column names to the active dataset schema while preserving this exact mathematical logic.")
    lines.append("[END SEMANTIC METRIC LAYER]\n")

    return "\n".join(lines)
