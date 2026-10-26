"""
Critic and Verification Engine for the Autonomous Data Analyst Agent.
Phase 5.1: Post-execution verification, factual grounding, hallucination detection,
and automated self-correction loop.
"""
from typing import Optional, Dict, Any, List, Set
import re
import pandas as pd
from backend.llm_client import call_llm


def extract_numbers_from_text(text: Optional[str]) -> List[float]:
    """
    Extracts numerical figures from text, filtering out non-metric numbers.
    Safely handles None or empty input strings.
    """
    if not text:
        return []

    # Matches integers and decimals, handles commas like 1,200.50
    cleaned = re.sub(r'(\d),(\d)', r'\1\2', text)
    tokens = re.findall(r'(?<![a-zA-Z_])\d+(?:\.\d+)?(?![a-zA-Z_])', cleaned)
    numbers: List[float] = []
    for t in tokens:
        try:
            val = float(t)
            numbers.append(val)
        except (ValueError, TypeError):
            continue
    return numbers


def extract_numbers_from_dataframe(df: Optional[pd.DataFrame]) -> Set[float]:
    """
    Extracts all numeric values and simple row/column aggregates from dataframe for grounding checks.
    """
    nums: Set[float] = set()
    if df is None or df.empty:
        return nums

    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            col_vals = df[col].dropna()
            for v in col_vals:
                try:
                    fv = float(v)
                    nums.add(round(fv, 2))
                    nums.add(round(fv, 0))
                except (ValueError, TypeError):
                    continue
            # Add common statistical aggregates cited in summaries
            if len(col_vals) > 0:
                try:
                    c_sum = float(col_vals.sum())
                    c_mean = float(col_vals.mean())
                    c_max = float(col_vals.max())
                    c_min = float(col_vals.min())
                    nums.add(round(c_sum, 2))
                    nums.add(round(c_sum, 0))
                    nums.add(round(c_mean, 2))
                    nums.add(round(c_mean, 0))
                    nums.add(round(c_max, 2))
                    nums.add(round(c_min, 2))
                except (ValueError, TypeError):
                    pass

    # Add row count and column count
    nums.add(float(len(df)))
    nums.add(float(len(df.columns)))
    return nums


def extract_numbers_from_analytics(analytics_result: Optional[dict]) -> Set[float]:
    """
    Gathers metrics produced by analytics tools (e.g., outlier counts, percentages, forecast values).
    """
    nums: Set[float] = set()
    if not analytics_result:
        return nums

    def recurse(data: Any) -> None:
        if isinstance(data, dict):
            for v in data.values():
                recurse(v)
        elif isinstance(data, (list, tuple)):
            for item in data:
                recurse(item)
        elif isinstance(data, (int, float)):
            try:
                fv = float(data)
                nums.add(round(fv, 2))
                nums.add(round(fv, 0))
            except (ValueError, TypeError):
                pass

    recurse(analytics_result)
    return nums


