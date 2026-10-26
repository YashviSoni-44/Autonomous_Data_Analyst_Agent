"""
Advanced Analytics Engine (Phase 4):
Provides statistical analysis (Pearson/Spearman correlations),
outlier detection (IQR and Z-score methods),
and time-series forecasting (Holt-Winters Exponential Smoothing and AR trend).
"""
import re
from typing import Optional, List, Dict, Any
import numpy as np
import pandas as pd


def detect_analysis_intent(question: str, plan: Optional[dict] = None) -> str:
    """
    Classifies user question and analysis plan into an analytical intent:
    - 'forecast': future projections, time series forecasting
    - 'correlation': relationship testing, correlation matrices
    - 'outliers': anomaly and extreme value detection
    - 'sql': standard query/aggregation (default)
    """
    q = question.lower()
    plan_text = ""
    if plan and isinstance(plan, dict):
        plan_text = (
            str(plan.get("intent", "")) + " " +
            " ".join(plan.get("operations", [])) + " " +
            " ".join(plan.get("steps", []))
        ).lower()

    combined = f"{q} {plan_text}"

    # Check for forecasting / predictive intent
    forecast_keywords = [
        "forecast", "predict", "projection", "projected", "future trend",
        "next month", "next quarter", "next year", "future sales", "next 30 days",
        "next 6 months", "next 12 months", "extrapolate", "expected trend"
    ]
    if any(k in combined for k in forecast_keywords):
        return "forecast"

    # Check for correlation / relationship intent
    correlation_stems = [
        "correlation", "correlate", "correlates", "correlated", "correlating",
        "relationship between", "relationships between", "covariance", "dependency between",
        "co-relation", "associated with"
    ]
    if any(stem in combined for stem in correlation_stems) or ("relate" in combined and "to" in combined):
        return "correlation"

    # Check for outlier / anomaly intent
    outlier_keywords = [
        "outlier", "outliers", "anomaly", "anomalies", "abnormal", "unusual",
        "extreme value", "extreme values", "irregular", "deviant", "spikes"
    ]
    if any(k in combined for k in outlier_keywords):
        return "outliers"

    return "sql"


# ─────────────────────────────────────────────────────────────────────────────
# 1. Statistical Analysis (Correlation Engine)
# ─────────────────────────────────────────────────────────────────────────────

