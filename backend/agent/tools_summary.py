"""
Summary Tool: Generates clear, executive business insights from SQL query results.
"""
import pandas as pd
from backend.llm_client import call_llm


def format_value(val) -> str:
    """Helper to format numbers gracefully into currency or human-readable strings."""
    if isinstance(val, (int, float)):
        if abs(val) >= 1_000_000:
            return f"${val/1_000_000:,.2f}M" if isinstance(val, float) else f"{val:,.0f}"
        elif isinstance(val, float):
            return f"{val:,.2f}"
        else:
            return f"{val:,.0f}"
    return str(val)

def plain_text(text: str) -> str:
    """Strips markdown (headings, bold/italic markers) and normalizes bullets for readable plain text."""
    import re
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.MULTILINE)   # ### headings
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)                       # **bold**
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"\1", text)  # *italic*
    text = re.sub(r"^\s*[-*]\s+", "• ", text, flags=re.MULTILINE)       # - / * bullets
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()



def build_smart_summary(question: str, sql: str, df: pd.DataFrame) -> str:
    """
    Generates a clear, professional, multi-point executive business summary from DataFrame results
    when LLM is offline or unavailable.
    """
    if df.empty:
        return "No data returned matching your query parameters."

    total_rows = len(df)
    cols = df.columns.tolist()

    if total_rows == 1:
        row = df.iloc[0]
        details = [f"{col.replace('_', ' ').title()}: {format_value(row[col])}" for col in cols]
        return "\n".join(f"• {d}" for d in details)

    # Multi-row analysis
    num_cols = df.select_dtypes(include=['number']).columns.tolist()
    cat_cols = df.select_dtypes(include=['object', 'string', 'category']).columns.tolist()

    insights = []
    
    if cat_cols and num_cols:
        cat_col = cat_cols[0]
        num_col = num_cols[0]
        
        # Sort to find top item
        sorted_df = df.sort_values(by=num_col, ascending=False)
        top_row = sorted_df.iloc[0]
        top_name = top_row[cat_col]
        top_val = format_value(top_row[num_col])
        total_sum = sorted_df[num_col].sum()
        
        insights.append(f"**Top Leader**: **{top_name}** generated the highest **{num_col.replace('_', ' ')}** at **{top_val}**.")
        if total_sum > 0 and isinstance(top_row[num_col], (int, float)):
            pct = (top_row[num_col] / total_sum) * 100
            insights.append(f"**Share of Volume**: **{top_name}** represents **{pct:.1f}%** of the total top items.")
        insights.append(f"**Aggregate Total**: The combined **{num_col.replace('_', ' ')}** across all {total_rows} items in this view is **{format_value(total_sum)}**.")
    elif cat_cols:
        cat_col = cat_cols[0]
        top_item = df[cat_col].mode().iloc[0] if not df[cat_col].mode().empty else df[cat_col].iloc[0]
        sample_vals = ", ".join(str(v) for v in df[cat_col].drop_duplicates().head(5).tolist())
        insights.append(f"The result contains {total_rows} rows of {cat_col.replace('_', ' ')}.")
        insights.append(f"Sample values: {sample_vals}.")
    elif num_cols:
        num_col = num_cols[0]
        avg_val = format_value(df[num_col].mean())
        max_val = format_value(df[num_col].max())
        insights.append(f"**Average**: Average **{num_col.replace('_', ' ')}** across records is **{avg_val}**.")
        insights.append(f"**Peak Value**: Maximum recorded **{num_col.replace('_', ' ')}** is **{max_val}**.")
    else:
        insights.append(f"Successfully retrieved **{total_rows}** records for analysis.")

    return "\n".join(f"• {i}" for i in insights)


