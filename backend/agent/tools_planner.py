"""
Planner Tool: Prompts the LLM to generate a structured AnalysisPlan before SQL generation.
"""
import json
import re
from typing import Dict, Any
from backend.llm_client import call_llm
from backend.models import AnalysisPlan


PLANNER_SYSTEM_PROMPT = """You are an expert AI Data Analyst Strategist.
Given a user's business question and a database schema, construct a structured analysis strategy plan before writing SQL.

Return ONLY a single valid JSON object matching this schema:
{
  "intent": "Short explanation of the analytical goal",
  "metrics": ["metric_1", "metric_2"],
  "dimensions": ["dimension_1"],
  "filters": ["filter_clause or none"],
  "time_range": "time range if applicable else null",
  "operations": ["AGGREGATE", "GROUP BY", "SORT", "LIMIT"],
  "visualization_recommended": true,
  "chart_type_suggestion": "bar_chart" | "line_chart" | "pie_chart" | "scatter_plot" | null,
  "steps": [
    "Step 1: Description",
    "Step 2: Description"
  ]
}

DO NOT include markdown code blocks, preambles, or postscript text outside the JSON object.
"""


def generate_analysis_plan(question: str, schema_str: str) -> Dict[str, Any]:
    """
    Generates a structured analysis plan (intent, metrics, dimensions, filters, operations, steps).
    Returns a dictionary representation of AnalysisPlan.
    """
    user_prompt = f"""Database Schema:
{schema_str}

User Question:
"{question}"

Generate the JSON Analysis Plan:"""

    try:
        raw_response = call_llm(user_prompt, system_instruction=PLANNER_SYSTEM_PROMPT, timeout=25, optional=True)

        # Attempt to extract JSON
        cleaned = raw_response.strip()
        # Strip markdown backticks if present
        if "```" in cleaned:
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1)
            else:
                cleaned = cleaned.replace("```json", "").replace("```", "").strip()

        plan_dict = json.loads(cleaned)
        # Validate through Pydantic
        plan_obj = AnalysisPlan(
            intent=plan_dict.get("intent", f"Analyze query: {question}"),
            metrics=plan_dict.get("metrics", []),
            dimensions=plan_dict.get("dimensions", []),
            filters=plan_dict.get("filters", []),
            time_range=plan_dict.get("time_range"),
            operations=plan_dict.get("operations", []),
            visualization_recommended=bool(plan_dict.get("visualization_recommended", True)),
            chart_type_suggestion=plan_dict.get("chart_type_suggestion"),
            steps=plan_dict.get("steps", [f"Decompose query: {question}", "Generate SQL", "Execute and plot results"]),
        )
        return plan_obj.model_dump()
    except Exception:
        # Fallback structured plan
        return AnalysisPlan(
            intent=f"Analyze data for query: {question}",
            metrics=["result_metric"],
            dimensions=["grouping_column"],
            filters=[],
            time_range=None,
            operations=["SELECT", "AGGREGATE", "LIMIT"],
            visualization_recommended=True,
            chart_type_suggestion="bar_chart",
            steps=[
                f"1. Understand intent for '{question}'",
                "2. Generate read-only SQL query over schema",
                "3. Execute query and synthesize visual & narrative insights",
            ],
        ).model_dump()
