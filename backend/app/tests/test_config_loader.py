"""Tests for YAML config loader."""
import pytest
from app.config.loader import load_products_config, load_pipelines_config, get_product


def test_load_products():
    products = load_products_config()
    assert len(products) >= 3
    assert "soc_a8" in products
    assert "soc_m4" in products
    assert "soc_x1" in products


def test_product_structure():
    products = load_products_config()
    p = products["soc_a8"]
    assert "name" in p
    assert "metrics" in p
    assert "tests" in p
    assert len(p["metrics"]) >= 4
    assert len(p["tests"]) >= 3


def test_metric_has_required_fields():
    products = load_products_config()
    for metric in products["soc_a8"]["metrics"]:
        assert "name" in metric
        assert "unit" in metric
        assert "min_val" in metric
        assert "max_val" in metric
        assert "nominal" in metric
        assert metric["min_val"] < metric["max_val"]
        assert metric["min_val"] <= metric["nominal"] <= metric["max_val"]


def test_get_product_returns_none_for_unknown():
    assert get_product("nonexistent_product_xyz") is None


def test_load_pipelines():
    pipelines = load_pipelines_config()
    assert len(pipelines) >= 2
    for p in pipelines:
        assert "id" in p
        assert "schedule" in p
        assert "transformations" in p
