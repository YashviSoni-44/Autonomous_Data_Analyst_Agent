"""
Chart Generation Tool: Uses LLM or smart automated plotting to generate matplotlib visualizations from tabular SQL results.
"""
import base64
import io
import re
from typing import Optional
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from backend.llm_client import call_llm


def build_forecast_chart(analytics_result: dict) -> Optional[str]:
    """Renders time-series historical vs projected forecast with 95% confidence bounds."""
    hist = analytics_result.get("historical", [])
    fc = analytics_result.get("forecast", [])
    if not hist or not fc:
        return None

    val_col = analytics_result.get("value_column", "Value").replace("_", " ").title()
    date_col = analytics_result.get("date_column", "Date").replace("_", " ").title()

    fig, ax = plt.subplots(figsize=(8.5, 4.5), dpi=120)
    ax.set_facecolor('#0f172a')
    fig.patch.set_facecolor('#1e293b')

    # Plot historical using integer indices for robust categorical coordinate mapping
    hist_x = [str(h["date"]) for h in hist]
    hist_y = [float(h["actual"]) for h in hist]
    n_hist = len(hist)
    n_fc = len(fc)
    hist_indices = list(range(n_hist))
    fc_indices = [n_hist - 1] + [n_hist + i for i in range(n_fc)]
    all_x_labels = hist_x + [str(f["date"]) for f in fc]

    ax.plot(hist_indices, hist_y, marker='o', color='#38bdf8', linewidth=2.2, label='Historical Actuals')

    # Plot forecast starting from last historical point
    fc_y = [hist_y[-1]] + [float(f["predicted"]) for f in fc]
    lower_b = [hist_y[-1]] + [float(f["lower_bound"]) for f in fc]
    upper_b = [hist_y[-1]] + [float(f["upper_bound"]) for f in fc]

    ax.plot(fc_indices, fc_y, marker='D', color='#34d399', linestyle='--', linewidth=2.2, label='Forecast Projection')
    ax.fill_between(fc_indices, lower_b, upper_b, color='#34d399', alpha=0.22, label='95% Prediction Band')

    # Data label on final forecast point
    last_pred = fc[-1]["predicted"]
    ax.annotate(f"Final: {last_pred:,.2f}",
                xy=(fc_indices[-1], fc_y[-1]),
                xytext=(0, 8), textcoords="offset points",
                ha='center', va='bottom', color='#34d399', fontsize=9, fontweight='bold')

    direction = analytics_result.get("metrics", {}).get("trend_direction", "Forecast")
    mae = analytics_result.get("metrics", {}).get("mae", 0.0)
    ax.set_title(f"{val_col} Forecast (Trend: {direction} | MAE: {mae})", color='#f8fafc', fontsize=12, fontweight='bold', pad=12)
    ax.set_xlabel(date_col, color='#94a3b8', fontsize=10)
    ax.set_ylabel(val_col, color='#94a3b8', fontsize=10)
    ax.tick_params(colors='#94a3b8')
    ax.set_xticks(range(len(all_x_labels)))
    ax.set_xticklabels(all_x_labels, rotation=40, ha='right')

    for spine in ax.spines.values():
        spine.set_color('#334155')
    ax.grid(True, linestyle=':', alpha=0.35, color='#475569')
    ax.legend(facecolor='#0f172a', edgecolor='#334155', labelcolor='#e2e8f0', loc='best', fontsize=8.5)
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format="png", facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def build_correlation_chart(analytics_result: dict) -> Optional[str]:
    """Renders an executive correlation heatmap matrix."""
    matrix = analytics_result.get("pearson_matrix", {})
    cols = analytics_result.get("columns", [])
    if not matrix or len(cols) < 2:
        return None

    data = []
    for r in cols:
        data.append([matrix[r].get(c, 0.0) for c in cols])
    arr = pd.DataFrame(data, index=cols, columns=cols).to_numpy()

    fig, ax = plt.subplots(figsize=(7, 5), dpi=120)
    ax.set_facecolor('#0f172a')
    fig.patch.set_facecolor('#1e293b')

    cax = ax.imshow(arr, cmap='RdYlGn', vmin=-1.0, vmax=1.0, aspect='auto')
    cbar = fig.colorbar(cax, ax=ax, fraction=0.046, pad=0.04)
    cbar.ax.yaxis.set_tick_params(color='#94a3b8')
    plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='#94a3b8')

    clean_labels = [c.replace('_', ' ').title() for c in cols]
    ax.set_xticks(range(len(cols)))
    ax.set_yticks(range(len(cols)))
    ax.set_xticklabels(clean_labels, rotation=40, ha='right', color='#e2e8f0', fontsize=9)
    ax.set_yticklabels(clean_labels, color='#e2e8f0', fontsize=9)

    # Annotate correlation numbers
    for i in range(len(cols)):
        for j in range(len(cols)):
            val = arr[i, j]
            text_color = '#ffffff' if abs(val) > 0.45 else '#0f172a'
            ax.text(j, i, f"{val:+.2f}", ha='center', va='center', color=text_color, fontweight='bold', fontsize=9)

    ax.set_title("Correlation Matrix (Pearson r)", color='#f8fafc', fontsize=12, fontweight='bold', pad=12)
    for spine in ax.spines.values():
        spine.set_color('#334155')
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format="png", facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def build_outlier_chart(df: pd.DataFrame, analytics_result: dict) -> Optional[str]:
    """Renders a scatter/distribution chart highlighting anomalous outlier points."""
    col = analytics_result.get("column")
    if not col or col not in df.columns:
        return None

    bounds = analytics_result.get("bounds", {})
    lower_b = bounds.get("lower_bound")
    upper_b = bounds.get("upper_bound")
    outliers = analytics_result.get("outliers", [])
    outlier_rows = {o["row_index"] for o in outliers}

    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=120)
    ax.set_facecolor('#0f172a')
    fig.patch.set_facecolor('#1e293b')

    y_vals = df[col].dropna().values
    x_vals = range(len(y_vals))

    normal_x = [x for i, x in enumerate(x_vals) if i not in outlier_rows]
    normal_y = [y for i, y in enumerate(y_vals) if i not in outlier_rows]
    outlier_x = [x for i, x in enumerate(x_vals) if i in outlier_rows]
    outlier_y = [y for i, y in enumerate(y_vals) if i in outlier_rows]

    ax.scatter(normal_x, normal_y, color='#38bdf8', alpha=0.75, s=35, label='Normal Observations')
    if outlier_x:
        ax.scatter(outlier_x, outlier_y, color='#ef4444', edgecolor='#ffffff', s=65, label='Detected Outliers', zorder=5)

    if lower_b is not None:
        ax.axhline(lower_b, color='#f59e0b', linestyle='--', linewidth=1.5, label=f'Lower Bound ({lower_b:,.1f})')
    if upper_b is not None:
        ax.axhline(upper_b, color='#f59e0b', linestyle='--', linewidth=1.5, label=f'Upper Bound ({upper_b:,.1f})')

    ax.set_title(f"Outlier Detection for {col.replace('_', ' ').title()} ({len(outliers)} Anomalies)",
                 color='#f8fafc', fontsize=12, fontweight='bold', pad=12)
    ax.set_xlabel("Sample Index", color='#94a3b8', fontsize=10)
    ax.set_ylabel(col.replace('_', ' ').title(), color='#94a3b8', fontsize=10)
    ax.tick_params(colors='#94a3b8')

    for spine in ax.spines.values():
        spine.set_color('#334155')
    ax.grid(True, linestyle=':', alpha=0.35, color='#475569')
    ax.legend(facecolor='#0f172a', edgecolor='#334155', labelcolor='#e2e8f0', loc='best', fontsize=8.5)
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format="png", facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def build_auto_chart(question: str, df: pd.DataFrame) -> Optional[str]:
    """
    Automated fallback chart generator for pandas DataFrames when LLM is offline or unavailable.
    """
    if df.empty or len(df) < 2 or len(df.columns) < 2:
        return None

    num_cols = df.select_dtypes(include=['number']).columns.tolist()
    cat_cols = df.select_dtypes(include=['object', 'string', 'category']).columns.tolist()
    date_cols = [c for c in cat_cols if 'date' in c.lower() or 'time' in c.lower()]

    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=120)
    # Apply modern dark theme consistent with React UI
    ax.set_facecolor('#0f172a')
    fig.patch.set_facecolor('#1e293b')

    try:
        if date_cols and num_cols:
            x_col = date_cols[0]
            y_col = num_cols[0]
            ax.plot(df[x_col].astype(str), df[y_col], marker='o', color='#38bdf8', linewidth=2)
            ax.set_title(f"{y_col.replace('_', ' ').title()} Over Time", fontsize=12, fontweight='bold', pad=12, color='#f8fafc')
            ax.set_xlabel(x_col.replace('_', ' ').title(), fontsize=10, color='#94a3b8')
            ax.set_ylabel(y_col.replace('_', ' ').title(), fontsize=10, color='#94a3b8')
            plt.xticks(rotation=45, ha='right', color='#94a3b8')
            plt.yticks(color='#94a3b8')
        elif cat_cols and num_cols:
            x_col = cat_cols[0]
            y_col = num_cols[0]
            bars = ax.bar(df[x_col].astype(str), df[y_col], color='#6366f1', edgecolor='#818cf8', width=0.6)
            ax.set_title(f"{y_col.replace('_', ' ').title()} by {x_col.replace('_', ' ').title()}", fontsize=12, fontweight='bold', pad=12, color='#f8fafc')
            ax.set_xlabel(x_col.replace('_', ' ').title(), fontsize=10, color='#94a3b8')
            ax.set_ylabel(y_col.replace('_', ' ').title(), fontsize=10, color='#94a3b8')
            plt.xticks(rotation=45, ha='right', color='#94a3b8')
            plt.yticks(color='#94a3b8')
            for bar in bars:
                height = bar.get_height()
                ax.annotate(f"{height:,.0f}" if isinstance(height, int) or height.is_integer() else f"{height:,.2f}",
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3), textcoords="offset points",
                            ha='center', va='bottom', fontsize=8, fontweight='bold', color='#e2e8f0')
        else:
            plt.close(fig)
            return None

        ax.grid(True, linestyle=':', alpha=0.35, color='#475569', axis='y')
        for spine in ax.spines.values():
            spine.set_color('#334155')
        plt.tight_layout()

        buffer = io.BytesIO()
        plt.savefig(buffer, format="png", facecolor=fig.get_facecolor(), edgecolor='none')
        plt.close(fig)
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode("utf-8")
    except Exception as err:
        plt.close("all")
        print(f"Auto chart error: {err}")
        return None


