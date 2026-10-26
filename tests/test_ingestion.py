"""
Unit tests for data ingestion into DuckDB and schema extraction.
"""
import pytest
import os
import duckdb
from backend.ingestion import load_file_into_duckdb, get_schema, get_dataset_connection

def test_load_csv():
    csv_path = "data/sample_dataset.csv"
    assert os.path.exists(csv_path)
    
    dataset_id, tables = load_file_into_duckdb(csv_path)
    assert dataset_id is not None
    assert len(tables) == 1
    assert tables[0] == "sample_dataset"
    
    conn = get_dataset_connection(dataset_id)
    df = conn.execute(f"SELECT COUNT(*) as cnt FROM {tables[0]}").fetchdf()
    assert df["cnt"].iloc[0] == 15

def test_get_schema():
    csv_path = "data/sample_dataset.csv"
    dataset_id, tables = load_file_into_duckdb(csv_path)
    conn = get_dataset_connection(dataset_id)
    
    schema_str = get_schema(conn)
    assert "Table: sample_dataset" in schema_str
    assert "sales_amount" in schema_str
    assert "category" in schema_str


def test_excel_multi_sheet_ingestion(tmp_path):
    import pandas as pd
    excel_file = tmp_path / "test_data.xlsx"
    with pd.ExcelWriter(excel_file) as writer:
        pd.DataFrame({"id": [1, 2], "product": ["A", "B"]}).to_excel(writer, sheet_name="product_lookup", index=False)
        pd.DataFrame({"id": [1, 2], "amount": [100, 200]}).to_excel(writer, sheet_name="sales_data", index=False)

    dataset_id, tables = load_file_into_duckdb(str(excel_file))
    assert len(tables) == 2
    assert tables == ["product_lookup", "sales_data"]

    conn = get_dataset_connection(dataset_id)
    catalog_tables = conn.execute("SHOW TABLES").fetchdf()["name"].tolist()
    assert sorted(catalog_tables) == ["product_lookup", "sales_data"]