def run_correlation_analysis(df: pd.DataFrame, target_cols: Optional[List[str]] = None) -> dict:
    """
    Computes Pearson and Spearman correlation matrices across numerical columns.
    Identifies and ranks top correlated variable pairs.
    """
    if df.empty:
        return {"error": "DataFrame is empty, cannot compute correlations."}

    num_df = df.select_dtypes(include=[np.number])
    if target_cols:
        valid_cols = [c for c in target_cols if c in num_df.columns]
        if len(valid_cols) >= 2:
            num_df = num_df[valid_cols]

    if num_df.shape[1] < 2:
        return {
            "error": "At least 2 numerical columns are required to compute correlations.",
            "available_numeric_columns": list(num_df.columns)
        }

    # Drop constant columns (std == 0)
    non_constant_cols = [col for col in num_df.columns if num_df[col].std(skipna=True) > 1e-9]
    if len(non_constant_cols) < 2:
        return {"error": "Insufficient numerical variance to compute meaningful correlation."}

    num_df = num_df[non_constant_cols].dropna()
    if len(num_df) < 3:
        return {"error": "At least 3 complete data rows are required for correlation analysis."}

    pearson_corr = num_df.corr(method="pearson").round(3)
    spearman_corr = num_df.corr(method="spearman").round(3)

    # Extract non-redundant pairs
    pairs = []
    cols = list(num_df.columns)
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            col1 = cols[i]
            col2 = cols[j]
            p_val = float(pearson_corr.loc[col1, col2])
            s_val = float(spearman_corr.loc[col1, col2])

            abs_val = abs(p_val)
            if abs_val >= 0.7:
                strength = "Strong"
            elif abs_val >= 0.4:
                strength = "Moderate"
            else:
                strength = "Weak"

            direction = "Positive" if p_val >= 0 else "Negative"

            pairs.append({
                "var1": col1,
                "var2": col2,
                "pearson": p_val,
                "spearman": s_val,
                "strength": strength,
                "direction": direction,
                "abs_pearson": abs_val
            })

    pairs.sort(key=lambda x: x["abs_pearson"], reverse=True)

    return {
        "analysis_type": "correlation",
        "columns": cols,
        "sample_size": len(num_df),
        "pearson_matrix": pearson_corr.to_dict(),
        "spearman_matrix": spearman_corr.to_dict(),
        "top_pairs": pairs[:5],
        "primary_relationship": pairs[0] if pairs else None
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. Outlier & Anomaly Detection (IQR & Z-Score)
# ─────────────────────────────────────────────────────────────────────────────

def detect_outliers(df: pd.DataFrame, num_col: Optional[str] = None, method: str = "iqr") -> dict:
    """
    Detects outliers in the DataFrame using IQR or Z-score methodologies.
    Returns anomaly records, bounds, and impact statistics.
    """
    if df.empty:
        return {"error": "DataFrame is empty, cannot perform outlier detection."}

    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not num_cols:
        return {"error": "No numerical columns found in result to detect outliers."}

    target_col = num_col if (num_col and num_col in num_cols) else num_cols[0]
    series = df[target_col].dropna()

    if len(series) < 4:
        return {"error": "Insufficient rows (need >= 4) to perform robust outlier detection."}

    q1 = float(series.quantile(0.25))
    q3 = float(series.quantile(0.75))
    iqr = q3 - q1
    lower_iqr = q1 - 1.5 * iqr
    upper_iqr = q3 + 1.5 * iqr

    mean_val = float(series.mean())
    std_val = float(series.std()) if float(series.std()) > 1e-9 else 1.0

    outlier_indices = []
    outlier_records = []

    for idx, row in df.iterrows():
        val = row[target_col]
        if pd.isna(val):
            continue

        is_outlier = False
        reason = ""
        z_score = round((val - mean_val) / std_val, 2)

        if method == "iqr":
            if val < lower_iqr:
                is_outlier = True
                reason = f"Below IQR lower bound ({round(lower_iqr, 2)})"
            elif val > upper_iqr:
                is_outlier = True
                reason = f"Above IQR upper bound ({round(upper_iqr, 2)})"
        else: # zscore
            if abs(z_score) > 3.0:
                is_outlier = True
                reason = f"Z-Score ({z_score}) exceeded 3.0"

        if is_outlier:
            outlier_indices.append(idx)
            # Find an identifier column (string / category / id)
            id_col = None
            for c in df.columns:
                if c != target_col:
                    id_col = c
                    break

            label = f"{id_col}={row[id_col]}" if id_col else f"Row {idx}"
            outlier_records.append({
                "row_index": int(idx),
                "label": str(label),
                "value": float(val),
                "z_score": z_score,
                "reason": reason
            })

    outlier_percentage = round((len(outlier_records) / len(df)) * 100, 1)

    return {
        "analysis_type": "outliers",
        "method": method.upper(),
        "column": target_col,
        "total_rows": len(df),
        "outlier_count": len(outlier_records),
        "outlier_percentage": outlier_percentage,
        "bounds": {
            "q1": round(q1, 2),
            "q3": round(q3, 2),
            "iqr": round(iqr, 2),
            "lower_bound": round(lower_iqr, 2),
            "upper_bound": round(upper_iqr, 2),
            "mean": round(mean_val, 2),
            "std": round(std_val, 2),
        },
        "outliers": outlier_records[:20]  # Cap to top 20 for preview
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. Time-Series Forecasting (Holt-Winters Exponential Smoothing & AR Trend)
# ─────────────────────────────────────────────────────────────────────────────

def _infer_date_and_val_columns(df: pd.DataFrame) -> tuple[Optional[str], Optional[str]]:
    """Identifies candidate date/time column and candidate numeric value column."""
    date_col = None
    val_col = None

    for col in df.columns:
        col_lower = col.lower()
        if any(term in col_lower for term in ["date", "time", "month", "year", "day", "quarter", "period"]):
            date_col = col
            break

    if not date_col:
        for col in df.columns:
            if df[col].dtype == "object" or pd.api.types.is_datetime64_any_dtype(df[col]):
                try:
                    pd.to_datetime(df[col], errors="raise")
                    date_col = col
                    break
                except Exception:
                    continue

    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if num_cols:
        val_candidates = [c for c in num_cols if c != date_col]
        val_col = val_candidates[0] if val_candidates else num_cols[0]

    return date_col, val_col


def run_time_series_forecast(
    df: pd.DataFrame,
    date_col: Optional[str] = None,
    val_col: Optional[str] = None,
    horizon: int = 5
) -> dict:
    """
    Performs time-series forecasting using Holt's Linear Exponential Smoothing.
    Computes model accuracy (MAE, RMSE) and upper/lower 95% confidence bounds.
    """
    if df.empty:
        return {"error": "DataFrame is empty, cannot compute forecast."}

    if not date_col or not val_col:
        inferred_date, inferred_val = _infer_date_and_val_columns(df)
        date_col = date_col or inferred_date
        val_col = val_col or inferred_val

    if not date_col or not val_col:
        return {
            "error": "Forecasting requires a date/time column and a numerical metric column.",
            "detected_columns": list(df.columns)
        }

    # Prepare and sort data
    ts_df = df[[date_col, val_col]].dropna().copy()
    try:
        ts_df["dt_parsed"] = pd.to_datetime(ts_df[date_col])
        ts_df = ts_df.sort_values(by="dt_parsed")
    except Exception:
        ts_df = ts_df.sort_values(by=date_col)

    # Group by date if there are duplicate timestamps
    aggregated = ts_df.groupby(date_col, as_index=False, sort=False)[val_col].sum()
    y = aggregated[val_col].to_numpy(dtype=float)
    dates = aggregated[date_col].astype(str).tolist()
    n = len(y)

    if n < 4:
        return {
            "error": f"Forecasting requires at least 4 historical data points (found {n}).",
            "points_count": n
        }

    # Holt's Linear Exponential Smoothing
    # Level (alpha) and Trend (beta)
    alpha = 0.35
    beta = 0.15

    level = np.zeros(n)
    trend = np.zeros(n)
    fitted = np.zeros(n)

    level[0] = y[0]
    trend[0] = y[1] - y[0] if n > 1 else 0.0
    fitted[0] = y[0]

    for t in range(1, n):
        fitted[t] = level[t - 1] + trend[t - 1]
        level[t] = alpha * y[t] + (1 - alpha) * (level[t - 1] + trend[t - 1])
        trend[t] = beta * (level[t] - level[t - 1]) + (1 - beta) * trend[t - 1]

    # Residuals and accuracy metrics
    residuals = y[1:] - fitted[1:]
    mae = float(np.mean(np.abs(residuals))) if len(residuals) > 0 else 0.0
    rmse = float(np.sqrt(np.mean(residuals ** 2))) if len(residuals) > 0 else 0.0
    se = rmse if rmse > 1e-6 else float(np.std(y) * 0.1)

    # Historical series
    historical_points = []
    for i in range(n):
        historical_points.append({
            "date": dates[i],
            "actual": round(float(y[i]), 2),
            "fitted": round(float(fitted[i]), 2)
        })

    # Generate future horizon points
    forecast_points = []
    last_level = level[-1]
    last_trend = trend[-1]

    for h in range(1, horizon + 1):
        pred_val = last_level + h * last_trend
        # Margin of error increases with horizon step h
        margin = 1.96 * se * np.sqrt(1.0 + (h / max(n, 1)))
        lower_b = max(0.0, pred_val - margin)  # Floor at 0 for business metrics like revenue
        upper_b = pred_val + margin

        future_label = f"Period +{h}"
        forecast_points.append({
            "date": future_label,
            "predicted": round(float(pred_val), 2),
            "lower_bound": round(float(lower_b), 2),
            "upper_bound": round(float(upper_b), 2)
        })

    next_period_prediction = forecast_points[0]["predicted"] if forecast_points else 0.0
    trend_direction = "Growth" if last_trend > 0 else ("Decline" if last_trend < 0 else "Flat")

    return {
        "analysis_type": "forecast",
        "date_column": date_col,
        "value_column": val_col,
        "horizon": horizon,
        "historical": historical_points,
        "forecast": forecast_points,
        "metrics": {
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "trend_direction": trend_direction,
            "average_trend_rate": round(float(last_trend), 2),
            "next_predicted_value": next_period_prediction
        }
    }
