"""
Summary Tool: Generates 2-3 sentence business insight from SQL query results.
"""
import pandas as pd
from backend.llm_client import call_llm

def generate_summary(question: str, sql: str, df: pd.DataFrame) -> str:
    """
    Given the user question, executed SQL, and result DataFrame,
    generates a 2-3 sentence clear business insight.
    """
    if df.empty:
        return "No data returned for this query."

    sample_rows = df.head(15).to_string(index=False)
    total_rows = len(df)

    system_instruction = (
        "You are an executive Data Analyst. Convert the SQL query result rows into a clear, professional 2-3 sentence executive business summary.\n"
        "Rules:\n"
        "1. Highlight top metrics, totals, trends, or leading items.\n"
        "2. Format numbers clearly (e.g., $1,200.50, units, or percentages).\n"
        "3. Do NOT mention SQL syntax, table names, or technical code details."
    )

    prompt = (
        f"Question: {question}\n"
        f"Result Preview:\n{sample_rows}\n\n"
        f"Executive Business Summary:"
    )

    try:
        summary = call_llm(prompt, system_instruction)
        return summary.strip()
    except Exception as e:
        return f"Query returned {total_rows} row(s). (Failed to generate automated narrative: {str(e)})"
