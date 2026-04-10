"""YAML configuration loader — single source of truth for products and pipelines."""
import os
from pathlib import Path
from typing import Any
import yaml
import structlog

logger = structlog.get_logger()

_CONFIG_DIR = Path(__file__).parent
_products_cache: dict[str, Any] = {}
_pipelines_cache: list[dict] = []


def load_products_config() -> dict[str, Any]:
    global _products_cache
    path = _CONFIG_DIR / "products.yaml"
    with open(path) as f:
        raw = yaml.safe_load(f)
    _products_cache = {p["id"]: p for p in raw.get("products", [])}
    logger.info("Loaded product configs", count=len(_products_cache))
    return _products_cache


def load_pipelines_config() -> list[dict]:
    global _pipelines_cache
    path = _CONFIG_DIR / "pipelines.yaml"
    with open(path) as f:
        raw = yaml.safe_load(f)
    _pipelines_cache = raw.get("data_pipelines", [])
    logger.info("Loaded pipeline configs", count=len(_pipelines_cache))
    return _pipelines_cache


def get_products() -> dict[str, Any]:
    if not _products_cache:
        return load_products_config()
    return _products_cache


def get_product(product_id: str) -> dict[str, Any] | None:
    products = get_products()
    return products.get(product_id)


def get_pipelines() -> list[dict]:
    if not _pipelines_cache:
        return load_pipelines_config()
    return _pipelines_cache


def reload_configs() -> None:
    """Hot-reload all YAML configs without restart."""
    load_products_config()
    load_pipelines_config()
    logger.info("Configs reloaded")
