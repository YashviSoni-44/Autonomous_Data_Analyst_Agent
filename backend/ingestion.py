"""
Ingestion layer: Converts CSV, Excel, or Postgres data into DuckDB tables and extracts schema.
"""
import os
import duckdb
import pandas as pd
import uuid

# Storage directory for active DuckDB sessions or uploads
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
DATASET_STORE = {}

def get_db_path(dataset_id: str) -> str:
    return os.path.join(UPLOAD_DIR, f"{dataset_id}.duckdb")

def load_file_into_duckdb(file_path: str, dataset_id: str = None) -> tuple[str, list[str]]:
    """
    Loads CSV or Excel into a persistent DuckDB connection stored in DATASET_STORE and disk.
    Returns (dataset_id, list of table names created).
    """
    if not dataset_id:
        dataset_id = str(uuid.uuid4())[:8]

    db_path = get_db_path(dataset_id)
    # If existing DB file exists, close old connection if open
    if dataset_id in DATASET_STORE:
        try:
            DATASET_STORE[dataset_id]["conn"].close()
        except Exception:
            pass

    conn = duckdb.connect(database=db_path)
    table_names = []

    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == ".csv":
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        table_name = "".join(c if c.isalnum() else "_" for c in base_name).lower()
        if not table_name or not table_name[0].isalpha():
            table_name = f"tbl_{table_name}"
        
        conn.execute(f'CREATE OR REPLACE TABLE "{table_name}" AS SELECT * FROM read_csv_auto(?)', [file_path])
        table_names.append(table_name)
        
    elif ext in [".xlsx", ".xls"]:
        excel_file = pd.read_excel(file_path, sheet_name=None)
        for sheet_name, df in excel_file.items():
            clean_name = "".join(c if c.isalnum() else "_" for c in sheet_name).lower()
            if not clean_name or not clean_name[0].isalpha():
                clean_name = f"tbl_{clean_name}"
            temp_view = f"temp_view_{clean_name}"
            conn.register(temp_view, df)
            conn.execute(f'CREATE OR REPLACE TABLE "{clean_name}" AS SELECT * FROM "{temp_view}"')
            conn.unregister(temp_view)
            table_names.append(clean_name)
    else:
        raise ValueError(f"Unsupported file extension: {ext}")

    try:
        conn.execute("CHECKPOINT")
    except Exception:
        pass

    DATASET_STORE[dataset_id] = {
        "conn": conn,
        "tables": table_names
    }

    try:
        from backend.profiling import clear_profile_cache
        clear_profile_cache(dataset_id)
        from backend.agent.tools_autonomous import clear_autonomous_cache
        clear_autonomous_cache(dataset_id)
    except Exception:
        pass

    return dataset_id, table_names

def get_schema(conn: duckdb.DuckDBPyConnection) -> str:
    """
    Generates a clean text schema representation of all tables in the DuckDB connection.
    """
    tables_df = conn.execute("SHOW TABLES").fetchdf()
    if tables_df.empty:
        return "No tables found."

    schema_parts = []
    for table_name in tables_df["name"]:
        columns_df = conn.execute(f'DESCRIBE "{table_name}"').fetchdf()
        cols_desc = [f"  - {row['column_name']} ({row['column_type']})" for _, row in columns_df.iterrows()]
        
        # Sample top 2 rows to give LLM context on values
        sample_df = conn.execute(f'SELECT * FROM "{table_name}" LIMIT 2').fetchdf()
        sample_str = sample_df.to_string(index=False)
        
        schema_parts.append(
            f"Table: {table_name}\n"
            f"Columns:\n" + "\n".join(cols_desc) + "\n"
            f"Sample Data:\n{sample_str}\n"
        )

    return "\n---\n".join(schema_parts)

def get_compact_schema(conn: duckdb.DuckDBPyConnection, max_distinct: int = 12) -> str:
    """
    Compact schema for LLM prompts: one line per column with its type, plus the actual
    distinct values of low-cardinality text columns and numeric min/max ranges.
    Keeps the prompt small (fast local inference) while giving the model real data context.
    """
    tables_df = conn.execute("SHOW TABLES").fetchdf()
    if tables_df.empty:
        return "No tables found."

    parts = []
    for table_name in tables_df["name"]:
        row_count = conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
        columns_df = conn.execute(f'DESCRIBE "{table_name}"').fetchdf()
        lines = [f"Table: {table_name} ({row_count} rows)", "Columns:"]
        for _, row in columns_df.iterrows():
            col, ctype = row["column_name"], str(row["column_type"])
            extra = ""
            try:
                if ctype.upper().startswith("VARCHAR"):
                    n_distinct = conn.execute(f'SELECT COUNT(DISTINCT "{col}") FROM "{table_name}"').fetchone()[0]
                    if 0 < n_distinct <= max_distinct:
                        vals = conn.execute(
                            f'SELECT DISTINCT "{col}" FROM "{table_name}" WHERE "{col}" IS NOT NULL ORDER BY 1 LIMIT {max_distinct}'
                        ).fetchall()
                        extra = " values: [" + ", ".join(str(v[0]) for v in vals) + "]"
                elif any(t in ctype.upper() for t in ("INT", "DOUBLE", "FLOAT", "DECIMAL", "REAL")):
                    lo, hi = conn.execute(f'SELECT MIN("{col}"), MAX("{col}") FROM "{table_name}"').fetchone()
                    if lo is not None:
                        extra = f" range: {lo} to {hi}"
            except Exception:
                pass
            lines.append(f"  - {col} ({ctype}){extra}")
        parts.append("\n".join(lines))

    return "\n\n".join(parts)

def get_dataset_connection(dataset_id: str) -> duckdb.DuckDBPyConnection:
    if dataset_id in DATASET_STORE:
        return DATASET_STORE[dataset_id]["conn"].cursor()

    db_path = get_db_path(dataset_id)
    if os.path.exists(db_path):
        conn = duckdb.connect(database=db_path)
        tables_df = conn.execute("SHOW TABLES").fetchdf()
        table_names = tables_df["name"].tolist() if not tables_df.empty else []
        DATASET_STORE[dataset_id] = {
            "conn": conn,
            "tables": table_names
        }
        return conn.cursor()

    raise KeyError(f"Dataset ID '{dataset_id}' not found. Please upload dataset first.")
