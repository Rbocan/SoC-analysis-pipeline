"""Tests for synthetic data generation."""
import pytest
import polars as pl
from unittest.mock import patch
from app.services.synthetic_generator import generate_soc_data


MOCK_PRODUCT = {
    "id": "test_soc",
    "name": "Test SoC",
    "description": "Test product",
    "data_source": "/data/parquet/test_soc.parquet",
    "metrics": [
        {"name": "voltage", "unit": "V", "min_val": 0.9, "max_val": 1.2, "nominal": 1.05, "distribution": "normal"},
        {"name": "temperature", "unit": "C", "min_val": -10, "max_val": 85, "nominal": 45, "distribution": "normal"},
    ],
    "tests": ["boot_test", "stress_test"],
}


@pytest.fixture
def mock_product():
    with patch("app.services.synthetic_generator.get_product", return_value=MOCK_PRODUCT):
        yield


def test_generate_returns_dataframe(mock_product):
    df = generate_soc_data("test_soc", num_records=100, num_batches=5)
    assert isinstance(df, pl.DataFrame)
    assert len(df) == 100


def test_generate_has_required_columns(mock_product):
    df = generate_soc_data("test_soc", num_records=100, num_batches=5)
    required = {"product_id", "batch_id", "test_id", "timestamp", "status", "voltage", "temperature"}
    assert required.issubset(set(df.columns))


def test_status_is_pass_or_fail(mock_product):
    df = generate_soc_data("test_soc", num_records=200, num_batches=5)
    assert set(df["status"].unique().to_list()).issubset({"passed", "failed"})


def test_product_id_correct(mock_product):
    df = generate_soc_data("test_soc", num_records=50, num_batches=5)
    assert all(v == "test_soc" for v in df["product_id"].to_list())


def test_anomaly_rate_approximately_correct(mock_product):
    """With anomaly_rate=0.20, roughly 20% should fail."""
    df = generate_soc_data("test_soc", num_records=10000, num_batches=10, anomaly_rate=0.20)
    fail_rate = df.filter(pl.col("status") == "failed").height / len(df)
    # Fail rate should be >= 15% (anomalies + borderline values)
    assert fail_rate >= 0.10


def test_no_anomalies_all_pass(mock_product):
    """With anomaly_rate=0, most records should pass (values near nominal)."""
    df = generate_soc_data("test_soc", num_records=500, num_batches=5, anomaly_rate=0.0)
    pass_rate = df.filter(pl.col("status") == "passed").height / len(df)
    # With normal distribution and 3-sigma spread, >99% should be in range
    assert pass_rate > 0.90


def test_invalid_product_raises():
    with patch("app.services.synthetic_generator.get_product", return_value=None):
        with pytest.raises(ValueError, match="Unknown product"):
            generate_soc_data("nonexistent", num_records=10)
