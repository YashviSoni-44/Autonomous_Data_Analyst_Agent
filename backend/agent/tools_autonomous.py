"""
Autonomous Dataset Investigation Engine for the Autonomous Data Analyst Agent.
Phase 5.2: Zero-prompt dataset analysis, hypothesis formulation, anomaly scans,
correlation discoveries, and executive intelligence reporting.
"""
from typing import Dict, Any, List, Optional
import io
import base64
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from backend.ingestion import get_dataset_connection
from backend.profiling import profile_dataset
from backend.agent.tools_analytics import run_correlation_analysis, detect_outliers
from backend.llm_client import call_llm


AUTONOMOUS_CACHE: Dict[str, Dict[str, Any]] = {}


def clear_autonomous_cache(dataset_id: Optional[str] = None):
    """Clears the cached autonomous report for a dataset or all datasets."""
    if dataset_id:
        AUTONOMOUS_CACHE.pop(dataset_id, None)
    else:
        AUTONOMOUS_CACHE.clear()


def run_autonomous_dataset_investigation(dataset_id: str, force: bool = False) -> Dict[str, Any]:
    """
    Autonomously investigates an ingested dataset without requiring a user prompt.
    Synthesizes KPIs, dimensional drivers, outliers, correlations, and strategic recommendations.
    Caches results per dataset_id unless force=True.
    """
    if not force and dataset_id in AUTONOMOUS_CACHE:
        return AUTONOMOUS_CACHE[dataset_id]

    conn = get_dataset_connection(dataset_id)
    profile = profile_dataset(dataset_id)

    if not profile.tables:
        from backend.ingestion import DATASET_STORE
        store_tables = DATASET_STORE.get(dataset_id, {}).get("tables", [])
        if store_tables:
            # Re-profile once more now that store is synchronized
            from backend.profiling import clear_profile_cache
            clear_profile_cache(dataset_id)
            profile = profile_dataset(dataset_id)

    if not profile.tables:
        raise ValueError(f"No tables found for dataset {dataset_id}")

    # Use the primary table (largest by row count)
    primary_table_profile = max(profile.tables, key=lambda t: t.row_count)
    table_name = primary_table_profile.table_name

    # Load full dataset into pandas dataframe via DuckDB
    df = conn.execute(f'SELECT * FROM "{table_name}"').fetchdf()
    if df.empty:
        raise ValueError(f"Table '{table_name}' contains no records.")

    # Robust column detection across DuckDB data type variations
    num_cols: List[str] = [
        c.name for c in primary_table_profile.columns
        if any(t in str(c.data_type).upper() for t in ["INT", "DOUBLE", "FLOAT", "DECIMAL", "NUMERIC", "REAL", "HUGEINT"])
    ]
    cat_cols: List[str] = [
        c.name for c in primary_table_profile.columns
        if any(t in str(c.data_type).upper() for t in ["VARCHAR", "TEXT", "STRING", "CHAR"]) and not c.is_candidate_pk
    ]
    date_cols: List[str] = [c.name for c in primary_table_profile.columns if c.is_datetime]

    # Fallback column detection if profile types are generic
    if not num_cols:
        num_cols = list(df.select_dtypes(include=[np.number]).columns)
    if not cat_cols:
        cat_cols = [c for c in df.select_dtypes(include=["object", "category"]).columns if df[c].nunique() < len(df) * 0.9]

    # Clean numeric columns to avoid dtype conflicts
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # --- 1. Compute High-Level Business KPIs ---
    kpis: List[Dict[str, str]] = [
        {"label": "Total Records", "value": f"{len(df):,}", "subtext": f"Across {len(df.columns)} dimensions"}
    ]

    primary_num: Optional[str] = num_cols[0] if num_cols else None

    if primary_num and primary_num in df.columns:
        col_sum = float(df[primary_num].dropna().sum())
        col_avg = float(df[primary_num].dropna().mean()) if len(df[primary_num].dropna()) > 0 else 0.0
        col_max = float(df[primary_num].dropna().max()) if len(df[primary_num].dropna()) > 0 else 0.0
        is_currency = any(term in primary_num.lower() for term in ["sale", "price", "amount", "revenue", "cost", "profit"])
        prefix = "$" if is_currency else ""

        kpis.append({
            "label": f"Total {primary_num.replace('_', ' ').title()}",
            "value": f"{prefix}{col_sum:,.2f}" if is_currency else f"{col_sum:,.1f}",
            "subtext": f"Avg: {prefix}{col_avg:,.2f}"
        })
        kpis.append({
            "label": f"Peak {primary_num.replace('_', ' ').title()}",
            "value": f"{prefix}{col_max:,.2f}" if is_currency else f"{col_max:,.1f}",
            "subtext": "Maximum individual record"
        })

    if cat_cols:
        primary_cat = cat_cols[0]
        unique_cnt = df[primary_cat].nunique()
        kpis.append({
            "label": f"Active {primary_cat.replace('_', ' ').title()}s",
            "value": str(unique_cnt),
            "subtext": "Distinct segments in data"
        })

    # --- 2. Top Dimensional Findings (Pareto Breakdown) ---
    top_findings: List[str] = []
    if primary_num and cat_cols:
        primary_cat = cat_cols[0]
        cat_agg = df.groupby(primary_cat)[primary_num].agg(["sum", "count"]).reset_index()
        cat_agg = cat_agg.sort_values(by="sum", ascending=False)
        total_val = float(cat_agg["sum"].sum())

        if len(cat_agg) > 0:
            top_row = cat_agg.iloc[0]
            top_share = (float(top_row["sum"]) / total_val * 100) if total_val > 0 else 0.0
            top_findings.append(
                f"Dominant Segment: '{top_row[primary_cat]}' accounts for {top_share:.1f}% of total {primary_num} "
                f"({int(top_row['count'])} transactions)."
            )

        if len(cat_agg) >= 3:
            top_3_share = (float(cat_agg.head(3)["sum"].sum()) / total_val * 100) if total_val > 0 else 0.0
            top_findings.append(
                f"Concentration Risk: Top 3 segments ({', '.join(cat_agg.head(3)[primary_cat].astype(str))}) "
                f"generate {top_3_share:.1f}% of aggregate {primary_num}."
            )

    # --- 3. Outlier and Anomaly Scan ---
    anomalies_detected: List[Dict[str, Any]] = []
    if primary_num:
        outlier_res = detect_outliers(df, num_col=primary_num, method="iqr")
        outlier_cnt = int(outlier_res.get("outlier_count", 0))
        pct = float(outlier_res.get("outlier_percentage", 0.0))
        bounds = outlier_res.get("bounds", {})

        anomalies_detected.append({
            "column": primary_num,
            "outlier_count": outlier_cnt,
            "outlier_percentage": pct,
            "lower_bound": bounds.get("lower_bound"),
            "upper_bound": bounds.get("upper_bound"),
            "severity": "High" if pct > 5.0 else ("Medium" if pct > 1.0 else "Low"),
            "details": f"{outlier_cnt} records ({pct}%) fall outside typical operating range [{bounds.get('lower_bound')} to {bounds.get('upper_bound')}]."
        })

        if outlier_cnt > 0:
            top_findings.append(
                f"Anomaly Warning: {outlier_cnt} extreme transactions ({pct}% of dataset) detected in '{primary_num}' requiring audit."
            )

    # --- 4. Correlation Discoveries ---
    correlations_list: List[Dict[str, Any]] = []
    if len(num_cols) >= 2:
        corr_res = run_correlation_analysis(df, target_cols=num_cols)
        top_pairs = corr_res.get("top_pairs", [])
        for p in top_pairs[:3]:
            correlations_list.append({
                "var1": str(p["var1"]),
                "var2": str(p["var2"]),
                "pearson": round(float(p["pearson"]), 2),
                "strength": str(p["strength"]),
                "direction": str(p["direction"])
            })
            if p.get("abs_pearson", 0.0) >= 0.6:
                top_findings.append(
                    f"Strong Association: {p['strength']} {str(p['direction']).lower()} correlation (r = {p['pearson']:.2f}) "
                    f"observed between '{p['var1']}' and '{p['var2']}'."
                )

    if not top_findings:
        top_findings.append(f"Successfully indexed and profiled {len(df)} records across {len(df.columns)} features.")

    # --- 5. Generate Multi-Dimensional Overview Visual ---
    chart_base64: Optional[str] = None
    fig = None
    try:
        fig, ax = plt.subplots(figsize=(9, 4.5), facecolor="#141923")
        ax.set_facecolor("#181f2e")

        if primary_num and cat_cols:
            primary_cat = cat_cols[0]
            top_cats = df.groupby(primary_cat)[primary_num].sum().sort_values(ascending=False).head(7)
            bars = ax.bar(top_cats.index.astype(str), top_cats.values, color="#38bdf8", edgecolor="#0ea5e9", width=0.55)
            ax.set_title(f"Autonomous Breakdown: {primary_num.title()} by Top {primary_cat.title()}", color="#f1f5f9", fontsize=13, fontweight="bold", pad=12)
            ax.set_xlabel(primary_cat.title(), color="#94a3b8", fontsize=10)
            ax.set_ylabel(primary_num.title(), color="#94a3b8", fontsize=10)
            ax.tick_params(colors="#94a3b8", labelsize=9)
            plt.xticks(rotation=25, ha="right")
            for bar in bars:
                height = bar.get_height()
                ax.annotate(f"{height:,.0f}",
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3), textcoords="offset points",
                            ha="center", va="bottom", color="#e2e8f0", fontsize=8, fontweight="bold")
        elif primary_num:
            ax.hist(df[primary_num].dropna(), bins=15, color="#10b981", edgecolor="#059669", alpha=0.85)
            ax.set_title(f"Autonomous Distribution: {primary_num.title()}", color="#f1f5f9", fontsize=13, fontweight="bold", pad=12)
            ax.tick_params(colors="#94a3b8", labelsize=9)

        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_color("#334155")
        ax.spines["left"].set_color("#334155")
        ax.grid(axis="y", linestyle="--", alpha=0.15, color="#ffffff")

        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="png", dpi=130, facecolor=fig.get_facecolor(), bbox_inches="tight")
        buf.seek(0)
        chart_base64 = base64.b64encode(buf.read()).decode("utf-8")
    except Exception:
        chart_base64 = None
    finally:
        if fig is not None:
            plt.close(fig)

    # --- 6. Formulate Strategic Follow-Up Questions ---
    recommended_actions: List[str] = []
    if primary_num and cat_cols:
        recommended_actions.append(f"What are the quarterly growth trends for the top {cat_cols[0]}s in {primary_num}?")
    if primary_num and len(num_cols) >= 2:
        recommended_actions.append(f"Break down the correlation between {num_cols[0]} and {num_cols[1]} by region.")
    if anomalies_detected and anomalies_detected[0]["outlier_count"] > 0:
        recommended_actions.append(f"Isolate and examine the top 5 highest outlier transactions in {primary_num}.")
    if date_cols and primary_num:
        recommended_actions.append(f"Forecast {primary_num} for the next 6 periods using historical seasonality.")
    if len(recommended_actions) < 3:
        recommended_actions.append("Compare average values across secondary categorical segments.")

    # --- 7. Executive Narrative Generation ---
    system_prompt = (
        "You are an elite Principal Business Intelligence Partner. "
        "Synthesize the provided autonomous analytical findings into a crisp, authoritative executive briefing (3 concise paragraphs). "
        "Highlight key business drivers, risks/anomalies, and clear strategic takeaways. Do not invent numbers not present in the data."
    )
    user_prompt = (
        f"Dataset: {table_name} ({len(df)} records, {len(df.columns)} columns)\n"
        f"Key KPIs: {kpis}\n"
        f"Top Findings: {top_findings}\n"
        f"Anomalies: {anomalies_detected}\n"
        f"Correlations: {correlations_list}\n\n"
        "Generate executive briefing:"
    )

    executive_summary = ""
    try:
        res = call_llm(prompt=user_prompt, system_instruction=system_prompt)
        if res and len(res.strip()) > 30:
            executive_summary = res.strip()
    except Exception:
        pass

    if not executive_summary:
        top_driver_str = top_findings[0] if top_findings else f"Evaluated {len(df)} records."
        anomaly_str = f"Found {anomalies_detected[0]['outlier_count']} outliers in {primary_num}." if (anomalies_detected and anomalies_detected[0]['outlier_count'] > 0) else "No severe distributional anomalies detected."
        executive_summary = (
            f"Autonomous investigation of table '{table_name}' ({len(df):,} records) reveals strong operational concentration. "
            f"{top_driver_str} "
            f"Data quality health and risk scanning indicates: {anomaly_str} "
            f"Recommended strategic focus centers on continuous performance tracking across primary drivers."
        )

    report = {
        "dataset_id": dataset_id,
        "table_name": table_name,
        "executive_summary": executive_summary,
        "kpi_metrics": kpis,
        "top_findings": top_findings,
        "anomalies_detected": anomalies_detected,
        "correlations": correlations_list,
        "chart_base64": chart_base64,
        "recommended_actions": recommended_actions,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    AUTONOMOUS_CACHE[dataset_id] = report
    return report