def verify_analysis_output(
    question: str,
    sql: Optional[str],
    df: Optional[pd.DataFrame],
    chart_base64: Optional[str],
    summary: Optional[str] = "",
    analytics_result: Optional[dict] = None
) -> Dict[str, Any]:
    """
    Inspects generated response components (SQL, results, charts, summaries)
    to enforce mathematical and factual accuracy.
    """
    if summary is None:
        summary = ""

    checks = {
        "numeric_grounding": True,
        "chart_consistency": True,
        "row_count_valid": True,
    }
    critique_notes: List[str] = []
    hallucination_detected = False
    corrected_summary: Optional[str] = None

    # Check 1: Row count sanity
    is_empty_df = (df is None or df.empty)
    if is_empty_df:
        checks["row_count_valid"] = False
        # If df is empty, the summary should acknowledge that no records were returned
        positive_affirmations = ["found", "shows that", "top", "highest", "total of", "reveals", "exceeded"]
        if any(term in summary.lower() for term in positive_affirmations):
            critique_notes.append("Empty dataset returned, but summary claims positive findings.")
            hallucination_detected = True
            corrected_summary = "The query executed successfully but returned 0 matching records for this filter criteria."

    # Check 2: Chart consistency
    chart_keywords = ["chart", "plot", "graph", "histogram", "heatmap", "visualization"]
    summary_mentions_chart = any(re.search(rf"\b{kw}\b", summary.lower()) for kw in chart_keywords)
    if summary_mentions_chart and not chart_base64:
        checks["chart_consistency"] = False
        critique_notes.append("Summary explicitly refers to a chart, but no visual artifact was generated.")

    # Check 3: Numeric Grounding
    if not is_empty_df and df is not None:
        summary_numbers = extract_numbers_from_text(summary)
        # Filter out numbers that are common step indexes or years
        testable_numbers = [
            n for n in summary_numbers
            if n not in {0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 10.0, 100.0, 2023.0, 2024.0, 2025.0, 2026.0}
        ]

        if testable_numbers:
            grounded_nums = extract_numbers_from_dataframe(df)
            analytics_nums = extract_numbers_from_analytics(analytics_result)
            all_known_nums = grounded_nums.union(analytics_nums)

            def is_grounded(target: float) -> bool:
                for k in all_known_nums:
                    if abs(target - k) < 0.05 or (k != 0 and abs(target - k) / abs(k) < 0.02):
                        return True
                return False

            unsupported = [n for n in testable_numbers if not is_grounded(n)]

            # If more than 40% of specific numbers cited are ungrounded
            if len(unsupported) > 0 and (len(unsupported) / len(testable_numbers)) > 0.4:
                checks["numeric_grounding"] = False
                critique_notes.append(
                    f"Unsupported numerical claims detected ({unsupported[:3]}). Values not found in SQL data."
                )
                hallucination_detected = True

    # Calculate overall confidence score (0.0 to 1.0)
    passed_checks = sum(1 for v in checks.values() if v)
    score = round(passed_checks / len(checks), 2)
    if hallucination_detected:
        score = min(score, 0.5)

    # Perform Self-Correction if hallucination was detected
    if hallucination_detected and not corrected_summary and not is_empty_df and df is not None:
        corrected_summary = self_correct_summary(
            question=question,
            df=df,
            critique="; ".join(critique_notes),
            original_summary=summary,
            analytics_result=analytics_result
        )

    critique_str = "; ".join(critique_notes) if critique_notes else "Verification passed. All metrics and claims are grounded."

    return {
        "is_valid": bool(not hallucination_detected and score >= 0.7),
        "score": score,
        "hallucination_detected": hallucination_detected,
        "critique": critique_str,
        "corrected_summary": corrected_summary,
        "checks": checks,
    }


def self_correct_summary(
    question: str,
    df: Optional[pd.DataFrame],
    critique: str,
    original_summary: str,
    analytics_result: Optional[dict] = None
) -> str:
    """
    Generates a factual, grounded executive summary replacing a hallucinated or flawed draft.
    Safely handles empty or missing dataframes.
    """
    if df is None or df.empty:
        return "Query executed with 0 matching records. No statistical metrics available."

    rows_sample = df.head(10).to_dict(orient="records")
    system_prompt = (
        "You are a strict Data Quality Critic. The previous summary contained hallucinated or "
        "ungrounded numbers that failed factual verification. Rewrite the summary so it ONLY states "
        "facts, numbers, and trends directly supported by the data table provided. Maximum 2-3 concise sentences."
    )
    user_prompt = (
        f"User Question: {question}\n\n"
        f"Verified Data Rows (top 10):\n{rows_sample}\n\n"
        f"Data Row Count: {len(df)}\n"
        f"Identified Flaws in Draft: {critique}\n"
        f"Previous Draft: {original_summary}\n\n"
        "Generate a strictly grounded, accurate executive summary:"
    )

    try:
        corrected = call_llm(prompt=user_prompt, system_instruction=system_prompt, timeout=25, optional=True)
        if corrected and len(corrected.strip()) > 10:
            return corrected.strip()
    except Exception:
        pass

    # Deterministic fallback correction
    cols = list(df.columns)
    first_obs = df.iloc[0].to_dict() if len(df) > 0 else {}
    return (
        f"Based on the verified query results across {len(df)} records, the data shows entries for "
        f"{', '.join(cols[:3])}. Top observation indicates {first_obs}."
    )
