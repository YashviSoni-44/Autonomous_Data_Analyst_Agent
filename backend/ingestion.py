"""
Ingestion layer: Converts CSV, Excel, or Postgres data into DuckDB tables and extracts schema.
"""
import os
import duckdb
import pandas as pd
import uuid

# Storage directory for active DuckDB sessions or uploads
DATASET_STORE = {}

def load_file_into_duckdb(file_path: str, dataset_id: str = None) -> tuple[str, list[str]]:
    """
    Loads CSV or Excel into a DuckDB connection stored in DATASET_STORE.
    Returns (dataset_id, list of table names created).
    """
    if not dataset_id:
        dataset_id = str(uuid.uuid4())[:8]

    conn = duckdb.connect(database=":memory:")
    table_names = []

    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == ".csv":
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        table_name = "".join(c if c.isalnum() else "_" for c in base_name).lower()
        if not table_name:
            table_name = "data_table"
        
        conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM read_csv_auto(?)", [file_path])
        table_names.append(table_name)
        
    elif ext in [".xlsx", ".xls"]:
        excel_file = pd.read_excel(file_path, sheet_name=None)
        for sheet_name, df in excel_file.items():
            clean_name = "".join(c if c.isalnum() else "_" for c in sheet_name).lower()
            if not clean_name:
                clean_name = "sheet"
            conn.register(f"df_{clean_name}", df)
            conn.execute(f"CREATE TABLE {clean_name} AS SELECT * FROM df_{clean_name}")
            table_names.append(clean_name)
    else:
        raise ValueError(f"Unsupported file extension: {ext}")

    DATASET_STORE[dataset_id] = {
        "conn": conn,
        "tables": table_names
    }

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
        columns_df = conn.execute(f"DESCRIBE {table_name}").fetchdf()
        cols_desc = [f"  - {row['column_name']} ({row['column_type']})" for _, row in columns_df.iterrows()]
        
        # Sample top 2 rows to give LLM context on values
        sample_df = conn.execute(f"SELECT * FROM {table_name} LIMIT 2").fetchdf()
        sample_str = sample_df.to_string(index=False)
        
        schema_parts.append(
            f"Table: {table_name}\n"
            f"Columns:\n" + "\n".join(cols_desc) + "\n"
            f"Sample Data:\n{sample_str}\n"
        )

    return "\n---\n".join(schema_parts)

def get_dataset_connection(dataset_id: str) -> duckdb.DuckDBPyConnection:
    if dataset_id not in DATASET_STORE:
        raise KeyError(f"Dataset ID '{dataset_id}' not found. Please upload dataset first.")
    return DATASET_STORE[dataset_id]["conn"]
