"""
Automated Data Profiling and Quality Engine.
Analyzes ingested DuckDB datasets to compute schema metadata, column statistics, data quality score, and warning alerts.
"""
from typing import Dict, Any, List
import duckdb
from backend.ingestion import get_dataset_connection
from backend.models import ColumnProfile, TableProfile, ProfileResponse


def profile_table(conn: duckdb.DuckDBPyConnection, table_name: str) -> TableProfile:
    """
    Computes schema, column statistics, duplicate counts, quality score, and alerts for a table.
    """
    row_count_df = conn.execute(f'SELECT COUNT(*) as cnt FROM "{table_name}"').fetchdf()
    row_count = int(row_count_df["cnt"].iloc[0]) if not row_count_df.empty else 0

    columns_df = conn.execute(f'DESCRIBE "{table_name}"').fetchdf()
    col_names = columns_df["column_name"].tolist()
    col_types = columns_df["column_type"].tolist()
    column_count = len(col_names)

    # Calculate duplicate rows count
    duplicate_rows = 0
    if row_count > 1 and column_count > 0:
        try:
            col_list_str = ", ".join([f'"{c}"' for c in col_names])
            dedup_df = conn.execute(
                f'SELECT COUNT(*) as distinct_cnt FROM (SELECT DISTINCT {col_list_str} FROM "{table_name}")'
            ).fetchdf()
            distinct_rows = int(dedup_df["distinct_cnt"].iloc[0])
            duplicate_rows = max(0, row_count - distinct_rows)
        except Exception:
            duplicate_rows = 0

    columns_profile: List[ColumnProfile] = []
    table_warnings: List[str] = []
    total_cells = max(1, row_count * column_count)
    total_null_cells = 0

    if duplicate_rows > 0:
        dup_pct = round((duplicate_rows / max(1, row_count)) * 100, 1)
        table_warnings.append(
            f"⚠️ Table '{table_name}' contains {duplicate_rows} duplicate rows ({dup_pct}% of dataset)."
        )

    for col_name, col_type in zip(col_names, col_types):
        type_upper = str(col_type).upper()

        # Stats query
        try:
            stats_query = f'''
                SELECT 
                    COUNT(*) - COUNT("{col_name}") as null_cnt,
                    COUNT(DISTINCT "{col_name}") as distinct_cnt
                FROM "{table_name}"
            '''
            stats_res = conn.execute(stats_query).fetchdf()
            null_count = int(stats_res["null_cnt"].iloc[0])
            distinct_count = int(stats_res["distinct_cnt"].iloc[0])
        except Exception:
            null_count = 0
            distinct_count = 0

        total_null_cells += null_count
        null_pct = round((null_count / max(1, row_count)) * 100, 1) if row_count > 0 else 0.0

        # Candidate PK check
        is_candidate_pk = (distinct_count == row_count) and (null_count == 0) and (row_count > 1)

        # Datetime detection
        is_datetime = any(t in type_upper for t in ["DATE", "TIME", "TIMESTAMP"])
        if not is_datetime and any(k in col_name.lower() for k in ["date", "time", "year", "month", "created", "updated"]):
            is_datetime = True

        # Sample values
        sample_values: List[str] = []
        try:
            sample_df = conn.execute(
                f'SELECT DISTINCT "{col_name}" FROM "{table_name}" WHERE "{col_name}" IS NOT NULL LIMIT 3'
            ).fetchdf()
            sample_values = [str(val) for val in sample_df[col_name].tolist()]
        except Exception:
            pass

        # Numeric min, max, mean
        min_val, max_val, mean_val = None, None, None
        is_numeric = any(t in type_upper for t in ["INT", "DOUBLE", "FLOAT", "DECIMAL", "NUMERIC", "HUGEINT"])
        if is_numeric and row_count > 0:
            try:
                num_df = conn.execute(
                    f'SELECT MIN("{col_name}") as min_v, MAX("{col_name}") as max_v, AVG("{col_name}") as avg_v FROM "{table_name}"'
                ).fetchdf()
                if not num_df.empty:
                    min_val = str(num_df["min_v"].iloc[0]) if num_df["min_v"].iloc[0] is not None else None
                    max_val = str(num_df["max_v"].iloc[0]) if num_df["max_v"].iloc[0] is not None else None
                    avg_raw = num_df["avg_v"].iloc[0]
                    mean_val = round(float(avg_raw), 2) if avg_raw is not None else None
            except Exception:
                pass

        # Warnings for column issues
        if null_pct >= 10.0:
            table_warnings.append(
                f"⚠️ Column '{col_name}' has {null_pct}% missing values ({null_count} missing rows)."
            )
        elif null_count == row_count and row_count > 0:
            table_warnings.append(f"🚨 Column '{col_name}' is 100% empty (all NULLs).")

        if distinct_count == 1 and row_count > 1:
            table_warnings.append(f"⚠️ Column '{col_name}' has constant value (cardinality = 1).")

        columns_profile.append(
            ColumnProfile(
                name=col_name,
                data_type=col_type,
                null_count=null_count,
                null_percentage=null_pct,
                distinct_count=distinct_count,
                sample_values=sample_values,
                is_candidate_pk=is_candidate_pk,
                is_datetime=is_datetime,
                min_val=min_val,
                max_val=max_val,
                mean_val=mean_val,
            )
        )

    # Compute Table Quality Score (0 - 100)
    # Deductions:
    # Up to 35 points for missing values ratio
    missing_ratio = total_null_cells / total_cells
    missing_deduction = min(35.0, missing_ratio * 70.0)

    # Up to 25 points for duplicate row ratio
    dup_ratio = duplicate_rows / max(1, row_count)
    dup_deduction = min(25.0, dup_ratio * 50.0)

    # Up to 20 points for constant / empty columns
    empty_const_cols = sum(1 for c in columns_profile if c.distinct_count <= 1 and row_count > 1)
    col_deduction = min(20.0, (empty_const_cols / max(1, column_count)) * 40.0)

    quality_score = max(0.0, round(100.0 - missing_deduction - dup_deduction - col_deduction, 1))

    return TableProfile(
        table_name=table_name,
        row_count=row_count,
        column_count=column_count,
        duplicate_rows=duplicate_rows,
        columns=columns_profile,
        quality_score=quality_score,
        warnings=table_warnings,
    )


