"""
SQL Generation & Guardrails Tool.
Generates DuckDB SQL from natural language, enforces read-only guardrails, and self-corrects on syntax errors.
"""
import re
import pandas as pd
import duckdb
from backend.llm_client import call_llm

SQL_GUARDRAIL_FORBIDDEN = [
    r"\bDROP\b", r"\bDELETE\b", r"\bINSERT\b", r"\bUPDATE\b",
    r"\bALTER\b", r"\bTRUNCATE\b", r"\bCREATE\b", r"\bGRANT\b", r"\bREVOKE\b"
]

def validate_sql_guardrails(sql: str) -> tuple[bool, str]:
    """
    Validates that the SQL query is strictly a read-only SELECT statement.
    """
    cleaned_sql = sql.strip().strip(";").upper()
    
    for pattern in SQL_GUARDRAIL_FORBIDDEN:
        if re.search(pattern, cleaned_sql):
            return False, f"Forbidden keyword detected in query. Only read-only SELECT queries are allowed."
            
    if not cleaned_sql.startswith("SELECT") and not cleaned_sql.startswith("WITH"):
        return False, "Query must begin with SELECT or WITH."
        
    return True, ""

def enforce_limit(sql: str, max_limit: int = 500) -> str:
    """
    Ensures query has a LIMIT clause capping results.
    """
    if "LIMIT" not in sql.upper():
        sql = sql.strip().rstrip(";") + f" LIMIT {max_limit}"
    return sql

def generate_and_run_sql(
    question: str,
    schema_str: str,
    conn: duckdb.DuckDBPyConnection,
    max_retries: int = 1,
    plan: dict = None
) -> tuple[str, pd.DataFrame, int, str]:
    """
    Generates SQL from user question using LLM, runs guardrails, executes on DuckDB,
    and self-corrects if execution fails.
    
    Returns (generated_sql, result_df, retries_taken, error_msg)
    """
    system_instruction = (
        "You are an expert DuckDB SQL engineer. Write ONLY valid DuckDB SQL for the provided schema and question.\n"
        "Rules:\n"
        "1. Output ONLY executable SQL inside a ```sql ... ``` block. No commentary or markdown text outside the block.\n"
        "2. For questions asking 'when', 'which', 'who', or 'top' for max/min values, select both the name/date column AND the value, then use ORDER BY ... DESC/ASC LIMIT 1 (or N).\n"
        "   - Example: 'When was max quantity sold?' -> SELECT order_date, customer_name, product, quantity FROM table_name ORDER BY quantity DESC LIMIT 1\n"
        "3. For questions asking for totals, averages, or counts by category/region/product, use GROUP BY and ORDER BY total DESC.\n"
        "4. Use exact column names and table names provided in the schema."
    )
    
    plan_context = ""
    if plan:
        plan_context = f"\nStrategy Plan:\n- Intent: {plan.get('intent')}\n- Metrics: {', '.join(plan.get('metrics', []))}\n- Dimensions: {', '.join(plan.get('dimensions', []))}\n- Operations: {', '.join(plan.get('operations', []))}\n"

    prompt = f"Schema:\n{schema_str}\n{plan_context}\nUser Question: {question}\n\nSQL Query:"
    
    last_error = ""
    current_prompt = prompt
    retries = 0

    while retries <= max_retries:
        try:
            raw_sql = call_llm(current_prompt, system_instruction)
            
            # Clean markdown formatting if model output wraps in ```sql ... ```
            cleaned_sql = raw_sql.strip()
            match = re.search(r"```(?:sql)?\s*(.*?)\s*```", cleaned_sql, re.DOTALL | re.IGNORECASE)
            if match:
                cleaned_sql = match.group(1).strip()
            elif cleaned_sql.startswith("```"):
                cleaned_sql = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned_sql)
                cleaned_sql = re.sub(r"\n?```$", "", cleaned_sql).strip()
            
            # If placeholder data_table is returned by LLM fallback, replace with actual table name from schema
            table_match = re.search(r"Table:\s*([a-zA-Z0-9_]+)", schema_str)
            if table_match:
                first_table = table_match.group(1)
                cleaned_sql = re.sub(r"\bdata_table\b", first_table, cleaned_sql)

            # Guardrails validation
            is_valid, guard_err = validate_sql_guardrails(cleaned_sql)
            if not is_valid:
                raise ValueError(f"Guardrail violation: {guard_err}")
                
            final_sql = enforce_limit(cleaned_sql)
            
            # Execute SQL
            result_df = conn.execute(final_sql).fetchdf()
            return final_sql, result_df, retries, ""
            
        except Exception as e:
            last_error = str(e)
            retries += 1
            if retries <= max_retries:
                current_prompt = (
                    f"Schema:\n{schema_str}\n\n"
                    f"User Question:\n{question}\n\n"
                    f"The previous SQL query failed with error:\n{last_error}\n\n"
                    f"Please fix the query and return ONLY corrected SQL:"
                )

    return "", pd.DataFrame(), retries - 1, f"Failed after {max_retries} retries. Last error: {last_error}"