def generate_chart(
    question: str,
    df: pd.DataFrame,
    analysis_type: Optional[str] = None,
    analytics_result: Optional[dict] = None
) -> Optional[str]:
    """
    Given user question and result dataframe, generates Matplotlib visualization.
    If analytics_result is provided, renders specialized forecast, correlation, or outlier visual.
    Falls back to automated chart generation if LLM call fails.
    """
    if analytics_result and not analytics_result.get("error"):
        if analysis_type == "forecast" or analytics_result.get("analysis_type") == "forecast":
            chart = build_forecast_chart(analytics_result)
            if chart:
                return chart
        elif analysis_type == "correlation" or analytics_result.get("analysis_type") == "correlation":
            chart = build_correlation_chart(analytics_result)
            if chart:
                return chart
        elif analysis_type == "outliers" or analytics_result.get("analysis_type") == "outliers":
            chart = build_outlier_chart(df, analytics_result)
            if chart:
                return chart

    if df.empty or len(df) < 2:
        return None

    sample_data = df.head(10).to_string(index=False)
    columns_info = list(df.columns)

    system_instruction = (
        "You are a Matplotlib Python chart generator. Given a pandas DataFrame `df` and user question, "
        "write Python code using `ax` (an existing Matplotlib Axes object) or `plt` to create a clean bar, line, or pie chart.\n"
        "Rules:\n"
        "1. Output ONLY Python code inside ```python ... ``` block.\n"
        "2. `df`, `fig`, `ax`, `plt` are already defined.\n"
        "3. Use `ax.set_title()`, `ax.set_xlabel()`, `ax.set_ylabel()`, `plt.xticks(rotation=45)` as appropriate.\n"
        "4. If no chart is appropriate (e.g. single number result), output strictly: NO_CHART"
    )

    prompt = (
        f"User Question: {question}\n"
        f"Columns: {columns_info}\n"
        f"Sample Data:\n{sample_data}\n\n"
        f"Python Plot Code:"
    )

    try:
        response = call_llm(prompt, system_instruction, timeout=20, optional=True).strip()
        
        if "NO_CHART" in response or not response:
            return None

        py_code = response.strip()
        match = re.search(r"```(?:python)?\s*(.*?)\s*```", py_code, re.DOTALL | re.IGNORECASE)
        if match:
            py_code = match.group(1).strip()
        elif py_code.startswith("```"):
            py_code = re.sub(r"^```[a-zA-Z]*\n?", "", py_code)
            py_code = re.sub(r"\n?```$", "", py_code).strip()

        fig, ax = plt.subplots(figsize=(8, 4.5), dpi=120)
        exec_globals = {
            "df": df.copy(),
            "plt": plt,
            "fig": fig,
            "ax": ax
        }

        exec(py_code, exec_globals)
        plt.tight_layout()
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format="png")
        plt.close(fig)
        buffer.seek(0)
        
        return base64.b64encode(buffer.read()).decode("utf-8")
    except Exception:
        plt.close("all")
        return build_auto_chart(question, df)