PROFILE_CACHE: Dict[str, ProfileResponse] = {}

def clear_profile_cache(dataset_id: str = None):
    """Clears cached profile for a dataset or all datasets."""
    if dataset_id:
        PROFILE_CACHE.pop(dataset_id, None)
    else:
        PROFILE_CACHE.clear()


def profile_dataset(dataset_id: str) -> ProfileResponse:
    """
    Profiles all tables for a registered dataset in DuckDB and aggregates quality metrics.
    Caches profiles in memory to prevent duplicate profiling during concurrent client requests.
    """
    if dataset_id in PROFILE_CACHE:
        return PROFILE_CACHE[dataset_id]

    conn = get_dataset_connection(dataset_id)
    tables_df = conn.execute("SHOW TABLES").fetchdf()

    table_names = []
    if not tables_df.empty:
        table_names = tables_df["name"].tolist()
    else:
        # Fallback to registered table names in DATASET_STORE if available
        try:
            from backend.ingestion import DATASET_STORE
            if dataset_id in DATASET_STORE and DATASET_STORE[dataset_id].get("tables"):
                table_names = DATASET_STORE[dataset_id]["tables"]
        except Exception:
            pass

    if not table_names:
        return ProfileResponse(
            dataset_id=dataset_id,
            overall_quality_score=100.0,
            tables=[],
            total_rows=0,
            total_columns=0,
            warnings=["No tables found in dataset."],
        )

    table_profiles: List[TableProfile] = []
    all_warnings: List[str] = []
    total_rows = 0
    total_columns = 0
    total_quality_points = 0.0

    for table_name in table_names:
        t_profile = profile_table(conn, table_name)
        table_profiles.append(t_profile)
        total_rows += t_profile.row_count
        total_columns += t_profile.column_count
        total_quality_points += t_profile.quality_score
        all_warnings.extend(t_profile.warnings)

    overall_score = round(total_quality_points / max(1, len(table_profiles)), 1)

    result = ProfileResponse(
        dataset_id=dataset_id,
        overall_quality_score=overall_score,
        tables=table_profiles,
        total_rows=total_rows,
        total_columns=total_columns,
        warnings=all_warnings,
    )
    PROFILE_CACHE[dataset_id] = result
    return result
