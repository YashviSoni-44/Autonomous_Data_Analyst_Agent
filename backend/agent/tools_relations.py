"""
Multi-table relationship inference engine.
Scans all tables in a DuckDB connection and detects likely foreign-key join relationships
based on shared column name patterns, then enriches the schema string with join hints.
"""
from typing import List, Dict, Tuple
import duckdb
import re


def _get_table_columns(conn: duckdb.DuckDBPyConnection) -> Dict[str, List[str]]:
    """Returns {table_name: [col1, col2, ...]} for all tables in the connection."""
    tables_df = conn.execute("SHOW TABLES").fetchdf()
    table_cols = {}
    for tname in tables_df["name"]:
        cols_df = conn.execute(f'DESCRIBE "{tname}"').fetchdf()
        table_cols[tname] = cols_df["column_name"].tolist()
    return table_cols


def _normalize(col_name: str) -> str:
    """Lowercase + strip common suffixes for fuzzy matching."""
    return re.sub(r"(s|_id|id|_key|key|_fk|_pk)$", "", col_name.lower().strip())


def infer_table_relationships(conn: duckdb.DuckDBPyConnection) -> List[Dict]:
    """
    Detects likely join paths between tables by comparing normalized column names.
    Returns a list of dicts: {left_table, left_col, right_table, right_col, confidence}
    """
    table_cols = _get_table_columns(conn)
    table_names = list(table_cols.keys())
    relationships = []

    if len(table_names) < 2:
        return []

    for i, t1 in enumerate(table_names):
        for t2 in table_names[i + 1:]:
            for c1 in table_cols[t1]:
                for c2 in table_cols[t2]:
                    # Exact match
                    if c1.lower() == c2.lower():
                        relationships.append({
                            "left_table": t1, "left_col": c1,
                            "right_table": t2, "right_col": c2,
                            "confidence": "HIGH"
                        })
                    # Normalized suffix match (e.g. customer_id vs customer_key)
                    elif _normalize(c1) == _normalize(c2) and len(_normalize(c1)) > 2:
                        relationships.append({
                            "left_table": t1, "left_col": c1,
                            "right_table": t2, "right_col": c2,
                            "confidence": "MEDIUM"
                        })
    return relationships


def build_join_hints(conn: duckdb.DuckDBPyConnection) -> str:
    """
    Returns a formatted string of discovered JOIN relationships to include in LLM prompts.
    """
    rels = infer_table_relationships(conn)
    if not rels:
        return ""

    lines = ["\n--- Detected Table Relationships (Use for JOINs) ---"]
    for r in rels:
        lines.append(
            f"  [{r['confidence']}] {r['left_table']}.{r['left_col']} "
            f"JOIN {r['right_table']}.{r['right_col']}"
        )
    return "\n".join(lines) + "\n"
