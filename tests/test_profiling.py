"""
Unit tests for automated dataset profiling and data quality engine.
"""
import pytest
import tempfile
import os
import pandas as pd
from backend.ingestion import load_file_into_duckdb
from backend.profiling import profile_dataset


def test_profiling_engine_basic():
    # Create temp CSV with known nulls and duplicate rows
    data = {
        "id": [1, 2, 3, 4, 4],  # 4 is duplicate row candidate if full row is dup
        "name": ["Alice", "Bob", "Charlie", "David", "David"],
        "age": [25, None, 30, 40, 40],
        "category": ["A", "A", "A", "A", "A"],  # constant column
    }
    df = pd.DataFrame(data)

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        tmp_path = tmp.name
        df.to_csv(tmp_path, index=False)

    try:
        dataset_id, tables = load_file_into_duckdb(tmp_path)
        profile = profile_dataset(dataset_id)

        assert profile.dataset_id == dataset_id
        assert len(profile.tables) == 1
        assert profile.total_rows == 5
        assert profile.total_columns == 4
        assert 0 <= profile.overall_quality_score <= 100

        t_prof = profile.tables[0]
        assert t_prof.row_count == 5
        assert t_prof.duplicate_rows == 1  # (4, David, 40, A) duplicated

        cols_map = {c.name: c for c in t_prof.columns}
        assert cols_map["age"].null_count == 1
        assert cols_map["age"].null_percentage == 20.0
        assert cols_map["category"].distinct_count == 1

        # Check warnings generated
        assert len(profile.warnings) > 0
        warning_text = " ".join(profile.warnings)
        assert "duplicate rows" in warning_text or "missing values" in warning_text or "constant value" in warning_text
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_profiling_sample_dataset():
    if os.path.exists("data/sample_dataset.csv"):
        dataset_id, _ = load_file_into_duckdb("data/sample_dataset.csv")
        profile = profile_dataset(dataset_id)
        assert profile.total_rows > 0
        assert profile.total_columns > 0
        assert profile.overall_quality_score > 0


def test_profile_endpoint():
    from fastapi.testclient import TestClient
    from backend.main import app

    client = TestClient(app)
    if os.path.exists("data/sample_dataset.csv"):
        dataset_id, _ = load_file_into_duckdb("data/sample_dataset.csv")
        response = client.get(f"/profile/{dataset_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["dataset_id"] == dataset_id
        assert "overall_quality_score" in data
        assert len(data["tables"]) > 0

