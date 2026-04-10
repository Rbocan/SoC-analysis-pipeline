"""Tests for DataProcessor (using temp parquet files)."""
import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch
import polars as pl

from app.services.data_processor import DataProcessor


@pytest.fixture
def sample_df():
    n = 200
    import numpy as np
    rng = np.random.default_rng(42)
    now = datetime.utcnow()
    return pl.DataFrame({
        "product_id": ["soc_a8"] * n,
        "batch_id": [f"BATCH-{i:04d}" for i in rng.integers(1, 20, n)],
        "lot_id": [f"LOT-{i:04d}" for i in rng.integers(1, 5, n)],
        "test_id": rng.choice(["boot_test", "stress_test", "thermal_validation"], n).tolist(),
        "unit_id": [f"UNIT-{i:06d}" for i in range(n)],
        "timestamp": [now - timedelta(hours=i) for i in range(n)],
        "voltage": rng.normal(1.05, 0.05, n).tolist(),
        "temperature": rng.normal(45, 10, n).tolist(),
        "status": ["passed"] * 180 + ["failed"] * 20,
    })


@pytest.fixture
def processor_with_data(sample_df, tmp_path):
    parquet_path = tmp_path / "soc_a8.parquet"
    sample_df.write_parquet(str(parquet_path))
    proc = DataProcessor()
    with patch.object(proc, "_parquet_path", return_value=parquet_path):
        yield proc


def test_query_returns_data(processor_with_data):
    result = processor_with_data.query("soc_a8", limit=50)
    assert result["total"] == 200
    assert len(result["data"]) == 50


def test_query_status_filter(processor_with_data):
    result = processor_with_data.query("soc_a8", status="failed", limit=100)
    assert result["total"] == 20
    for row in result["data"]:
        assert row["status"] == "failed"


def test_query_pagination(processor_with_data):
    page1 = processor_with_data.query("soc_a8", limit=50, offset=0)
    page2 = processor_with_data.query("soc_a8", limit=50, offset=50)
    ids1 = {r["unit_id"] for r in page1["data"]}
    ids2 = {r["unit_id"] for r in page2["data"]}
    assert ids1.isdisjoint(ids2), "Pages should not overlap"


def test_metrics_summary(processor_with_data):
    metrics = processor_with_data.get_metrics_summary("soc_a8")
    assert "pass_rate" in metrics
    assert "total_records" in metrics
    assert metrics["total_records"] == 200
    assert 85 <= metrics["pass_rate"] <= 100
    assert "voltage" in metrics
    assert isinstance(metrics["voltage"], dict)
    assert all(k in metrics["voltage"] for k in ("mean", "min", "max", "std"))


def test_pivot_returns_matrix(processor_with_data):
    result = processor_with_data.pivot(
        "soc_a8",
        index="batch_id",
        columns="test_id",
        values="voltage",
        agg_func="mean",
    )
    assert "data" in result
    assert "shape" in result
    assert result["shape"][1] > 1  # Multiple test columns


def test_missing_product_raises(tmp_path):
    proc = DataProcessor()
    with patch.object(proc, "_parquet_path", return_value=tmp_path / "nonexistent.parquet"):
        with pytest.raises(FileNotFoundError):
            proc.query("nonexistent")


def test_sql_query(processor_with_data, sample_df, tmp_path):
    """DuckDB SQL query over parquet."""
    parquet_path = tmp_path / "soc_a8.parquet"
    sample_df.write_parquet(str(parquet_path))

    proc = DataProcessor()
    with patch.object(proc, "_parquet_path", return_value=parquet_path):
        result = proc.sql_query(
            "soc_a8",
            "SELECT status, COUNT(*) as cnt FROM measurements GROUP BY status ORDER BY cnt DESC",
        )
    assert "data" in result
    assert len(result["data"]) == 2


def test_sql_injection_blocked(processor_with_data):
    with pytest.raises(ValueError, match="Only SELECT"):
        processor_with_data.sql_query("soc_a8", "DROP TABLE measurements")
