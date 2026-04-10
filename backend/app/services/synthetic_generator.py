"""
Synthetic SoC test data generator.
Produces realistic manufacturing measurements respecting product-spec constraints.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
from faker import Faker

import structlog

from app.settings import settings
from app.config.loader import get_product

logger = structlog.get_logger()
fake = Faker()
rng = np.random.default_rng()


def _generate_metric(spec: dict, n: int, anomaly_mask: np.ndarray) -> np.ndarray:
    dist = spec.get("distribution", "normal")
    lo, hi = spec["min_val"], spec["max_val"]
    nominal = spec["nominal"]

    if dist == "normal":
        sigma = (hi - lo) / 6  # 3-sigma within [lo, hi]
        values = rng.normal(loc=nominal, scale=sigma, size=n)
    else:
        values = rng.uniform(lo, hi, size=n)

    # Inject anomalies — push 20% outside bounds
    n_anomalies = anomaly_mask.sum()
    if n_anomalies > 0:
        direction = rng.choice([-1, 1], size=n_anomalies)
        overshoot = rng.uniform(0.05, 0.20, size=n_anomalies) * (hi - lo)
        values[anomaly_mask] = np.where(
            direction == 1,
            hi + overshoot,
            lo - overshoot,
        )

    return values


def generate_soc_data(
    product_id: str,
    num_records: int = 10_000,
    num_batches: int = 20,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    anomaly_rate: float = 0.02,
) -> pl.DataFrame:
    product = get_product(product_id)
    if product is None:
        raise ValueError(f"Unknown product: {product_id}")

    if start_date is None:
        start_date = datetime.utcnow() - timedelta(days=30)
    if end_date is None:
        end_date = datetime.utcnow()

    metrics: list[dict] = product["metrics"]
    tests: list[str] = product["tests"]

    # Build batch IDs
    batch_ids = [f"BATCH-{fake.bothify(text='??####').upper()}" for _ in range(num_batches)]
    lot_ids = [f"LOT-{fake.bothify(text='####').upper()}" for _ in range(max(1, num_batches // 5))]

    # Anomaly mask
    anomaly_mask = rng.random(num_records) < anomaly_rate

    # Timestamps — realistic production cadence
    start_ts = start_date.timestamp()
    end_ts = end_date.timestamp()
    timestamps = [
        datetime.fromtimestamp(ts)
        for ts in sorted(rng.uniform(start_ts, end_ts, num_records))
    ]

    data: dict[str, Any] = {
        "product_id": [product_id] * num_records,
        "batch_id": rng.choice(batch_ids, num_records).tolist(),
        "lot_id": rng.choice(lot_ids, num_records).tolist(),
        "test_id": rng.choice(tests, num_records).tolist(),
        "unit_id": [f"UNIT-{i:06d}" for i in rng.integers(1, 999999, num_records)],
        "timestamp": timestamps,
    }

    # Generate each metric
    for spec in metrics:
        name = spec["name"]
        values = _generate_metric(spec, num_records, anomaly_mask)
        data[name] = values.tolist()

    # Status: pass/fail based on all metrics within spec
    status = []
    for i in range(num_records):
        passed = True
        for spec in metrics:
            val = data[spec["name"]][i]
            if val < spec["min_val"] or val > spec["max_val"]:
                passed = False
                break
        status.append("passed" if passed else "failed")
    data["status"] = status

    # Yield rate per batch (derived)
    df = pl.DataFrame(data)
    logger.info(
        "Generated synthetic data",
        product=product_id,
        records=num_records,
        batches=num_batches,
        pass_rate=f"{sum(s == 'passed' for s in status) / num_records:.1%}",
    )
    return df


def save_synthetic_data(
    product_id: str,
    df: pl.DataFrame,
    append: bool = False,
) -> Path:
    out_dir = Path(settings.parquet_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{product_id}.parquet"

    if append and out_path.exists():
        existing = pl.read_parquet(str(out_path))
        df = pl.concat([existing, df])

    df.write_parquet(str(out_path))
    logger.info("Saved parquet", path=str(out_path), rows=len(df))
    return out_path