def build_analytics_summary(analytics_result: dict) -> str:
    """Builds a rich, bulleted executive narrative from analytics results."""
    analysis_type = analytics_result.get("analysis_type")

    if analysis_type == "forecast":
        metrics = analytics_result.get("metrics", {})
        direction = metrics.get("trend_direction", "Stable")
        val_col = analytics_result.get("value_column", "Metric").replace("_", " ").title()
        next_val = format_value(metrics.get("next_predicted_value", 0))
        fc = analytics_result.get("forecast", [])
        lower_b = format_value(fc[0]["lower_bound"]) if fc else "$0"
        upper_b = format_value(fc[0]["upper_bound"]) if fc else "$0"
        mae = format_value(metrics.get("mae", 0))

        insights = [
            f"**Projected Trend**: Model indicates an expected **{direction.lower()} trend** for **{val_col}** over the next **{analytics_result.get('horizon', 5)} periods**.",
            f"**Immediate Forecast**: Next period expected value is **{next_val}** (95% confidence interval: **{lower_b}** to **{upper_b}**).",
            f"**Model Accuracy**: Exponential smoothing fit achieved a Mean Absolute Error (MAE) of **{mae}**.",
        ]
        return "### 📈 Predictive Forecast Summary\n\n• " + "\n• ".join(insights)

    elif analysis_type == "correlation":
        primary = analytics_result.get("primary_relationship")
        top_pairs = analytics_result.get("top_pairs", [])
        sample_size = analytics_result.get("sample_size", 0)

        insights = []
        if primary:
            var1 = primary['var1'].replace('_', ' ').title()
            var2 = primary['var2'].replace('_', ' ').title()
            insights.append(
                f"**Leading Correlation**: **{var1}** and **{var2}** have a **{primary['strength'].lower()} {primary['direction'].lower()} correlation** (Pearson *r* = **{primary['pearson']:+.2f}**)."
            )
        if len(top_pairs) > 1:
            second = top_pairs[1]
            s1 = second['var1'].replace('_', ' ').title()
            s2 = second['var2'].replace('_', ' ').title()
            insights.append(
                f"**Secondary Relationship**: **{s1}** and **{s2}** show *r* = **{second['pearson']:+.2f}** ({second['strength'].lower()})."
            )
        insights.append(f"**Sample Scope**: Evaluated across **{sample_size}** observations and **{len(analytics_result.get('columns', []))}** numeric metrics.")
        return "### 🔗 Correlation Analysis Summary\n\n• " + "\n• ".join(insights)

    elif analysis_type == "outliers":
        col = analytics_result.get("column", "Metric").replace("_", " ").title()
        cnt = analytics_result.get("outlier_count", 0)
        pct = analytics_result.get("outlier_percentage", 0.0)
        bounds = analytics_result.get("bounds", {})
        outliers = analytics_result.get("outliers", [])

        insights = [
            f"**Anomaly Volume**: Identified **{cnt} outlier records** representing **{pct}%** of all entries for **{col}**.",
            f"**Expected Range**: Normal values fall between **{format_value(bounds.get('lower_bound', 0))}** and **{format_value(bounds.get('upper_bound', 0))}**.",
        ]
        if outliers:
            top_outlier = outliers[0]
            insights.append(f"**Most Extreme Anomaly**: **{top_outlier['label']}** recorded value **{format_value(top_outlier['value'])}** ({top_outlier['reason']}).")

        return "### 🚨 Outlier & Anomaly Detection Summary\n\n• " + "\n• ".join(insights)

    return ""


def generate_summary(
    question: str,
    sql: str,
    df: pd.DataFrame,
    analysis_type: str = None,
    analytics_result: dict = None
) -> str:
    """
    Given the user question, executed SQL, and result DataFrame,
    generates a clear, professional executive business summary.
    If analytics_result is present, synthesizes statistical findings.
    """
    if analytics_result and not analytics_result.get("error"):
        return plain_text(build_analytics_summary(analytics_result))

    if df.empty:
        return "No data returned for this query."

    sample_rows = df.head(10).to_string(index=False)

    system_instruction = (
        "You are a senior data analyst providing a clear, direct business summary.\n"
        "RULES:\n"
        "1. Directly answer the user's exact question using the actual data values shown.\n"
        "2. If the user asked 'what are the different X' or 'state X', LIST all unique values found in the data.\n"
        "3. If the user asked for top/bottom N, list those specific N rows with their values.\n"
        "4. Write in plain, simple English. Do NOT use markdown: no **, no #, no backticks.\n"
        "5. Use short sentences, or short lines starting with '• ' when listing. Be specific, not generic.\n"
        "6. Do NOT say 'the top leader is X' when asked for a list. Do NOT mention SQL, table names, or column names.\n"
        "7. Maximum 150 words."
    )

    prompt = (
        f"User Question: {question}\n"
        f"Query Result (first 15 rows):\n{df.head(15).to_string(index=False)}\n\n"
        f"Write a direct, specific business summary answering the question:"
    )

    try:
        summary = call_llm(prompt, system_instruction, timeout=30, optional=True)
        if summary and len(summary.strip()) > 10 and "SELECT *" not in summary:
            return plain_text(summary)
    except Exception:
        pass

    return plain_text(build_smart_summary(question, sql, df))

